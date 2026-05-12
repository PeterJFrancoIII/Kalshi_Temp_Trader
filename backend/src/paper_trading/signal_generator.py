import os
import json
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

logger = logging.getLogger(__name__)

try:
    from shared.manual_corrections import get_market_open_time_et
except ImportError:
    def get_market_open_time_et(date_str): return None


from market_data.kalshi_contract_mapper import parse_kalshi_markets
from shared.artifact_paths import (
    LATEST_KALSHI_MARKET_SNAPSHOT,
    LATEST_NWS_KMIA_SNAPSHOT,
    LATEST_PAPER_SIGNAL,
)
from shared.timestamp_utils import extract_embedded_timestamp
from trading.edge_engine import calculate_edge, calculate_expected_value, calculate_speed_to_roi
from risk.risk_engine import evaluate_risk_gates
from paper_trading.paper_ledger import PaperLedger

# Resolve ROOT
ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = ROOT / "backend" / "data" / "processed" / "reports"
SNAPSHOT_FILE = LATEST_KALSHI_MARKET_SNAPSHOT
NWS_SNAPSHOT_FILE = LATEST_NWS_KMIA_SNAPSHOT   # override in tests via sg.NWS_SNAPSHOT_FILE
OUTPUT_DIR = ROOT / "backend" / "data" / "processed" / "paper_trading"


def get_latest_file(directory: Path, pattern: str) -> Optional[Path]:
    """Returns the most-recent matching file, preferring embedded JSON timestamps
    over filesystem mtime to avoid silent lookahead from file copies or syncs."""
    files = list(directory.glob(pattern))
    if not files:
        return None

    candidates = []
    for f in files:
        ts = extract_embedded_timestamp(f)
        if ts is not None:
            candidates.append((ts, f))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]

    # Fallback to mtime only when no embedded timestamps exist (non-JSON files, etc.)
    logger.warning(
        f"get_latest_file({pattern}): no embedded timestamps found; "
        f"falling back to filesystem mtime."
    )
    return max(files, key=os.path.getmtime)

def parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """Parses timestamp from filename like kmia_forecast_2026-05-03_rules_v2_climatology_203650.md"""
    match = re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d{2})(\d{2})(\d{2})", filename)
    if match:
        date_str, hh, mm, ss = match.groups()
        try:
            return datetime.strptime(f"{date_str} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None

def parse_ticker_date(ticker: str) -> Optional[str]:
    """Parses date from ticker like KXHIGHMIA-26MAY06-B84.5"""
    match = re.search(r"([0-9]{2})([A-Z]{3})([0-9]{2})", ticker)
    if not match: return None
    year_short, mon_str, day_str = match.groups()
    months = {"JAN":"01","FEB":"02","MAR":"03","APR":"04","MAY":"05","JUN":"06",
              "JUL":"07","AUG":"08","SEP":"09","OCT":"10","NOV":"11","DEC":"12"}
    month = months.get(mon_str.upper())
    if not month: return None
    return f"20{year_short}-{month}-{day_str}"

def parse_forecast_bins_from_md(md_path: Path) -> Dict[str, float]:
    """Parses probability bins from a forecast markdown report."""
    if not md_path.exists():
        return {}
    
    with open(md_path, "r") as f:
        content = f.read()
    
    bins = {}
    pattern = r"\|\s*([<>=]*\d+[-\d]*)\s*\|\s*(\d+\.?\d*)%\s*\|"
    matches = re.findall(pattern, content)
    for bin_label, prob_str in matches:
        bins[bin_label] = float(prob_str) / 100.0
    
    return bins

def select_executable_price(ask: Optional[float], last: Optional[float]) -> Optional[float]:
    """Selects the price to use for execution (Ask for buying, or fallback to Last)."""
    return ask if ask is not None else last


# ---------------------------------------------------------------------------
# Legacy coarse fixed-bin contract probability estimator.
# The main signal pipeline now uses map_distribution_to_bins() from
# kalshi_contract_mapper (integer-level, dynamic bins).  This function is
# retained for backward compatibility and tests that exercise the coarse
# 6-bin approximation.
# ---------------------------------------------------------------------------

_LEGACY_BIN_RANGES: Dict[str, tuple] = {
    "<=78":  (None, 78),
    "79-80": (79,   80),
    "81-82": (81,   82),
    "83-84": (83,   84),
    "85-86": (85,   86),
    ">=87":  (87,   None),
}


def estimate_contract_probability(mapping: Dict[str, Any], model_bins: Dict[str, float]) -> tuple:
    """
    Estimates contract probability from fixed bins.

    Legacy function retained for backward compatibility.  The active signal
    pipeline uses map_distribution_to_bins() with integer-level distributions
    instead, which correctly handles arbitrary Kalshi contract thresholds.

    Returns (probability, warnings).
    """
    cond = mapping.get("condition_type")
    t = mapping.get("threshold_f")
    h = mapping.get("range_high_f")

    if cond == "unknown" or t is None:
        return None, ["Unknown contract condition or missing threshold."]

    total_prob = 0.0
    matched_any = False
    uncertain = False

    for bin_label, (b_low, b_high) in _LEGACY_BIN_RANGES.items():
        prob = model_bins.get(bin_label, 0.0)

        if cond == "above":
            if b_low is not None and b_low > t:
                total_prob += prob
                matched_any = True
            elif b_high is not None and b_high <= t:
                pass
            else:
                uncertain = True

        elif cond == "below":
            if b_high is not None and b_high < t:
                total_prob += prob
                matched_any = True
            elif b_low is not None and b_low >= t:
                pass
            else:
                uncertain = True

        elif cond == "between":
            if b_low is not None and b_high is not None and b_low >= t and b_high <= h:
                total_prob += prob
                matched_any = True
            elif (b_high is not None and b_high < t) or (b_low is not None and b_low > h):
                pass
            else:
                uncertain = True

    if uncertain:
        return None, [f"Contract boundary {t} cuts through model bins. Exact mapping uncertain."]

    if not matched_any and total_prob == 0:
        if cond == "above" and t >= 87:
            return 0.0, ["Threshold above model's max bin boundary (87)."]
        if cond == "below" and t <= 78:
            return 0.0, ["Threshold below model's min bin boundary (78)."]

    return total_prob, []


def _read_embedded_snapshot_timestamp(snapshot_path: Path) -> Optional[datetime]:
    """
    Reads the embedded timestamp from a Kalshi market snapshot JSON file.

    Tries fields: fetched_at_utc, generated_at_utc, timestamp, created_at.
    Returns a timezone-aware UTC datetime, or None if no valid field found.

    Uses embedded timestamps rather than os.path.getmtime() to avoid silent
    lookahead from file copies, Drive syncs, or Git checkouts.
    """
    try:
        with open(snapshot_path, "r") as f:
            data = json.load(f)
        for field in ("fetched_at_utc", "generated_at_utc", "timestamp", "created_at"):
            raw = data.get(field)
            if not raw:
                continue
            try:
                dt = datetime.fromisoformat(str(raw))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError):
                continue
    except Exception:
        pass
    return None

def generate_paper_signal(
    forecast_path: Optional[Path] = None,
    snapshot_path: Optional[Path] = None,
    prediction_timestamp: Optional[datetime] = None,
    output_dir: Optional[Path] = None,
    latest_path_override: Optional[Path] = None,
    ledger_path_override: Optional[Path] = None
):
    """Generates a quantitative edge report comparing model vs market using active contracts."""
    out_dir = output_dir if output_dir else OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Load Forecast
    if forecast_path:
        forecast_file = forecast_path
    else:
        forecast_file = get_latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.json")
        if not forecast_file:
            forecast_file = get_latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.md")
        
    # Validation
    if forecast_file and prediction_timestamp:
        file_ts = parse_timestamp_from_filename(forecast_file.name)
        if file_ts and file_ts > prediction_timestamp:
            raise ValueError(f"Forecast file {forecast_file.name} is from the future relative to prediction timestamp {prediction_timestamp}")
            
    model_bins = {}
    integer_dist = {}
    forecast_data_obj = {}
    if forecast_file:
        if forecast_file.suffix == ".md":
            model_bins = parse_forecast_bins_from_md(forecast_file)
            forecast_data_obj = {"probability_bins": model_bins}
        else:
            with open(forecast_file, "r") as f:
                forecast_data_obj = json.load(f)
                model_bins = forecast_data_obj.get("probability_bins", {})
                # Load integer distribution if available (keys are strings in JSON, convert to int)
                raw_int_dist = forecast_data_obj.get("integer_distribution", {})
                integer_dist = {int(k): v for k, v in raw_int_dist.items()}
    
    # Extract forecast date
    forecast_date_str = None
    if forecast_file:
        file_ts = parse_timestamp_from_filename(forecast_file.name)
        if file_ts:
            forecast_date_str = file_ts.strftime("%Y-%m-%d")
            
    # 2. Load and Map Active Markets
    snapshot_to_use = snapshot_path if snapshot_path else SNAPSHOT_FILE
    
    # Validation for snapshot — use embedded JSON timestamp, never filesystem mtime.
    if snapshot_path and prediction_timestamp:
        embedded_ts = _read_embedded_snapshot_timestamp(snapshot_path)
        if embedded_ts is None:
            logger.warning(
                f"Snapshot {snapshot_path.name}: no embedded timestamp found; "
                f"skipping future-check (mtime fallback forbidden)."
            )
        elif embedded_ts > prediction_timestamp:
            raise ValueError(
                f"Snapshot file {snapshot_path.name} has embedded timestamp "
                f"{embedded_ts.isoformat()} which is after prediction_timestamp "
                f"{prediction_timestamp.isoformat()}"
            )

    # F2: Load NWS snapshot to extract the real observation timestamp for Gate 2.
    # If the observation time is missing or unavailable, Gate 2 fails closed (blocks).
    # Passing datetime.now() here would permanently bypass Gate 2 — never do that.
    # NWS_SNAPSHOT_FILE is a module-level variable so tests can inject a temp path.
    latest_obs_time_iso: Optional[str] = None
    try:
        if NWS_SNAPSHOT_FILE.exists():
            with open(NWS_SNAPSHOT_FILE, "r") as _f:
                _nws_data = json.load(_f)
            latest_obs_time_iso = _nws_data.get("latest_observation_time")
            if latest_obs_time_iso is None:
                logger.warning(
                    "NWS snapshot loaded but 'latest_observation_time' field is missing. "
                    "Gate 2 (weather freshness) will block."
                )
        else:
            logger.warning(
                f"NWS snapshot not found at {NWS_SNAPSHOT_FILE}. "
                "Gate 2 (weather freshness) will block."
            )
    except Exception as _e:
        logger.warning(f"Could not load NWS snapshot for Gate 2 check: {_e}. Gate 2 will block.")

    from market_data.kalshi_contract_mapper import parse_kalshi_markets, mapping_to_bin_string
    markets = parse_kalshi_markets(snapshot_to_use)

    signals = []
    global_warnings = []
    status = "OK"
    
    if not model_bins:
        global_warnings.append("No forecast bins available. Ensure daily workflow ran.")
        status = "NO_SIGNAL"
        
    if not markets:
        global_warnings.append("No active KXHIGHMIA markets available in current market snapshot.")
        status = "NO_SIGNAL"

    for m in markets:
        ticker = m.get("ticker")
        mapping = m.get("contract_mapping", {})
        contract_bin_data = m.get("contract_bin")
        
        # Extract Market Price first so we can use it in fallback signals
        ask = m.get("yes_ask_dollars")
        bid = m.get("yes_bid_dollars")
        last = m.get("last_price_dollars")
        
        # Fallback to cents
        if ask is None and m.get("yes_ask") is not None: ask = m.get("yes_ask") / 100.0
        else: ask = float(ask) if ask is not None else None
            
        if bid is None and m.get("yes_bid") is not None: bid = m.get("yes_bid") / 100.0
        else: bid = float(bid) if bid is not None else None

        if last is None and m.get("last_price") is not None: last = m.get("last_price") / 100.0
        else: last = float(last) if last is not None else None

        executable_price = select_executable_price(ask, last)
        
        if executable_price is None or executable_price == 0:
            global_warnings.append(f"{ticker}: No usable price data. Skipping.")
            continue
            
        ticker_date = parse_ticker_date(ticker)
        is_stale = False
        if ticker_date and forecast_date_str and ticker_date < forecast_date_str:
            is_stale = True
        
        # Legacy compatibility bridge:
        # Historical markdown reports may still contain coarse fixed bins.
        # Active Kalshi paper signals should map an integer temperature distribution
        # into Kalshi-discovered contract_bin ranges.
        if contract_bin_data:
            bin_str = contract_bin_data.get("label")
        else:
            bin_str = mapping_to_bin_string(mapping)
        prob = None
        
        if bin_str:
            if is_stale:
                prob = 0.0
            else:
                prob = model_bins.get(bin_str)
                if prob is None and integer_dist:
                    # Fallback: map from integer distribution
                    from market_data.kalshi_contract_mapper import map_distribution_to_bins
                    mapped = map_distribution_to_bins(integer_dist, [bin_str])
                    prob = mapped.get(bin_str)
                
            if prob is None:
                global_warnings.append(f"{ticker}: Probability for bin {bin_str} not found in forecast.")
                # Requirement 5: Generate Dashboard-Compatible Signal Rows even if mapping fails
                signals.append({
                    "market_ticker": ticker,
                    "market_title": m.get("title"),
                    "status": m.get("status"),
                    "condition_type": mapping.get("condition_type"),
                    "threshold_f": mapping.get("threshold_f"),
                    "model_probability": None,
                    "market_probability": round(executable_price, 4) if executable_price else None,
                    "raw_edge": None,
                    "edge": None,
                    "breakeven_probability": None,
                    "expected_value": None,
                    "paper_action": "NO SIGNAL",
                    "confidence": "low",
                    "yes_ask": ask,
                    "yes_bid": bid,
                    "last_price": last,
                    "warnings": [f"Probability for bin {bin_str} not found in forecast"],
                    "market_open_time_et": get_market_open_time_et(ticker_date) if ticker_date else None,
                    "stale": is_stale
                })
                continue
        else:
            global_warnings.append(f"{ticker}: Could not convert contract mapping to bin string.")
            continue
        # Use Edge Engine for math
        edge, raw_edge, final_breakeven = calculate_edge(prob, executable_price, slippage=0.0)
        ev = calculate_expected_value(prob, final_breakeven)
        speed_score, mins_to_close = calculate_speed_to_roi(ev, m.get("close_time"))

        # Evaluate Risk Gates
        if ledger_path_override:
            ledger = PaperLedger(ledger_path=ledger_path_override)
        else:
            ledger = PaperLedger()

        ledger_summary = ledger.get_summary()

        forecast_data_for_risk = dict(forecast_data_obj)
        if global_warnings:
            forecast_data_for_risk.setdefault("warnings", []).extend(global_warnings)

        risk_decision = evaluate_risk_gates(
            forecast_data=forecast_data_for_risk,
            # F2: Pass the real NWS observation timestamp (loaded above before this loop).
            # latest_obs_time_iso is None when the snapshot is missing or lacks the field,
            # which causes Gate 2 to fail closed — that is the correct safe behavior.
            latest_obs_time_iso=latest_obs_time_iso,
            model_prob=prob,
            executable_price=executable_price,
            yes_ask=ask,
            yes_bid=bid,
            edge=edge,
            raw_edge=raw_edge,
            ledger_summary=ledger_summary,
            target_date_str=ticker_date if ticker_date else "unknown"
        )
        
        # Action logic
        action = "NO EDGE"
        confidence = "low"
        
        if is_stale:
            action = "NO SIGNAL"
            edge = -999.0
            ev = -999.0
            risk_decision.passed = False
            risk_decision.reason = "Stale ticker or missing forecast mapping."
        elif not risk_decision.passed:
            action = "BLOCKED BY RISK ENGINE"
        elif edge > 0.05:
            action = "PAPER BUY CANDIDATE"
            confidence = "medium"
            if edge > 0.15: confidence = "high"
        elif edge > 0:
            action = "WATCH"
        
        signals.append({
            "market_ticker": ticker,
            "market_title": m.get("title"),
            "status": m.get("status"),
            "condition_type": mapping.get("condition_type"),
            "threshold_f": mapping.get("threshold_f"),
            "range_high_f": mapping.get("range_high_f"),
            # F3: forecast_bin_label is the actual Kalshi contract range string used
            # for probability lookup (e.g. ">=87", "<=84", "91-92").  Coordinator and
            # other callers must store THIS field as forecast_bin in the ledger — NOT
            # condition_type ("above"/"below"/"between") which settlement cannot match.
            "forecast_bin_label": bin_str,
            "model_probability": round(prob, 4),
            "market_probability": round(executable_price, 4),
            "raw_edge": round(raw_edge, 4),
            "edge": round(edge, 4),
            "breakeven_probability": round(final_breakeven, 4),
            "expected_value": round(ev, 4),
            "speed_to_roi_score": speed_score,
            "time_to_close_minutes": mins_to_close,
            "paper_action": action,
            "confidence": confidence,
            "risk_decision": {
                "passed": risk_decision.passed,
                "reason": risk_decision.reason
            },
            "yes_ask": ask,
            "yes_bid": bid,
            "last_price": last,
            "market_open_time_et": get_market_open_time_et(ticker_date) if ticker_date else None,
            "stale": is_stale
        })

    # Check if all signals are stale
    all_stale = True
    if signals:
        for s in signals:
            if not s.get("stale"):
                all_stale = False
                break
                
    if signals and all_stale:
        signals = []
        status = "NO_SIGNAL"
        global_warnings.append("Preserved Kalshi snapshot is stale or event-date mismatched; no actionable signal generated.")

    signals.sort(key=lambda x: x["edge"] if x["edge"] is not None else -999.0, reverse=True)
    
    # If best signal has edge -999 or is None, it means all are stale or no edge!
    best_signal = signals[0] if signals and signals[0]["edge"] is not None and signals[0]["edge"] > -900 else None
    
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "forecast_source": str(forecast_file.name) if forecast_file else None,
        "market_snapshot_source": str(snapshot_to_use.name) if snapshot_to_use else None,
        "signals": signals,
        "best_signal": best_signal,
        "warnings": list(set(global_warnings)),
        "safety": {
            "no_real_trading": True,
            "disclaimer": "NO REAL TRADING EXECUTION - PAPER ONLY"
        }
    }
    
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    latest_path = latest_path_override if latest_path_override else LATEST_PAPER_SIGNAL
    ts_path = out_dir / f"paper_signal_{ts}.json"
    
    with open(latest_path, "w") as f:
        json.dump(report, f, indent=2)
    with open(ts_path, "w") as f:
        json.dump(report, f, indent=2)
        
    return latest_path

if __name__ == "__main__":
    path = generate_paper_signal()
    print(f"Paper signal report generated at {path}")

import os
import json
import re
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, Any, List, Optional

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

logger = logging.getLogger(__name__)

try:
    from shared.manual_corrections import get_market_open_time_et
except ImportError:
    def get_market_open_time_et(date_str): return None


from market_data.kalshi_contract_mapper import parse_kalshi_markets, mapping_to_bin_string
from shared.artifact_paths import (
    LATEST_KALSHI_MARKET_SNAPSHOT,
    LATEST_KALSHI_ORDERBOOKS,
    LATEST_NWS_KMIA_SNAPSHOT,
    LATEST_PAPER_SIGNAL,
    REPORTS_DIR,
    PAPER_TRADING_DIR
)
from shared.timestamp_utils import extract_embedded_timestamp, parse_ticker_date
from shared.normalization import normalize_contract_key
from trading.edge_engine import calculate_edge, calculate_expected_value, calculate_speed_to_roi
from risk.risk_engine import evaluate_risk_gates
from paper_trading.paper_ledger import PaperLedger

# Resolve ROOT
ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_FILE = LATEST_KALSHI_MARKET_SNAPSHOT
NWS_SNAPSHOT_FILE = LATEST_NWS_KMIA_SNAPSHOT   # override in tests via sg.NWS_SNAPSHOT_FILE
OUTPUT_DIR = PAPER_TRADING_DIR


def get_latest_file(directory: Path, pattern: str) -> Optional[Path]:
    """Returns the most-recent matching file, preferring embedded JSON timestamps
    over filesystem mtime to avoid silent lookahead from file copies or syncs."""
    files = list(directory.glob(pattern))
    if not files:
        return None

    candidates = []
    for f in files:
        ts = extract_embedded_timestamp(f)
        if ts is None:
            ts = parse_timestamp_from_filename(f.name)
        if ts is not None:
            candidates.append((ts, f))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]

    # Strict Lookahead Enforcement: Fallback to mtime is forbidden.
    logger.error(
        f"get_latest_file({pattern}): no embedded timestamps found. "
        f"Strict lookahead safety prohibits fallback to filesystem mtime."
    )
    raise ValueError(f"No valid embedded timestamps found for {pattern}. Filesystem mtime is forbidden.")

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

# _normalize_contract_key was moved to shared.normalization.normalize_contract_key

def find_forecast_for_date(target_date_str: str) -> Optional[Path]:
    """Finds the most recent forecast JSON or MD for a specific target date."""
    # JSON preferred
    json_pat = f"kmia_forecast_{target_date_str}_rules_v2_climatology_*.json"
    try:
        f = get_latest_file(REPORTS_DIR, json_pat)
        if f: return f
    except ValueError:
        pass

    md_pat = f"kmia_forecast_{target_date_str}_rules_v2_climatology_*.md"
    try:
        return get_latest_file(REPORTS_DIR, md_pat)
    except ValueError:
        return None

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
    
    if prediction_timestamp is None:
        prediction_timestamp = datetime.now(timezone.utc)
    
    # Use US/Eastern local date for staleness checks to avoid UTC rollover issues.
    now_date_str = prediction_timestamp.astimezone(ZoneInfo("US/Eastern")).strftime("%Y-%m-%d")

    # 1. Load NWS snapshot for Gate 2 check
    latest_obs_time_iso: Optional[str] = None
    try:
        if NWS_SNAPSHOT_FILE.exists():
            with open(NWS_SNAPSHOT_FILE, "r") as _f:
                _nws_data = json.load(_f)
            latest_obs_time_iso = _nws_data.get("latest_observation_time")
        else:
            logger.warning(f"NWS snapshot not found at {NWS_SNAPSHOT_FILE}.")
    except Exception as _e:
        logger.warning(f"Could not load NWS snapshot for Gate 2 check: {_e}.")

    # 2. Load Orderbooks
    all_orderbooks = {}
    if os.path.exists(LATEST_KALSHI_ORDERBOOKS):
        try:
            with open(LATEST_KALSHI_ORDERBOOKS, 'r') as f:
                ob_root = json.load(f)
                all_orderbooks = ob_root.get("orderbooks", {})
        except Exception as e:
            logger.warning(f"Could not load orderbook artifact: {e}")

    # 3. Load and Group Markets
    snapshot_to_use = snapshot_path if snapshot_path else SNAPSHOT_FILE
    if snapshot_path and prediction_timestamp:
        embedded_ts = _read_embedded_snapshot_timestamp(snapshot_path)
        if embedded_ts and embedded_ts > prediction_timestamp:
            raise ValueError(f"Snapshot file {snapshot_path.name} is from the future.")

    all_discovered_markets = parse_kalshi_markets(snapshot_to_use)
    markets_by_date = {}
    for m in all_discovered_markets:
        ticker_date = parse_ticker_date(m.get("ticker"))
        if ticker_date:
            markets_by_date.setdefault(ticker_date, []).append(m)

    # 4. Process each event date
    events_by_date = {}
    all_signals = []
    global_warnings = []
    
    # Sort dates so we process today then tomorrow
    target_dates = sorted(list(markets_by_date.keys()))
    
    # If a specific forecast_path was passed, identify its date
    override_forecast_date = None
    if forecast_path:
        with open(forecast_path, "r") as f:
            if forecast_path.suffix == ".json":
                f_data = json.load(f)
                override_forecast_date = f_data.get("date")
            if not override_forecast_date:
                # Fallback to filename
                f_ts = parse_timestamp_from_filename(forecast_path.name)
                if f_ts: override_forecast_date = f_ts.strftime("%Y-%m-%d")
        
        # C1-B Regression: If provided forecast date doesn't match ANY market date, emit mismatch warning
        if override_forecast_date and override_forecast_date not in target_dates:
            global_warnings.append(
                f"Forecast date {override_forecast_date} does not match any active contract dates: {target_dates}. "
                f"Signals may be unreliable due to date mismatch."
            )

    for event_date in target_dates:
        markets = markets_by_date[event_date]
        event_ticker = markets[0].get("event_ticker")
        
        # Find matching forecast
        f_file = None
        if forecast_path and event_date == override_forecast_date:
            f_file = forecast_path
        else:
            f_file = find_forecast_for_date(event_date)
            
        event_status = "OK"
        event_warnings = []
        event_signals = []
        event_probs = {}
        forecast_data_obj = {}
        model_bins = {}
        integer_dist = {}

        if not f_file:
            event_status = "NO_SIGNAL"
            event_warnings.append(f"No forecast artifact found for {event_date}.")
        else:
            # Load forecast data
            try:
                if f_file.suffix == ".md":
                    model_bins = parse_forecast_bins_from_md(f_file)
                    forecast_data_obj = {"probability_bins": model_bins, "date": event_date}
                else:
                    with open(f_file, "r") as f:
                        forecast_data_obj = json.load(f)
                        model_bins = forecast_data_obj.get("probability_bins", {})
                        raw_int_dist = forecast_data_obj.get("integer_distribution", {})
                        integer_dist = {int(k): v for k, v in raw_int_dist.items()}
                
                # Check for date mismatch between loaded forecast and target event_date
                f_date = forecast_data_obj.get("date")
                if f_date and f_date != event_date:
                    event_warnings.append(
                        f"Forecast date {f_date} does not match event date {event_date}. Signals may be unreliable."
                    )
            except Exception as e:
                event_status = "ERROR_LOADING_FORECAST"
                event_warnings.append(f"Error loading forecast {f_file.name}: {e}")

        if not model_bins and event_status == "OK":
            event_status = "NO_SIGNAL"
            event_warnings.append(f"Forecast for {event_date} contains no probability bins.")

        # Calculate probabilities and signals for this date
        if model_bins:
            # Pre-compute probabilities
            for m in markets:
                ticker = m.get("ticker")
                mapping = m.get("contract_mapping", {})
                contract_bin_data = m.get("contract_bin")
                
                is_stale = (event_date < now_date_str)
                bin_str = contract_bin_data.get("label") if contract_bin_data else mapping_to_bin_string(mapping)
                
                prob = None
                if bin_str:
                    if is_stale: prob = 0.0
                    else:
                        prob = model_bins.get(bin_str)
                        if prob is None and integer_dist:
                            from forecasting.contract_probability_mapper import map_distribution_to_contracts
                            res = map_distribution_to_contracts(integer_dist, [mapping])
                            prob = res.get(ticker, {}).get("probability")

                    if prob is not None:
                        norm_key = normalize_contract_key(bin_str)
                        event_probs[norm_key] = prob

            # Generate signals
            for m in markets:
                ticker = m.get("ticker")
                mapping = m.get("contract_mapping", {})
                bin_str = m.get("contract_bin", {}).get("label") if m.get("contract_bin") else mapping_to_bin_string(mapping)
                
                # Pricing
                ask = m.get("yes_ask_dollars")
                bid = m.get("yes_bid_dollars")
                last = m.get("last_price_dollars")
                
                # Cast to float if present
                ask = float(ask) if ask is not None else None
                bid = float(bid) if bid is not None else None
                last = float(last) if last is not None else None
                
                # Cents fallback
                if ask is None and m.get("yes_ask") is not None: ask = m.get("yes_ask") / 100.0
                if bid is None and m.get("yes_bid") is not None: bid = m.get("yes_bid") / 100.0
                if last is None and m.get("last_price") is not None: last = m.get("last_price") / 100.0

                # Orderbook override
                ob_m = all_orderbooks.get(ticker, {})
                if ob_m.get("top_yes_ask_dollars") is not None: ask = float(ob_m["top_yes_ask_dollars"])
                if ob_m.get("top_yes_bid_dollars") is not None: bid = float(ob_m["top_yes_bid_dollars"])
                if ob_m.get("last_price_dollars") is not None: last = float(ob_m["last_price_dollars"])

                executable_price = select_executable_price(ask, last)
                if executable_price is None or executable_price == 0:
                    event_warnings.append(f"{ticker}: No usable price data.")
                    continue

                is_stale = (event_date < now_date_str)
                prob = event_probs.get(normalize_contract_key(bin_str)) if bin_str else None
                
                if prob is None:
                    event_warnings.append(f"{ticker}: Probability for bin {bin_str} not found in forecast.")
                    event_signals.append({
                        "market_ticker": ticker,
                        "event_ticker": m.get("event_ticker"),
                        "market_title": m.get("title"),
                        "status": m.get("status"),
                        "condition_type": mapping.get("condition_type"),
                        "threshold_f": mapping.get("threshold_f"),
                        "contract_range": mapping.get("contract_range"),
                        "model_probability": None,
                        "market_probability": round(executable_price, 4),
                        "paper_action": "NO SIGNAL",
                        "yes_ask": ask, "yes_bid": bid, "last_price": last,
                        "stale": is_stale,
                        "warnings": [f"Probability for bin {bin_str} not found in forecast"]
                    })
                    continue

                # Math and Risk
                edge, raw_edge, fb = calculate_edge(prob, executable_price)
                ev = calculate_expected_value(prob, fb)
                speed, mins = calculate_speed_to_roi(ev, m.get("close_time"))

                from paper_trading.paper_ledger import PaperLedger
                if ledger_path_override:
                    ledger_summary = PaperLedger(ledger_path=ledger_path_override).get_summary()
                else:
                    ledger_summary = PaperLedger().get_summary()

                forecast_risk = dict(forecast_data_obj)
                forecast_risk["dynamic_contract_probabilities"] = event_probs
                
                risk_decision = evaluate_risk_gates(
                    forecast_data=forecast_risk,
                    latest_obs_time_iso=latest_obs_time_iso,
                    model_prob=prob,
                    executable_price=executable_price,
                    yes_ask=ask, yes_bid=bid,
                    edge=edge, raw_edge=raw_edge,
                    ledger_summary=ledger_summary,
                    target_date_str=event_date,
                    best_high_f=forecast_data_obj.get("best_single_number_f"),
                    bin_label=bin_str,
                    contract_bins=markets
                )

                action = "NO EDGE"
                conf = "low"
                if is_stale:
                    action = "NO SIGNAL"; edge = -999.0; ev = -999.0; risk_decision.passed = False
                elif not risk_decision.passed: action = "BLOCKED BY RISK ENGINE"
                elif edge > 0.05:
                    action = "PAPER BUY CANDIDATE"; conf = "medium"
                    if edge > 0.15: conf = "high"
                elif edge > 0: action = "WATCH"

                event_signals.append({
                    "market_ticker": ticker, "event_ticker": m.get("event_ticker"),
                    "market_title": m.get("title"), "status": m.get("status"),
                    "condition_type": mapping.get("condition_type"),
                    "threshold_f": mapping.get("threshold_f"),
                    "range_high_f": mapping.get("range_high_f"),
                    "contract_range": mapping.get("contract_range"),
                    "forecast_bin_label": bin_str,
                    "model_probability": round(prob, 4),
                    "market_probability": round(executable_price, 4),
                    "raw_edge": round(raw_edge, 4), "edge": round(edge, 4),
                    "breakeven_probability": round(fb, 4), "expected_value": round(ev, 4),
                    "speed_to_roi_score": speed, "time_to_close_minutes": mins,
                    "paper_action": action, "confidence": conf,
                    "risk_decision": risk_decision.__dict__,
                    "yes_ask": ask, "yes_bid": bid, "last_price": last,
                    "market_open_time_et": get_market_open_time_et(event_date),
                    "stale": is_stale
                })

        event_signals.sort(key=lambda x: x["edge"] if x.get("edge") is not None else -999.0, reverse=True)
        
        events_by_date[event_date] = {
            "event_ticker": event_ticker,
            "forecast_source": str(f_file.name) if f_file else None,
            "signals": event_signals,
            "dynamic_contract_probabilities": event_probs,
            "status": event_status,
            "warnings": event_warnings
        }
        all_signals.extend(event_signals)
        global_warnings.extend(event_warnings)

    # 5. Consolidation for Backwards Compatibility
    all_signals.sort(key=lambda x: x["edge"] if x.get("edge") is not None else -999.0, reverse=True)
    best_sig = all_signals[0] if all_signals and all_signals[0].get("edge") is not None and all_signals[0]["edge"] > -900 else None
    
    # Identify primary date (the one we want to show in legacy UI)
    primary_date = now_date_str
    if primary_date not in events_by_date and target_dates:
        primary_date = target_dates[0]
        
    primary_event = events_by_date.get(primary_date, {})
    
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary_event_date": primary_date,
        "status": primary_event.get("status", "NO_SIGNAL"),
        "forecast_source": primary_event.get("forecast_source"),
        "market_snapshot_source": str(snapshot_to_use.name) if snapshot_to_use else None,
        "dynamic_contract_probabilities": primary_event.get("dynamic_contract_probabilities", {}),
        "signals": all_signals,
        "best_signal": best_sig,
        "events_by_date": events_by_date,
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

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
from shared.kalshi_market_window import (
    MARKET_STATUS_CLOSED,
    MARKET_STATUS_MISSING_FORECAST,
    MARKET_STATUS_OPEN,
    MARKET_STATUS_PRE_OPEN,
    assess_kalshi_snapshot_freshness,
    classify_market_window,
    is_tradable_market_status,
    is_visible_active_market_status,
    resolve_event_market_status,
)
from trading.edge_engine import calculate_edge, calculate_expected_value, calculate_speed_to_roi, compute_edge
from risk.risk_engine import evaluate_risk_gates, evaluate_risk_decision
from forecasting.contract_probability_mapper import map_contract_probability
from forecasting.distribution_utils import build_integer_distribution_from_bins
from paper_trading.paper_ledger import PaperLedger
from risk.money_distribution import distribute_money

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


# ---------------------------------------------------------------------------
# Private helpers used by generate_paper_signal() below.
#
# These were extracted from a 400+ line monolithic implementation to make the
# per-market signal pipeline readable and individually testable. Behavior is
# unchanged.
# ---------------------------------------------------------------------------


def _extract_market_pricing(
    market: Dict[str, Any], orderbook: Dict[str, Any]
) -> Dict[str, Optional[float]]:
    """Resolve YES ask, bid, and last_price (in dollars) for a market.

    Resolution order:

    1. Snapshot ``*_dollars`` fields on the market.
    2. Cent fallback fields (``yes_ask``, ``yes_bid``, ``last_price``)
       divided by 100.
    3. Orderbook overrides (``top_yes_ask_dollars``,
       ``top_yes_bid_dollars``, ``last_price_dollars``) — these take
       priority over the snapshot when present, because the orderbook
       artifact is fresher than the market snapshot.

    Returns a dict ``{"ask": float|None, "bid": float|None, "last": float|None}``.
    """
    ask = market.get("yes_ask_dollars")
    bid = market.get("yes_bid_dollars")
    last = market.get("last_price_dollars")
    ask = float(ask) if ask is not None else None
    bid = float(bid) if bid is not None else None
    last = float(last) if last is not None else None

    if ask is None and market.get("yes_ask") is not None:
        ask = market.get("yes_ask") / 100.0
    if bid is None and market.get("yes_bid") is not None:
        bid = market.get("yes_bid") / 100.0
    if last is None and market.get("last_price") is not None:
        last = market.get("last_price") / 100.0

    if orderbook.get("top_yes_ask_dollars") is not None:
        ask = float(orderbook["top_yes_ask_dollars"])
    if orderbook.get("top_yes_bid_dollars") is not None:
        bid = float(orderbook["top_yes_bid_dollars"])
    if orderbook.get("last_price_dollars") is not None:
        last = float(orderbook["last_price_dollars"])

    return {"ask": ask, "bid": bid, "last": last}


def _resolve_model_probability_from_bins(
    model_bins: Dict[str, float], bin_str: Optional[str]
) -> Optional[float]:
    """Direct-lookup the model probability for ``bin_str`` in ``model_bins``.

    Matches by :func:`shared.normalization.normalize_contract_key` so
    ``">=87"`` and ``"≥87°F"`` are treated as the same bin. Returns
    ``None`` if the bin is not in ``model_bins`` (so a present-but-zero
    probability is distinguishable from a missing one).
    """
    if not (model_bins and bin_str):
        return None
    norm_bin = normalize_contract_key(bin_str)
    for k, v in model_bins.items():
        if normalize_contract_key(k) == norm_bin:
            return v
    return None


def _build_contract_probability_payload(
    market: Dict[str, Any],
    mapping: Dict[str, Any],
    temp_dist: Optional[Dict[int, float]],
    model_bins: Dict[str, float],
    bin_str: Optional[str],
    is_stale: bool,
) -> Dict[str, Any]:
    """Build the ``contract_prob_payload`` attached to each signal.

    Priority order:

    1. Temperature distribution via
       :func:`forecasting.contract_probability_mapper.map_contract_probability`.
    2. A stub payload marked ``tradable=False`` if no distribution is
       available (kept so downstream consumers always get a well-formed
       payload).
    3. Direct-lookup override against ``model_bins`` for backwards
       compatibility with older v1 forecasts.

    Stale markets are forced to probability 0.0 and ``tradable=False``.
    """
    if temp_dist is not None:
        payload = map_contract_probability(temp_dist, mapping)
    else:
        payload = None

    if payload is None:
        payload = {
            "market_ticker": market.get("ticker"),
            "contract_range_label": bin_str,
            "condition_type": mapping.get("condition_type", "unknown"),
            "threshold_f": mapping.get("threshold_f"),
            "range_high_f": mapping.get("range_high_f"),
            "model_probability": None,
            "tradable": False,
            "warnings": ["No temperature distribution found"],
            "distribution_source": "none",
            "schema_version": "1.0.0",
        }
    else:
        payload = dict(payload)

    if is_stale:
        payload["model_probability"] = 0.0
        payload["tradable"] = False
        payload["warnings"] = list(payload.get("warnings", [])) + ["Market is stale"]

    # Direct-lookup override for backwards compatibility with older
    # forecasts that publish ``model_bins`` directly. We always trust an
    # explicit direct match over the distribution mapping, because the
    # distribution may have rounding artifacts near contract boundaries.
    direct_prob = _resolve_model_probability_from_bins(model_bins, bin_str)
    if direct_prob is not None:
        payload["model_probability"] = direct_prob

    return payload


def _load_event_forecast(
    event_date: str,
    override_forecast_path: Optional[Path],
    override_forecast_date: Optional[str],
) -> Dict[str, Any]:
    """Resolve and load the forecast artifact for a specific event date.

    Search order:

    1. If ``override_forecast_path`` was passed AND its date matches the
       event date, use it directly.
    2. Otherwise, search ``REPORTS_DIR`` for the latest
       ``kmia_forecast_<event_date>_rules_v2_climatology_*`` file.

    The artifact is parsed into ``model_bins`` (label → probability)
    and ``integer_dist`` (1°F-resolution integer distribution). The
    bins come either from the JSON ``probability_bins`` field or from
    parsing the markdown report when no JSON exists.

    Returns a dict with keys:
    ``forecast_path``, ``forecast_data``, ``model_bins``,
    ``integer_dist``, ``status``, ``warnings``.

    On clean load the status is ``"OK"``; missing forecasts produce
    ``"NO_SIGNAL"`` and parser failures produce
    ``"ERROR_LOADING_FORECAST"``.
    """
    result: Dict[str, Any] = {
        "forecast_path": None,
        "forecast_data": {},
        "model_bins": {},
        "integer_dist": {},
        "status": "OK",
        "warnings": [],
    }

    if override_forecast_path and event_date == override_forecast_date:
        f_file: Optional[Path] = override_forecast_path
    else:
        f_file = find_forecast_for_date(event_date)
    result["forecast_path"] = f_file

    if not f_file:
        result["status"] = "NO_SIGNAL"
        result["warnings"].append(f"No forecast artifact found for {event_date}.")
        return result

    try:
        if f_file.suffix == ".md":
            model_bins = parse_forecast_bins_from_md(f_file)
            forecast_data_obj: Dict[str, Any] = {"probability_bins": model_bins, "date": event_date}
            integer_dist: Dict[int, float] = {}
        else:
            with open(f_file, "r") as f:
                forecast_data_obj = json.load(f)
                model_bins = forecast_data_obj.get("probability_bins", {})
                raw_int_dist = forecast_data_obj.get("integer_distribution", {})
                integer_dist = {int(k): v for k, v in raw_int_dist.items()}

        result["forecast_data"] = forecast_data_obj
        result["model_bins"] = model_bins
        result["integer_dist"] = integer_dist

        f_date = forecast_data_obj.get("date")
        if f_date and f_date != event_date:
            result["warnings"].append(
                f"Forecast date {f_date} does not match event date {event_date}. "
                "Signals may be unreliable."
            )
    except Exception as e:
        result["status"] = "ERROR_LOADING_FORECAST"
        result["warnings"].append(f"Error loading forecast {f_file.name}: {e}")
        return result

    if not model_bins and result["status"] == "OK":
        result["status"] = "NO_SIGNAL"
        result["warnings"].append(f"Forecast for {event_date} contains no probability bins.")

    return result


def _forecast_has_distribution(model_bins: Dict[str, float], integer_dist: Dict[int, float]) -> bool:
    """True when a forecast artifact has bins or integer_distribution for mapping."""
    return bool(integer_dist) or bool(model_bins)


def _build_event_contracts(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Lightweight contract list for events_by_date visibility (no fake prices)."""
    contracts: List[Dict[str, Any]] = []
    for m in markets:
        mapping = m.get("contract_mapping", {})
        contract_bin = m.get("contract_bin") or {}
        bin_str = contract_bin.get("label") if contract_bin else mapping_to_bin_string(mapping)
        contracts.append({
            "ticker": m.get("ticker"),
            "event_ticker": m.get("event_ticker"),
            "kalshi_status": m.get("status"),
            "contract_range": mapping.get("contract_range"),
            "forecast_bin_label": bin_str,
            "title": m.get("title"),
        })
    return contracts


def _contract_untradeable_for_window(market_status: str) -> bool:
    """Contracts on CLOSED/PRE_OPEN dates are not paper-tradable."""
    return market_status in (MARKET_STATUS_CLOSED, MARKET_STATUS_PRE_OPEN)


def _append_contract_rows_without_forecast(
    markets: List[Dict[str, Any]],
    all_orderbooks: Dict[str, Any],
    event_date: str,
    market_status: str,
    event_warnings: List[str],
    event_signals: List[Dict[str, Any]],
    weather_gate: Dict[str, Any],
) -> None:
    """Emit one signal row per contract when forecast distribution is missing (no fake probs)."""
    msg = f"Forecast distribution missing for {event_date}"
    if msg not in event_warnings:
        event_warnings.append(msg)

    untradeable = _contract_untradeable_for_window(market_status)

    for m in markets:
        ticker = m.get("ticker")
        mapping = m.get("contract_mapping", {})
        bin_str = m.get("contract_bin", {}).get("label") if m.get("contract_bin") else mapping_to_bin_string(mapping)
        prices = _extract_market_pricing(m, all_orderbooks.get(ticker, {}))
        ask, bid, last = prices["ask"], prices["bid"], prices["last"]
        executable_price = select_executable_price(ask, last)

        if executable_price is None or executable_price == 0:
            event_warnings.append(f"{ticker}: No usable price data.")
            continue

        if not weather_gate.get("allow_paper_recommendations", False):
            p_action = "NO TRADE"
            p_risk_dec: Any = "BLOCK"
            p_no_trade_reason = weather_gate.get("no_trade_reason")
        elif untradeable:
            p_action = "NO SIGNAL"
            p_risk_dec = {"decision": "BLOCK", "reason": f"Market window status: {market_status}"}
            p_no_trade_reason = f"Market window status: {market_status}"
        else:
            p_action = "NO SIGNAL"
            p_risk_dec = None
            p_no_trade_reason = msg

        event_signals.append({
            "market_ticker": ticker,
            "event_ticker": m.get("event_ticker"),
            "market_title": m.get("title"),
            "status": m.get("status"),
            "condition_type": mapping.get("condition_type"),
            "threshold_f": mapping.get("threshold_f"),
            "range_high_f": mapping.get("range_high_f"),
            "contract_range": mapping.get("contract_range"),
            "forecast_bin_label": bin_str,
            "model_probability": None,
            "market_probability": round(executable_price, 4),
            "executable_price": round(executable_price, 4),
            "paper_action": p_action,
            "risk_decision": p_risk_dec,
            "no_trade_reason": p_no_trade_reason,
            "weather_gate_status": weather_gate.get("status"),
            "market_status": market_status,
            "yes_ask": ask,
            "yes_bid": bid,
            "last_price": last,
            "stale": untradeable,
            "warnings": [msg],
        })


def _resolve_temp_distribution(
    model_bins: Dict[str, float],
    integer_dist: Dict[int, float],
    nws_snapshot: Optional[Dict[str, Any]],
    event_date: str,
) -> Optional[Dict[int, float]]:
    """Choose the 1°F-resolution distribution to feed the contract mapper.

    Priority:

    1. The forecast's own ``integer_distribution`` (preferred — produced
       by the v2 climatology model).
    2. A reconstructed distribution from coarse ``model_bins`` via
       :func:`forecasting.distribution_utils.build_integer_distribution_from_bins`
       (used for v1 forecasts and tests that don't supply a full
       distribution).
    3. ``None`` if neither is available.

    The ``observed_max_so_far_f`` from the NWS snapshot is passed
    through to the reconstruction so already-realized temperatures
    zero out the lower bins.
    """
    if integer_dist:
        return integer_dist
    if model_bins:
        observed_max = nws_snapshot.get("observed_max_so_far_f") if nws_snapshot else None
        return build_integer_distribution_from_bins(
            probability_bins=model_bins,
            observed_max_so_far_f=observed_max,
            station="KMIA",
            target_date=event_date,
        )
    return None


def _decide_paper_action(
    edge: float,
    is_stale: bool,
    risk_decision: Dict[str, Any],
    weather_gate: Dict[str, Any],
) -> Dict[str, Any]:
    """Assign paper-trading action, confidence, and propagated risk fields.

    Resolution order (first matching rule wins):

    1. ``is_stale`` → ``NO SIGNAL`` with synthesized BLOCK risk decision.
    2. Risk engine voted BLOCK → ``NO TRADE``.
    3. ``edge >= 0.05`` → ``PAPER BUY CANDIDATE`` (``high`` if
       ``edge >= 0.15``, else ``medium``).
    4. ``0 < edge < 0.05`` → ``WATCH``.
    5. ``edge <= 0`` → ``NO EDGE``.

    After the above, the NWS weather gate acts as a strict fail-closed
    override: if ``allow_paper_recommendations`` is ``False``, the
    action is forced to ``NO TRADE`` regardless of the edge.

    Returns ``{"action", "confidence", "risk_decision_val", "no_trade_reason_val"}``.
    """
    action = "NO EDGE"
    conf = "low"

    if is_stale:
        action = "NO SIGNAL"
        risk_decision_val: Any = {
            "decision": "BLOCK",
            "reason": "Market is stale",
            "gates_evaluated": (
                risk_decision.get("gates_evaluated", {})
                if isinstance(risk_decision, dict) else {}
            ),
        }
        no_trade_reason_val = "Market is stale"
    elif risk_decision.get("decision") == "BLOCK":
        action = "NO TRADE"
        risk_decision_val = risk_decision
        no_trade_reason_val = risk_decision.get("reason")
    elif edge >= 0.05:
        action = "PAPER BUY CANDIDATE"
        conf = "high" if edge >= 0.15 else "medium"
        risk_decision_val = risk_decision
        no_trade_reason_val = risk_decision.get("reason")
    elif edge > 0.0:
        action = "WATCH"
        risk_decision_val = risk_decision
        no_trade_reason_val = risk_decision.get("reason")
    else:
        action = "NO EDGE"
        risk_decision_val = risk_decision
        no_trade_reason_val = risk_decision.get("reason")

    if not weather_gate.get("allow_paper_recommendations", False):
        action = "NO TRADE"
        risk_decision_val = "BLOCK"
        no_trade_reason_val = weather_gate.get("no_trade_reason")

    return {
        "action": action,
        "confidence": conf,
        "risk_decision_val": risk_decision_val,
        "no_trade_reason_val": no_trade_reason_val,
    }


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
    ledger_path_override: Optional[Path] = None,
    allocation_mode: Optional[str] = None
):
    """Generates a quantitative edge report comparing model vs market using active contracts."""
    out_dir = output_dir if output_dir else OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    
    if prediction_timestamp is None:
        prediction_timestamp = datetime.now(timezone.utc)
    
    # Use US/Eastern local date for staleness checks to avoid UTC rollover issues.
    now_date_str = prediction_timestamp.astimezone(ZoneInfo("US/Eastern")).strftime("%Y-%m-%d")

    # 1. Load NWS snapshot and assess freshness gate
    nws_snapshot = None
    try:
        if NWS_SNAPSHOT_FILE.exists():
            with open(NWS_SNAPSHOT_FILE, "r") as _f:
                nws_snapshot = json.load(_f)
        else:
            logger.warning(f"NWS snapshot not found at {NWS_SNAPSHOT_FILE}.")
    except Exception as _e:
        logger.warning(f"Could not load NWS snapshot for freshness gate check: {_e}.")

    from weather.nws_snapshot_contract import assess_nws_snapshot
    weather_gate = assess_nws_snapshot(nws_snapshot, now_utc=prediction_timestamp)
    latest_obs_time_iso = nws_snapshot.get("latest_observation_time") if nws_snapshot else None

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
    if not all_discovered_markets:
        msg = "No active Kalshi high-temperature contracts discovered."
        logger.warning(msg)
        global_warnings = [
            "Kalshi market snapshot is missing or contains no active KXHIGHMIA markets. Running in restricted no-trade mode."
        ]
        
        if ledger_path_override:
            ledger = PaperLedger(ledger_path_override)
        else:
            ledger = PaperLedger()
        ledger_summary = ledger.get_summary()
        alloc_mode = allocation_mode or os.environ.get("KALSHI_ALLOCATION_MODE", "risk_adjusted").lower()
        money_dist_report = distribute_money(
            bankroll=ledger_summary.get("account_balance", 1000.0),
            active_signals=[],
            forecast_data={},
            weather_gate=weather_gate,
            ledger_summary=ledger_summary,
            target_date=now_date_str,
            mode=alloc_mode,
            config=None
        )

        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "primary_event_date": now_date_str,
            "status": "NO_SIGNAL",
            "forecast_source": None,
            "market_snapshot_source": str(snapshot_to_use.name) if snapshot_to_use else None,
            "dynamic_contract_probabilities": {},
            "signals": [],
            "best_signal": None,
            "events_by_date": {},
            "money_distribution": money_dist_report,
            "warnings": global_warnings,
            "weather_gate": weather_gate,
            "allow_paper_recommendations": False,
            "no_trade_reason": msg,
            "safety": {
                "no_real_trading": True,
                "no_order_execution": True,
                "disclaimer": "NO REAL TRADING EXECUTION - PAPER ONLY"
            }
        }
        
        latest_path = latest_path_override if latest_path_override else LATEST_PAPER_SIGNAL
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        ts_path = out_dir / f"paper_signal_{ts}.json"
        
        with open(latest_path, "w") as f:
            json.dump(report, f, indent=2)
        with open(ts_path, "w") as f:
            json.dump(report, f, indent=2)
            
        return latest_path

    markets_by_date = {}
    for m in all_discovered_markets:
        ticker_date = parse_ticker_date(m.get("ticker"))
        if ticker_date:
            markets_by_date.setdefault(ticker_date, []).append(m)

    snapshot_freshness = assess_kalshi_snapshot_freshness(
        snapshot_to_use, now_utc=prediction_timestamp
    )
    global_warnings: List[str] = list(snapshot_freshness.get("warnings", []))

    # 4. Process each event date
    events_by_date = {}
    all_signals = []
    
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
        event_ticker = markets[0].get("event_ticker") if markets else None
        contracts_meta = _build_event_contracts(markets)

        window_info = classify_market_window(event_date, prediction_timestamp)
        window_status = window_info["market_status"]

        forecast_load = _load_event_forecast(
            event_date=event_date,
            override_forecast_path=forecast_path,
            override_forecast_date=override_forecast_date,
        )
        f_file = forecast_load["forecast_path"]
        model_bins = forecast_load["model_bins"]
        integer_dist = forecast_load["integer_dist"]
        event_status = forecast_load["status"]
        event_warnings = list(forecast_load["warnings"])
        event_signals: List[Dict[str, Any]] = []
        event_probs: Dict[str, float] = {}

        has_forecast_dist = _forecast_has_distribution(model_bins, integer_dist)
        if not has_forecast_dist and forecast_load["status"] == "OK":
            event_status = "NO_SIGNAL"
            event_warnings.append(f"Forecast distribution missing for {event_date}")

        market_status = resolve_event_market_status(
            window_status=window_status,
            snapshot_stale=snapshot_freshness.get("is_stale", False),
            has_contracts=bool(markets),
            has_forecast_distribution=has_forecast_dist,
        )
        contract_untradeable = _contract_untradeable_for_window(market_status)

        # Calculate probabilities and signals for this date
        if has_forecast_dist:
            temp_dist_to_use = _resolve_temp_distribution(
                model_bins=model_bins,
                integer_dist=integer_dist,
                nws_snapshot=nws_snapshot,
                event_date=event_date,
            )

            # Pre-compute probabilities using map_contract_probability dynamically
            for m in markets:
                ticker = m.get("ticker")
                mapping = m.get("contract_mapping", {})
                contract_bin_data = m.get("contract_bin")

                bin_str = contract_bin_data.get("label") if contract_bin_data else mapping_to_bin_string(mapping)

                if contract_untradeable:
                    prob = 0.0
                else:
                    prob = None
                    # When the forecast JSON contains a real integer_distribution
                    # (per-degree probabilities from the v2 climatology model),
                    # integrate over the contract range first.  This handles
                    # fine-grained Kalshi contracts (87-88, 89-90, 91-92, >=93,
                    # <=84, etc.) that don’t appear as labels in the 6-bin
                    # coarse model_bins.
                    if integer_dist and temp_dist_to_use is not None:
                        res_prob = map_contract_probability(temp_dist_to_use, mapping)
                        prob = res_prob.get("model_probability")
                    # Legacy path (v1 forecasts or tests): direct label lookup in
                    # coarse model_bins.  Fall back to distribution reconstruction
                    # only when the label is absent.
                    if prob is None:
                        prob = _resolve_model_probability_from_bins(model_bins, bin_str)
                    if prob is None and not integer_dist and temp_dist_to_use is not None:
                        res_prob = map_contract_probability(temp_dist_to_use, mapping)
                        prob = res_prob.get("model_probability")

                if prob is not None:
                    norm_key = normalize_contract_key(bin_str) if bin_str else ticker
                    event_probs[norm_key] = prob

            # Generate signals
            for m in markets:
                ticker = m.get("ticker")
                mapping = m.get("contract_mapping", {})
                bin_str = m.get("contract_bin", {}).get("label") if m.get("contract_bin") else mapping_to_bin_string(mapping)

                prices = _extract_market_pricing(m, all_orderbooks.get(ticker, {}))
                ask, bid, last = prices["ask"], prices["bid"], prices["last"]

                executable_price = select_executable_price(ask, last)
                if executable_price is None or executable_price == 0:
                    event_warnings.append(f"{ticker}: No usable price data.")
                    continue

                contract_prob_payload = _build_contract_probability_payload(
                    market=m,
                    mapping=mapping,
                    temp_dist=temp_dist_to_use,
                    model_bins=model_bins,
                    bin_str=bin_str,
                    is_stale=contract_untradeable,
                )
                prob = contract_prob_payload.get("model_probability")

                # A bin is "explicitly missing" only when there is NO real
                # integer_distribution from the forecast AND the coarse model_bins
                # does not list this contract bin.  When the JSON forecast provides
                # integer_distribution, the range integration above already computed
                # the correct probability — we must not override that with a label-
                # lookup failure against the 6-bin coarse model_bins.
                is_missing_from_model_bins = bool(
                    not integer_dist              # no real integer distribution
                    and model_bins                # but coarse bins exist
                    and bin_str
                    and _resolve_model_probability_from_bins(model_bins, bin_str) is None
                )

                if prob is None or is_missing_from_model_bins:
                    event_warnings.append(f"{ticker}: Probability for bin {bin_str} not found in forecast.")
                    if not weather_gate.get("allow_paper_recommendations", False):
                        p_action = "NO TRADE"
                        p_risk_dec: Any = "BLOCK"
                        p_no_trade_reason = weather_gate.get("no_trade_reason")
                    else:
                        p_action = "NO SIGNAL"
                        p_risk_dec = None
                        p_no_trade_reason = f"Probability for bin {bin_str} not found in forecast"

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
                        "paper_action": p_action,
                        "risk_decision": p_risk_dec,
                        "no_trade_reason": p_no_trade_reason,
                        "weather_gate_status": weather_gate.get("status"),
                        "yes_ask": ask,
                        "yes_bid": bid,
                        "last_price": last,
                        "market_status": market_status,
                        "stale": contract_untradeable,
                        "warnings": [f"Probability for bin {bin_str} not found in forecast"],
                    })
                    continue

                # Compute fee- and slippage-aware trading edge.
                edge_payload = compute_edge(
                    model_probability=prob,
                    yes_ask=ask,
                    yes_bid=bid,
                    last_price=last,
                    slippage_buffer=0.0,
                )

                edge = edge_payload.get("executable_edge", 0.0)
                raw_edge = edge_payload.get("raw_edge", 0.0)
                fb = edge_payload.get("breakeven_probability", 0.0)

                ev = calculate_expected_value(prob, fb)
                speed, mins = calculate_speed_to_roi(ev, m.get("close_time"))

                # Evaluate risk decision (fail-closed check).
                risk_decision = evaluate_risk_decision(
                    weather_gate=weather_gate,
                    contract_probability=contract_prob_payload,
                    edge=edge_payload,
                    manual_kill_switch=False,
                    min_executable_edge=0.0,
                    max_spread=0.15,
                    near_boundary_risk=False,
                )

                # Closed/pre-open markets get sentinel edge/EV values so they sort last.
                if contract_untradeable:
                    edge = -999.0
                    ev = -999.0

                action_info = _decide_paper_action(
                    edge=edge,
                    is_stale=contract_untradeable,
                    risk_decision=risk_decision,
                    weather_gate=weather_gate,
                )

                event_signals.append({
                    "market_ticker": ticker,
                    "event_ticker": m.get("event_ticker"),
                    "market_title": m.get("title"),
                    "status": m.get("status"),
                    "condition_type": mapping.get("condition_type"),
                    "threshold_f": mapping.get("threshold_f"),
                    "range_high_f": mapping.get("range_high_f"),
                    "contract_range": mapping.get("contract_range"),
                    "forecast_bin_label": bin_str,
                    "model_probability": round(prob, 4),
                    "market_probability": round(executable_price, 4),
                    "executable_price": round(executable_price, 4) if executable_price is not None else None,
                    "raw_edge": round(raw_edge, 4),
                    "edge": round(edge, 4),
                    "executable_edge": round(edge, 4),
                    "breakeven_probability": round(fb, 4),
                    "expected_value": round(ev, 4),
                    "speed_to_roi_score": speed,
                    "time_to_close_minutes": mins,
                    "paper_action": action_info["action"],
                    "confidence": action_info["confidence"],
                    "risk_decision": action_info["risk_decision_val"],
                    "no_trade_reason": action_info["no_trade_reason_val"],
                    "weather_gate_status": weather_gate.get("status"),
                    "yes_ask": ask,
                    "yes_bid": bid,
                    "last_price": last,
                    "market_open_time_et": get_market_open_time_et(event_date),
                    "market_status": market_status,
                    "stale": contract_untradeable,
                    "warnings": list(set(contract_prob_payload.get("warnings", []) + edge_payload.get("warnings", [])))
                })

        else:
            _append_contract_rows_without_forecast(
                markets=markets,
                all_orderbooks=all_orderbooks,
                event_date=event_date,
                market_status=market_status,
                event_warnings=event_warnings,
                event_signals=event_signals,
                weather_gate=weather_gate,
            )

        event_signals.sort(key=lambda x: x["edge"] if x.get("edge") is not None else -999.0, reverse=True)
        
        events_by_date[event_date] = {
            "market_date": event_date,
            "event_ticker": event_ticker,
            "market_status": market_status,
            "open_start_et": window_info["open_start_et"],
            "open_end_et": window_info["open_end_et"],
            "snapshot_fetched_at_utc": snapshot_freshness.get("fetched_at_utc"),
            "snapshot_age_minutes": snapshot_freshness.get("snapshot_age_minutes"),
            "contracts": contracts_meta,
            "forecast_source": str(f_file.name) if f_file else None,
            "forecast_data": forecast_load.get("forecast_data", {}),
            "signals": event_signals,
            "dynamic_contract_probabilities": event_probs if has_forecast_dist else {},
            "status": event_status,
            "warnings": event_warnings,
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
    
    # Run Money Distribution Engine for primary event date
    if ledger_path_override:
        ledger = PaperLedger(ledger_path_override)
    else:
        ledger = PaperLedger()
    ledger_summary = ledger.get_summary()
    
    primary_event_status = primary_event.get("market_status", "")
    primary_signals = [
        sig for sig in all_signals
        if parse_ticker_date(sig["market_ticker"]) == primary_date
        and is_tradable_market_status(primary_event_status)
    ]
    primary_forecast = primary_event.get("forecast_data", {})
    
    alloc_mode = allocation_mode
    if not alloc_mode:
        alloc_mode = os.environ.get("KALSHI_ALLOCATION_MODE", "risk_adjusted").lower()
    if alloc_mode not in ("guarantee_profit", "risk_adjusted", "conservative"):
        alloc_mode = "risk_adjusted"
        
    money_dist_report = distribute_money(
        bankroll=ledger_summary.get("account_balance", 1000.0),
        active_signals=primary_signals,
        forecast_data=primary_forecast,
        weather_gate=weather_gate,
        ledger_summary=ledger_summary,
        target_date=primary_date,
        mode=alloc_mode,
        config=None
    )
    
    open_market_dates = sorted(
        d for d, ev in events_by_date.items()
        if is_visible_active_market_status(ev.get("market_status", ""))
    )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary_event_date": primary_date,
        "status": primary_event.get("status", "NO_SIGNAL"),
        "forecast_source": primary_event.get("forecast_source"),
        "market_snapshot_source": str(snapshot_to_use.name) if snapshot_to_use else None,
        "market_snapshot": {
            "path": str(snapshot_to_use) if snapshot_to_use else None,
            "fetched_at_utc": snapshot_freshness.get("fetched_at_utc"),
            "snapshot_age_minutes": snapshot_freshness.get("snapshot_age_minutes"),
            "max_age_minutes": snapshot_freshness.get("max_age_minutes"),
            "is_stale": snapshot_freshness.get("is_stale", False),
        },
        "open_market_dates": open_market_dates,
        "dynamic_contract_probabilities": primary_event.get("dynamic_contract_probabilities", {}),
        "signals": all_signals,
        "best_signal": best_sig,
        "events_by_date": events_by_date,
        "money_distribution": money_dist_report,
        "warnings": list(set(global_warnings)),
        "weather_gate": weather_gate,
        "allow_paper_recommendations": weather_gate.get("allow_paper_recommendations", False),
        "no_trade_reason": weather_gate.get("no_trade_reason"),
        "safety": {
            "no_real_trading": True,
            "no_order_execution": True,
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

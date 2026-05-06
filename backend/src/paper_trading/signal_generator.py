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

# Resolve ROOT
ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = ROOT / "backend" / "data" / "processed" / "reports"
SNAPSHOT_FILE = ROOT / "backend" / "data" / "processed" / "kalshi_market_snapshots" / "latest_kalshi_market_snapshot.json"
OUTPUT_DIR = ROOT / "backend" / "data" / "processed" / "paper_trading"

# Model Bins Definition
BIN_RANGES = {
    "<=78": (None, 78),
    "79-80": (79, 80),
    "81-82": (81, 82),
    "83-84": (83, 84),
    "85-86": (85, 86),
    ">=87": (87, None)
}

def get_latest_file(directory: Path, pattern: str) -> Optional[Path]:
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

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

def estimate_contract_probability(mapping: Dict[str, Any], model_bins: Dict[str, float]) -> tuple:
    """
    Estimates the probability of a contract condition based on model bins.
    Returns (probability, warnings)
    """
    cond = mapping.get("condition_type")
    t = mapping.get("threshold_f")
    h = mapping.get("range_high_f")
    
    if cond == "unknown" or t is None:
        return None, ["Unknown contract condition or missing threshold."]
    
    total_prob = 0.0
    matched_any = False
    uncertain = False
    
    for bin_label, (b_low, b_high) in BIN_RANGES.items():
        prob = model_bins.get(bin_label, 0.0)
        
        # Above T
        if cond == "above":
            # If bin is strictly above T
            if b_low is not None and b_low > t:
                total_prob += prob
                matched_any = True
            elif b_high is not None and b_high <= t:
                # Bin is strictly below T, ignore
                pass
            else:
                # T falls inside the bin
                uncertain = True
                
        # Below T
        elif cond == "below":
            if b_high is not None and b_high < t:
                total_prob += prob
                matched_any = True
            elif b_low is not None and b_low >= t:
                pass
            else:
                uncertain = True
                
        # Between T and H
        elif cond == "between":
            if b_low is not None and b_high is not None and b_low >= t and b_high <= h:
                total_prob += prob
                matched_any = True
            elif (b_high is not None and b_high < t) or (b_low is not None and b_low > h):
                pass
            else:
                uncertain = True
                
    if uncertain:
        # For KMIA, if T is an integer like 86, and bin is 85-86, then "above 86" means >= 87.
        # Let's try a small refinement for integer boundaries.
        if cond == "above" and t.is_integer():
             # Re-check above T as >= T+1
             pass # Already handled by b_low > t if b_low is T+1
        return None, [f"Contract boundary {t} cuts through model bins. Exact mapping uncertain."]

    if not matched_any and total_prob == 0:
        # Check if condition is beyond range
        if cond == "above" and t >= 87:
             return 0.0, ["Threshold above model's max bin boundary (87). Probability likely > 0 but unquantifiable."]
        if cond == "below" and t <= 78:
             return 0.0, ["Threshold below model's min bin boundary (78). Probability likely > 0 but unquantifiable."]
             
    return total_prob, []

def calculate_speed_to_roi(ev: float, close_time_iso: Optional[str]) -> tuple:
    """Calculates ROI speed score. (Expected Value / Time to Close)"""
    if not close_time_iso:
        return 0.0, None
        
    try:
        close_dt = datetime.fromisoformat(close_time_iso.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        diff = close_dt - now_dt
        minutes = max(diff.total_seconds() / 60.0, 1.0) # Min 1 min
        
        # Simple score: ROI % per hour or similar. 
        # Here: EV per 100 minutes.
        score = (ev / minutes) * 1000.0 if ev > 0 else 0.0
        return round(score, 2), round(minutes, 1)
    except:
        return 0.0, None

def generate_paper_signal():
    """Generates a quantitative edge report comparing model vs market using active contracts."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Load Latest Forecast
    latest_forecast = get_latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.md")
    model_bins = parse_forecast_bins_from_md(latest_forecast) if latest_forecast else {}
    
    # 2. Load and Map Active Markets
    markets = parse_kalshi_markets(SNAPSHOT_FILE)
    
    signals = []
    global_warnings = []
    
    if not model_bins:
        global_warnings.append("No forecast bins available. Ensure daily workflow ran.")
    if not markets:
        global_warnings.append("No active KMIA Kalshi markets available in snapshot.")

    for m in markets:
        ticker = m.get("ticker")
        mapping = m.get("contract_mapping", {})
        
        prob, map_warnings = estimate_contract_probability(mapping, model_bins)
        
        if prob is None:
            if map_warnings:
                global_warnings.extend([f"{ticker}: {w}" for w in map_warnings])
            continue
            
        # Extract Market Price
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

        market_prob = ask if ask is not None else last
        
        if market_prob is None or market_prob == 0:
            global_warnings.append(f"{ticker}: No usable price data. Skipping.")
            continue
            
        edge = prob - market_prob
        cost = ask if ask is not None else market_prob
        ev = (prob * 1.0) - cost
        
        speed_score, mins_to_close = calculate_speed_to_roi(ev, m.get("close_time"))
        
        # Action logic
        action = "NO EDGE"
        confidence = "low"
        if edge > 0.05:
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
            "model_probability": round(prob, 4),
            "market_probability": round(market_prob, 4),
            "edge": round(edge, 4),
            "expected_value": round(ev, 4),
            "speed_to_roi_score": speed_score,
            "time_to_close_minutes": mins_to_close,
            "paper_action": action,
            "confidence": confidence,
            "yes_ask": ask,
            "yes_bid": bid,
            "last_price": last,
            "market_open_time_et": get_market_open_time_et(parse_ticker_date(ticker)) if ticker else None
        })

    signals.sort(key=lambda x: x["edge"], reverse=True)
    best_signal = signals[0] if signals else None
    
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_source": str(latest_forecast.name) if latest_forecast else None,
        "market_snapshot_source": str(SNAPSHOT_FILE.name),
        "signals": signals,
        "best_signal": best_signal,
        "warnings": list(set(global_warnings)),
        "safety": {
            "no_real_trading": True,
            "disclaimer": "NO REAL TRADING EXECUTION - PAPER ONLY"
        }
    }
    
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    latest_path = OUTPUT_DIR / "latest_paper_signal.json"
    ts_path = OUTPUT_DIR / f"paper_signal_{ts}.json"
    
    with open(latest_path, "w") as f:
        json.dump(report, f, indent=2)
    with open(ts_path, "w") as f:
        json.dump(report, f, indent=2)
        
    return latest_path

if __name__ == "__main__":
    path = generate_paper_signal()
    print(f"Paper signal report generated at {path}")

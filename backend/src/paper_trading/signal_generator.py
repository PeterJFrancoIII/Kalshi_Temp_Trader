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

# Resolve ROOT
ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = ROOT / "backend" / "data" / "processed" / "reports"
SNAPSHOT_FILE = ROOT / "backend" / "data" / "processed" / "kalshi_market_snapshots" / "latest_kalshi_market_snapshot.json"
OUTPUT_DIR = ROOT / "backend" / "data" / "processed" / "paper_trading"

def get_latest_file(directory: Path, pattern: str) -> Optional[Path]:
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def parse_forecast_bins_from_md(md_path: Path) -> Dict[str, float]:
    """Parses probability bins from a forecast markdown report."""
    if not md_path.exists():
        return {}
    
    with open(md_path, "r") as f:
        content = f.read()
    
    bins = {}
    # Pattern to match table rows like | 81-82 | 8.5% | or | >=87 | 33.9% |
    pattern = r"\|\s*([<>=]*\d+[-\d]*)\s*\|\s*(\d+\.?\d*)%\s*\|"
    matches = re.findall(pattern, content)
    for bin_label, prob_str in matches:
        bins[bin_label] = float(prob_str) / 100.0
    
    return bins

def map_market_to_bin(m: Dict[str, Any], model_bins: Dict[str, float]) -> Dict[str, Any]:
    """
    Maps a Kalshi market to model bins and calculates the total model probability.
    Returns { "bin_label": "...", "model_prob": 0.0, "warnings": [] }
    """
    title = m.get("title", "").lower()
    subtitle = m.get("subtitle", "").lower()
    text = (title + " " + subtitle).replace("\u00b0", "deg") # Handle degree symbol
    
    res = { "bin_label": "Unknown", "model_prob": 0.0, "warnings": [] }
    
    # 1. Extract Range from Kalshi
    k_low = -float('inf')
    k_high = float('inf')
    
    # Patterns for Ranges
    range_match = re.search(r"(\d+)(?:\s*deg|\s*degrees)?\s*(?:to|-|and)\s*(\d+)", text)
    if range_match:
        k_low = int(range_match.group(1))
        k_high = int(range_match.group(2))
    
    # Patterns for Upper Thresholds
    above_match = re.search(r"(\d+)\s*(?:deg|degrees)?\s*or\s*above", text)
    if not range_match and above_match:
        k_low = int(above_match.group(1))
    elif not range_match:
        above_match = re.search(r"(?:above\s+|>\s*)(\d+)", text)
        if above_match:
            k_low = int(above_match.group(1)) + 1
            if ">=" in text: k_low -= 1

    # Patterns for Lower Thresholds
    below_match = re.search(r"(\d+)\s*(?:deg|degrees)?\s*or\s*below", text)
    if not range_match and below_match:
        k_high = int(below_match.group(1))
    elif not range_match:
        below_match = re.search(r"(?:below\s+|<\s*)(\d+)", text)
        if below_match:
            k_high = int(below_match.group(1)) - 1
            if "<=" in text: k_high += 1
    
    if k_low == -float('inf') and k_high == float('inf'):
        res["warnings"].append(f"Could not parse range from: {subtitle}")
        return res

    # 2. Map to Model Bins
    # Model bins are: <=78, 79-80, 81-82, 83-84, 85-86, >=87
    matched_bins = []
    total_prob = 0.0
    
    for b_label, b_prob in model_bins.items():
        # Parse model bin range
        m_low = -float('inf')
        m_high = float('inf')
        
        if "-" in b_label:
            m_low, m_high = map(int, b_label.split("-"))
        elif "<=" in b_label:
            m_high = int(b_label.replace("<=", ""))
        elif ">=" in b_label:
            m_low = int(b_label.replace(">=", ""))
            
        # Check overlap: max(start) <= min(end)
        overlap_start = max(k_low, m_low)
        overlap_end = min(k_high, m_high)
        
        if overlap_start <= overlap_end:
            matched_bins.append(b_label)
            total_prob += b_prob
            
    if matched_bins:
        res["bin_label"] = "/".join(matched_bins) if len(matched_bins) > 1 else matched_bins[0]
        res["model_prob"] = total_prob
    else:
        res["warnings"].append(f"No model bin overlap for Kalshi range {k_low}-{k_high}")
        
    return res

def generate_paper_signal():
    """Generates a quantitative edge report comparing model vs market."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Load Latest Forecast
    latest_forecast = get_latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.md")
    model_bins = parse_forecast_bins_from_md(latest_forecast) if latest_forecast else {}
    
    # 2. Load Latest Kalshi Snapshot
    market_data = {}
    if SNAPSHOT_FILE.exists():
        try:
            with open(SNAPSHOT_FILE, "r") as f:
                market_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load market snapshot: {e}")
    
    markets = market_data.get("selected_temperature_markets", [])
    if not markets:
        markets = market_data.get("markets", []) # Fallback to generic list
    
    signals = []
    warnings = []
    
    if not model_bins:
        warnings.append("No forecast bins available. Ensure daily workflow ran.")
    if not markets:
        warnings.append("No Kalshi markets available in snapshot.")

    for m in markets:
        ticker = m.get("ticker")
        mapping = map_market_to_bin(m, model_bins)
        
        if mapping["bin_label"] == "Unknown":
            if mapping["warnings"]:
                warnings.extend([f"{ticker}: {w}" for w in mapping["warnings"]])
            continue
            
        model_prob = mapping["model_prob"]
        
        # Extract Market Price (0.0 - 1.0)
        # Check for both cents (yes_ask) and dollars (yes_ask_dollars)
        ask = m.get("yes_ask_dollars")
        bid = m.get("yes_bid_dollars")
        last = m.get("last_price_dollars")
        
        # Fallback to cents if dollars missing
        if ask is None and m.get("yes_ask") is not None:
            ask = m.get("yes_ask") / 100.0
        else:
            ask = float(ask) if ask is not None else None
            
        if bid is None and m.get("yes_bid") is not None:
            bid = m.get("yes_bid") / 100.0
        else:
            bid = float(bid) if bid is not None else None

        if last is None and m.get("last_price") is not None:
            last = m.get("last_price") / 100.0
        else:
            last = float(last) if last is not None else None

        # Determine Implied Prob
        market_prob = None
        if ask is not None:
            market_prob = ask
        elif last is not None:
            market_prob = last
        
        if market_prob is None:
            warnings.append(f"{ticker}: No usable price data (yes_ask or last_price). Skipping.")
            continue
            
        edge = model_prob - market_prob
        # Expected Value for a $1 payoff
        cost = ask if ask is not None else market_prob
        ev = (model_prob * 1.0) - cost
        
        # Action logic
        action = "NO EDGE"
        confidence = "low"
        if edge > 0.05: # > 5% edge
            action = "PAPER BUY CANDIDATE"
            confidence = "medium"
            if edge > 0.15: # > 15% edge
                confidence = "high"
        elif edge > 0:
            action = "WATCH"
        
        signals.append({
            "market_ticker": ticker,
            "market_title": m.get("title"),
            "forecast_bin": mapping["bin_label"],
            "model_probability": round(model_prob, 4),
            "market_implied_probability": round(market_prob, 4),
            "edge": round(edge, 4),
            "expected_value": round(ev, 4),
            "paper_action": action,
            "confidence": confidence,
            "yes_ask": ask,
            "yes_bid": bid,
            "last_price": last
        })

    # Sort signals by edge descending
    signals.sort(key=lambda x: x["edge"] if x["edge"] is not None else -1.0, reverse=True)
    
    best_signal = signals[0] if signals else None
    
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_source": str(latest_forecast.name) if latest_forecast else None,
        "market_snapshot_source": str(SNAPSHOT_FILE.name),
        "signals": signals,
        "best_signal": best_signal,
        "warnings": list(set(warnings)),
        "safety": {
            "no_real_trading": True,
            "disclaimer": "NO REAL TRADING EXECUTION - PAPER ONLY"
        }
    }
    
    # Save reports
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

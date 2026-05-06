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

def map_market_to_bin(title: str) -> Optional[str]:
    """Maps Kalshi market titles to our internal bin labels."""
    title = title.lower()
    
    # "between 81 and 82" -> "81-82"
    between_match = re.search(r"between\s+(\d+)\s+and\s+(\d+)", title)
    if between_match:
        return f"{between_match.group(1)}-{between_match.group(2)}"
    
    # "87 degrees or above" -> ">=87"
    above_match = re.search(r"(\d+)\s+degrees\s+or\s+above", title)
    if above_match:
        return f">={above_match.group(1)}"
        
    # "78 degrees or below" -> "<=78"
    below_match = re.search(r"(\d+)\s+degrees\s+or\s+below", title)
    if below_match:
        return f"<={below_match.group(1)}"
        
    return None

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
    for m in markets:
        ticker = m.get("ticker")
        title = m.get("title", "")
        bin_label = map_market_to_bin(title)
        
        # We need a match in our model bins to calculate edge
        if not bin_label or bin_label not in model_bins:
            continue
            
        model_prob = model_bins[bin_label]
        
        # Extract Market Implied Probability
        # yes_bid/yes_ask are in cents (0-100)
        bid = m.get("yes_bid")
        ask = m.get("yes_ask")
        
        market_prob = None
        if bid is not None and ask is not None:
            market_prob = (bid + ask) / 200.0 # Midpoint as 0.0 - 1.0
        elif ask is not None:
            market_prob = ask / 100.0 # Conservative: assume ask
        elif bid is not None:
            market_prob = bid / 100.0 # Optimistic: assume bid
            
        edge = None
        ev = None
        action = "NO EDGE"
        confidence = "low"
        
        if market_prob is not None:
            edge = model_prob - market_prob
            # Expected Value for a $1 payoff (100 cents)
            # EV = (Prob of Win * Payoff) - Cost
            cost = ask / 100.0 if ask is not None else market_prob
            ev = (model_prob * 1.0) - cost
            
            # Action logic
            if edge > 0.05: # > 5% edge
                action = "PAPER BUY CANDIDATE"
                confidence = "medium"
                if edge > 0.15: # > 15% edge
                    confidence = "high"
            elif edge > 0:
                action = "WATCH"
                confidence = "low"
        
        signals.append({
            "ticker": ticker,
            "bin": bin_label,
            "title": title,
            "model_prob": round(model_prob, 4),
            "market_prob": round(market_prob, 4) if market_prob is not None else None,
            "edge": round(edge, 4) if edge is not None else None,
            "expected_value": round(ev, 4) if ev is not None else None,
            "action": action,
            "confidence": confidence
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

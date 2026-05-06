import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

logger = logging.getLogger(__name__)

# Resolve ROOT
ROOT = Path(__file__).resolve().parents[3]
SIGNAL_FILE = ROOT / "backend" / "data" / "processed" / "paper_trading" / "latest_paper_signal.json"
LEDGER_FILE = ROOT / "backend" / "data" / "processed" / "paper_trading" / "paper_trade_ledger.jsonl"

def record_paper_trade():
    """
    Reads the latest paper signal and records a trade in the ledger if an edge is found.
    """
    if not SIGNAL_FILE.exists():
        logger.warning(f"No signal file found at {SIGNAL_FILE}")
        return
    
    try:
        with open(SIGNAL_FILE, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load signal file: {e}")
        return

    best_signal = data.get("best_signal")
    if not best_signal:
        logger.info("No best signal found in report.")
        return

    action = best_signal.get("action")
    if action != "PAPER BUY CANDIDATE":
        logger.info(f"Signal action is {action}, not PAPER BUY CANDIDATE. No trade recorded.")
        return

    ticker = best_signal.get("ticker")
    if not ticker:
        logger.warning("Signal missing ticker.")
        return

    # Check for duplicates (same ticker on same day)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("market_ticker") == ticker and entry.get("timestamp_utc", "").startswith(today):
                        logger.info(f"Trade for {ticker} already recorded today.")
                        return
                except json.JSONDecodeError:
                    continue

    # Record simulated trade
    trade = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "market_ticker": ticker,
        "forecast_bin": best_signal.get("bin"),
        "model_probability": best_signal.get("model_prob"),
        "market_probability": best_signal.get("market_prob"),
        "edge": best_signal.get("edge"),
        "simulated_entry_price": best_signal.get("market_prob"), # Simplified: buy at market prob
        "paper_action": action,
        "status": "OPEN",
        "safety": "NO REAL TRADING EXECUTION"
    }

    os.makedirs(LEDGER_FILE.parent, exist_ok=True)
    with open(LEDGER_FILE, "a") as f:
        f.write(json.dumps(trade) + "\n")
    
    logger.info(f"Recorded paper trade for {ticker}")
    return trade

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    record_paper_trade()

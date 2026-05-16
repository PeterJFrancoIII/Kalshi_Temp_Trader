import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

logger = logging.getLogger(__name__)

from paper_trading.paper_ledger import PaperLedger
from paper_trading.settlement import parse_ticker_date

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

logger = logging.getLogger(__name__)

# Resolve ROOT
ROOT = Path(__file__).resolve().parents[3]
SIGNAL_FILE = ROOT / "backend" / "data" / "processed" / "paper_trading" / "latest_paper_signal.json"

def signal_market_probability(best_signal: Dict[str, Any]) -> Any:
    """Return the market probability using the current field name first."""
    current = best_signal.get("market_probability")
    if current is not None:
        return current
    return best_signal.get("market_implied_probability")

def signal_entry_price(best_signal: Dict[str, Any]) -> Any:
    """Return the simulated entry price without treating valid 0.0 as missing."""
    yes_ask = best_signal.get("yes_ask")
    if yes_ask is not None:
        return yes_ask
    return signal_market_probability(best_signal)

def record_paper_trade():
    """
    Reads the latest paper signal and records a trade in the ledger if an edge is found.
    Uses the canonical PaperLedger (ledger.json).
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

    action = best_signal.get("paper_action")
    if action != "PAPER BUY CANDIDATE":
        logger.info(f"Signal action is {action}, not PAPER BUY CANDIDATE. No trade recorded.")
        return

    ticker = best_signal.get("market_ticker")
    if not ticker:
        logger.warning("Signal missing market_ticker.")
        return

    target_date = best_signal.get("target_date") or parse_ticker_date(ticker)
    if not target_date:
        logger.warning(f"Could not determine target date for ticker {ticker}")
        return

    ledger = PaperLedger()
    summary = ledger.get_summary()
    
    # Check for duplicates
    for trade in ledger.ledger_data.get("trades", []):
        if trade.get("market_ticker") == ticker and trade.get("target_date") == target_date:
            logger.info(f"Trade for {ticker} ({target_date}) already recorded in ledger.")
            return

    # Record simulated trade
    ledger.record_trade(
        market_ticker=ticker,
        target_date=target_date,
        execution_price=signal_entry_price(best_signal),
        quantity=1, # Default paper quantity
        model_probability=best_signal.get("model_probability"),
        forecast_bin=best_signal.get("forecast_bin_label") or best_signal.get("forecast_bin")
    )

    logger.info(f"Recorded paper trade for {ticker} in ledger.json")
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    record_paper_trade()

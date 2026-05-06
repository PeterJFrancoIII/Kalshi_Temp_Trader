import json
import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

try:
    from forecasting.bin_converter import temp_to_bin
except ImportError:
    # Fallback for bare execution or tests
    def temp_to_bin(temp):
        if temp <= 78: return "<=78"
        if 79 <= temp <= 80: return "79-80"
        if 81 <= temp <= 82: return "81-82"
        if 83 <= temp <= 84: return "83-84"
        if 85 <= temp <= 86: return "85-86"
        return ">=87"

logger = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).resolve().parents[3]
PAPER_DIR = ROOT / "backend" / "data" / "processed" / "paper_trading"
LEDGER_FILE = PAPER_DIR / "paper_trade_ledger.jsonl"
SETTLEMENTS_FILE = PAPER_DIR / "paper_trade_settlements.jsonl"
PERFORMANCE_FILE = PAPER_DIR / "latest_paper_trading_performance.json"
HISTORY_FILE = ROOT / "backend" / "data" / "processed" / "history" / "kmia_daily_history.jsonl"

def parse_ticker_date(ticker: str) -> Optional[str]:
    """
    Parses date from ticker like KXHIGHMIA-26MAY06-B84.5
    Returns YYYY-MM-DD string.
    """
    # Pattern: KXHIGHMIA-YYMONDD
    match = re.search(r"([0-9]{2})([A-Z]{3})([0-9]{2})", ticker)
    if not match:
        return None
    
    year_short, mon_str, day_str = match.groups()
    year = f"20{year_short}"
    
    months = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
    }
    month = months.get(mon_str.upper())
    if not month:
        return None
        
    return f"{year}-{month}-{day_str}"

def load_history() -> Dict[str, int]:
    """Loads history as a map of date -> tmax_f"""
    history = {}
    if not HISTORY_FILE.exists():
        return history
    
    try:
        with open(HISTORY_FILE, "r") as f:
            for line in f:
                if not line.strip(): continue
                data = json.loads(line)
                date = data.get("date")
                tmax = data.get("tmax_f")
                if date and tmax is not None:
                    history[date] = int(tmax)
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        
    return history

def settle_paper_trades():
    """
    Main settlement loop.
    """
    if not LEDGER_FILE.exists():
        logger.info("No ledger file found. Nothing to settle.")
        return

    history = load_history()
    
    # Load existing settlements to avoid duplicates
    settled_tickers = set()
    if SETTLEMENTS_FILE.exists():
        with open(SETTLEMENTS_FILE, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    settled_tickers.add(f"{data['trade_date']}_{data['market_ticker']}")
                except:
                    continue

    new_settlements = []
    pending_count = 0

    with open(LEDGER_FILE, "r") as f:
        for line in f:
            try:
                trade = json.loads(line)
                if trade.get("status") != "OPEN":
                    continue
                
                ticker = trade.get("market_ticker")
                trade_date = parse_ticker_date(ticker)
                
                if not trade_date:
                    logger.warning(f"Could not parse date from ticker: {ticker}")
                    continue
                
                # Check if already settled
                if f"{trade_date}_{ticker}" in settled_tickers:
                    continue
                    
                actual_max = history.get(trade_date)
                
                if actual_max is not None:
                    actual_bin = temp_to_bin(actual_max)
                    forecast_bin = trade.get("forecast_bin", "")
                    
                    # Logic: WIN if actual_bin is in forecast_bin (handling "/" separator)
                    bins_covered = [b.strip() for b in forecast_bin.split("/")]
                    is_won = actual_bin in bins_covered
                    
                    entry_price = trade.get("simulated_entry_price", 0)
                    pnl = 1.00 - entry_price if is_won else -entry_price
                    
                    settlement = {
                        "settled_at_utc": datetime.now(timezone.utc).isoformat(),
                        "trade_date": trade_date,
                        "market_ticker": ticker,
                        "forecast_bin": forecast_bin,
                        "actual_max_temp_f": actual_max,
                        "actual_bin": actual_bin,
                        "result": "WON" if is_won else "LOST",
                        "simulated_entry_price": entry_price,
                        "simulated_pnl": round(pnl, 4),
                        "model_probability": trade.get("model_probability"),
                        "market_probability": trade.get("market_probability"),
                        "edge": trade.get("edge"),
                        "safety": "NO REAL TRADING EXECUTION"
                    }
                    new_settlements.append(settlement)
                    logger.info(f"Settled {ticker} on {trade_date}: {settlement['result']} (High: {actual_max})")
                else:
                    pending_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing trade line: {e}")

    # Append new settlements
    if new_settlements:
        with open(SETTLEMENTS_FILE, "a") as f:
            for s in new_settlements:
                f.write(json.dumps(s) + "\n")
                
    # Generate Performance Summary
    generate_performance_summary(pending_count)

def generate_performance_summary(pending_count: int = 0):
    """
    Reads all settlements and computes aggregate stats.
    """
    settlements = []
    if SETTLEMENTS_FILE.exists():
        with open(SETTLEMENTS_FILE, "r") as f:
            for line in f:
                try:
                    settlements.append(json.loads(line))
                except:
                    continue

    summary = {
        "total_settled_trades": len(settlements),
        "wins": sum(1 for s in settlements if s["result"] == "WON"),
        "losses": sum(1 for s in settlements if s["result"] == "LOST"),
        "win_rate": 0,
        "total_simulated_pnl": round(sum(s["simulated_pnl"] for s in settlements), 4),
        "average_edge": 0,
        "average_entry_price": 0,
        "best_trade": None,
        "worst_trade": None,
        "pending_trades": pending_count,
        "warnings": [],
        "safety": {"no_real_trading": True}
    }

    if summary["total_settled_trades"] > 0:
        summary["win_rate"] = round(summary["wins"] / summary["total_settled_trades"], 4)
        summary["average_edge"] = round(sum(s.get("edge", 0) for s in settlements) / summary["total_settled_trades"], 4)
        summary["average_entry_price"] = round(sum(s["simulated_entry_price"] for s in settlements) / summary["total_settled_trades"], 4)
        
        # Best/Worst by PnL
        sorted_by_pnl = sorted(settlements, key=lambda x: x["simulated_pnl"], reverse=True)
        summary["best_trade"] = sorted_by_pnl[0]
        summary["worst_trade"] = sorted_by_pnl[-1]

    with open(PERFORMANCE_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Performance summary generated at {PERFORMANCE_FILE}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    settle_paper_trades()

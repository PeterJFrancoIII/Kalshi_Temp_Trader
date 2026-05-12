import json
import os
import re
import logging
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

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

try:
    from shared.manual_corrections import get_correction_for_date, is_excluded_from_learning
except ImportError:
    # Fallback if PYTHONPATH is not set correctly during tests
    def get_correction_for_date(date_str): return {}
    def is_excluded_from_learning(date_str): return False

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

def _temp_satisfies_bin_label(temp: int, bin_label: str) -> bool:
    """
    Returns True if *temp* falls within *bin_label*.

    Supports both legacy fixed-bin labels (<=78, 79-80, 83-84, >=87)
    and dynamic Kalshi labels (<=89, 91-92, >=95, <86, >84).
    Labels are matched by evaluating the boundary expression directly,
    so this works correctly for any threshold — unlike temp_to_bin() which
    only maps to the 6 hardcoded legacy buckets.
    """
    label = (bin_label or "").strip()
    if not label:
        return False
    try:
        if label.startswith("<="):
            return temp <= float(label[2:])
        if label.startswith(">="):
            return temp >= float(label[2:])
        if label.startswith("<"):
            return temp < float(label[1:])
        if label.startswith(">"):
            return temp > float(label[1:])
        if "-" in label:
            parts = label.split("-", 1)
            lo, hi = float(parts[0]), float(parts[1])
            return lo <= temp <= hi
        return temp == float(label)
    except (ValueError, TypeError):
        return False


def _load_trades_from_ledger(ledger_path: Path) -> List[Dict[str, Any]]:
    """
    Loads trade records from either format:

    - JSON object  (new PaperLedger): ``{"trades": [...], "account_balance": ...}``
    - JSONL        (legacy format):   one JSON object per line

    Returns a list of trade dicts.  Never raises; logs warnings on failure.
    """
    try:
        with open(ledger_path, "r") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Could not read ledger {ledger_path}: {e}")
        return []

    # Try JSON object format first (new PaperLedger)
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "trades" in data:
            return list(data.get("trades", []))
    except json.JSONDecodeError:
        pass

    # Fall back to JSONL (one JSON object per line)
    trades: List[Dict[str, Any]] = []
    for lineno, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            trades.append(json.loads(line))
        except json.JSONDecodeError as e:
            logger.warning(
                f"Ledger {ledger_path.name} line {lineno}: "
                f"JSON parse error — {e}. Line skipped."
            )
    return trades


def _update_json_ledger_pnl(
    ledger_path: Path,
    settlements_by_key: Dict[Tuple[str, str], Dict[str, Any]],
) -> None:
    """
    Writes realized PnL and ``status="settled"`` back into a JSON-object-format
    PaperLedger for each trade key in *settlements_by_key*.

    This is the F1 fix: makes daily_pnl / weekly_pnl in PaperLedger.get_summary()
    reflect actual settled outcomes so that risk Gates 7 and 8 can fire.

    No-op if the ledger is not in JSON object format (e.g. legacy JSONL).
    """
    if not settlements_by_key:
        return
    try:
        with open(ledger_path, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "trades" not in data:
            return  # Not JSON object format — skip silently

        changed = False
        for trade in data["trades"]:
            key = (trade.get("market_ticker"), trade.get("target_date"))
            if key in settlements_by_key:
                val = settlements_by_key[key]
                trade["pnl"] = val["pnl"]
                trade["settled_at_utc"] = val["settled_at_utc"]
                trade["status"] = "settled"
                changed = True

        if changed:
            with open(ledger_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(
                f"Wrote realized PnL for {len(settlements_by_key)} trade(s) "
                f"back into JSON ledger {ledger_path.name}."
            )
    except Exception as e:
        logger.warning(
            f"Could not write settlement PnL back to JSON ledger "
            f"{ledger_path.name}: {e}"
        )


def settle_paper_trades(
    ledger_path: Optional[Path] = None,
    settlements_path: Optional[Path] = None,
    performance_path: Optional[Path] = None,
    settlement_as_of_time: Optional[datetime] = None,
):
    """
    Main settlement loop.

    Args:
        ledger_path: Path to the paper trade ledger (JSONL or JSON).
        settlements_path: Path to write settlements JSONL.
        performance_path: Path to write performance summary JSON.
        settlement_as_of_time: UTC datetime representing the simulated "now" for
            settlement purposes.  A trade's settlement data is only available
            after this time is past the day following the trade date at
            DEFAULT_SETTLEMENT_AVAILABILITY_HOUR_UTC (06:00 UTC by default).

            In backtest replay, set this to the simulated current time so that
            same-day or next-day-before-06:00 trades are NOT prematurely settled.

            If None, defaults to datetime.now(UTC) — appropriate for live/paper
            paper trading where real-world time is the constraint.

    Settlement availability rule:
        settlement becomes available at 06:00 UTC on (trade_date + 1 day).
        Trades whose settlement window has not yet opened return PENDING status.
    """
    # Default to real wall-clock time (safe for live paper trading)
    if settlement_as_of_time is None:
        settlement_as_of_time = datetime.now(timezone.utc)
    ledger = ledger_path if ledger_path else LEDGER_FILE
    settlements_file = settlements_path if settlements_path else SETTLEMENTS_FILE

    if not ledger.exists():
        logger.info("No ledger file found. Nothing to settle.")
        return

    history = load_history()

    # Load existing settlements to avoid duplicates
    settled_tickers: set = set()
    if settlements_file.exists():
        with open(settlements_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    settled_tickers.add(f"{data['trade_date']}_{data['market_ticker']}")
                except Exception:
                    continue

    new_settlements: List[Dict[str, Any]] = []
    pending_count = 0
    # F1: track (ticker, target_date) -> {pnl, settled_at_utc} for JSON ledger writeback
    settlements_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

    # F4: load trades from either JSON object or JSONL format
    all_trades = _load_trades_from_ledger(ledger)

    for trade in all_trades:
        try:
            # F4: normalize status — handle both "open" (new PaperLedger) and "OPEN" (legacy)
            if trade.get("status", "").upper() != "OPEN":
                continue

            ticker = trade.get("market_ticker")
            trade_date = parse_ticker_date(ticker)

            if not trade_date:
                logger.warning(f"Could not parse date from ticker: {ticker}")
                continue

            # Settlement availability guard
            # Official KMIA daily high is published by NWS at ~06:00 UTC the next day.
            # We must not settle a trade before that time in backtest mode.
            try:
                trade_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                logger.warning(f"Could not parse trade_date: {trade_date}")
                continue

            # Settlement is available at 06:00 UTC on (trade_date + 1 day)
            settlement_available_at = (
                trade_date_obj + timedelta(days=1)
            ).replace(hour=6, minute=0, second=0, microsecond=0)

            if settlement_as_of_time < settlement_available_at:
                logger.debug(
                    f"Settlement not yet available for {ticker}: "
                    f"settlement_as_of={settlement_as_of_time.isoformat()}, "
                    f"available_at={settlement_available_at.isoformat()}"
                )
                pending_count += 1
                continue

            # Check if already settled
            if f"{trade_date}_{ticker}" in settled_tickers:
                continue

            correction = get_correction_for_date(trade_date)
            corrected_max = correction.get("corrected_official_max_temp_f")
            history_max = history.get(trade_date)

            # Rule: If correction exists, it is the authority. 
            # But if it differs from history by >= 1°F, flag for review.
            actual_max = corrected_max if corrected_max is not None else history_max

            if actual_max is not None:
                actual_max = int(actual_max)
                
                # DSM/CLI Mismatch check
                mismatch = False
                if corrected_max is not None and history_max is not None:
                    if abs(int(corrected_max) - int(history_max)) >= 1:
                        logger.warning(
                            f"DSM/CLI Mismatch on {trade_date}: "
                            f"History={history_max}, Correction={corrected_max}. "
                            f"Marking as NEEDS_MANUAL_REVIEW."
                        )
                        mismatch = True
                forecast_bin = trade.get("forecast_bin", "")

                # F3: use _temp_satisfies_bin_label so dynamic bin labels (>=95, <=89,
                # 91-92) work correctly in addition to legacy fixed-bin labels.
                bins_covered = [b.strip() for b in forecast_bin.split("/") if b.strip()]
                is_won = any(
                    _temp_satisfies_bin_label(actual_max, b) for b in bins_covered
                )

                # F4: support both new (execution_price) and legacy (simulated_entry_price)
                entry_price = (
                    trade.get("execution_price")
                    if trade.get("execution_price") is not None
                    else trade.get("simulated_entry_price", 0)
                )
                pnl = 1.00 - entry_price if is_won else -entry_price

                result_str = "WON" if is_won else "LOST"
                if mismatch or correction.get("settlement_status") == "needs_manual_review":
                    result_str = "NEEDS_MANUAL_REVIEW"

                actual_bin = temp_to_bin(actual_max)
                settlement = {
                    "settled_at_utc": datetime.now(timezone.utc).isoformat(),
                    "trade_date": trade_date,
                    "market_ticker": ticker,
                    "forecast_bin": forecast_bin,
                    "actual_max_temp_f": actual_max,
                    "actual_bin": actual_bin,
                    "result": result_str,
                    "simulated_entry_price": entry_price,
                    "simulated_pnl": round(pnl, 4),
                    "model_probability": trade.get("model_probability"),
                    "market_probability": trade.get("market_probability"),
                    "edge": trade.get("edge"),
                    "correction_source": (
                        "manual_operator_override"
                        if correction.get("corrected_official_max_temp_f") is not None
                        else None
                    ),
                    "exclude_from_learning": correction.get("exclude_from_learning", False),
                    "safety": "NO REAL TRADING EXECUTION",
                }
                new_settlements.append(settlement)
                # F1: record for JSON ledger PnL writeback
                settlements_by_key[(ticker, trade_date)] = {
                    "pnl": round(pnl, 4),
                    "settled_at_utc": settlement["settled_at_utc"]
                }
                logger.info(
                    f"Settled {ticker} on {trade_date}: "
                    f"{settlement['result']} (High: {actual_max})"
                )
            else:
                pending_count += 1

        except Exception as e:
            logger.error(f"Error processing trade record: {e}")

    # Append new settlements
    if new_settlements:
        with open(settlements_file, "a") as f:
            for s in new_settlements:
                f.write(json.dumps(s) + "\n")

    # F1: write realized PnL back into JSON-format ledger so that
    # PaperLedger.get_summary() can aggregate daily_pnl / weekly_pnl
    # and risk Gates 7 and 8 can actually fire.
    if settlements_by_key:
        _update_json_ledger_pnl(ledger, settlements_by_key)

    # Generate Performance Summary
    generate_performance_summary(
        pending_count, settlements_path=settlements_file, performance_path=performance_path
    )

def generate_performance_summary(
    pending_count: int = 0,
    settlements_path: Optional[Path] = None,
    performance_path: Optional[Path] = None
):
    """
    Reads all settlements and computes aggregate stats.
    """
    settlements_file = settlements_path if settlements_path else SETTLEMENTS_FILE
    perf_file = performance_path if performance_path else PERFORMANCE_FILE
    
    settlements = []
    if settlements_file.exists():
        with open(settlements_file, "r") as f:
            for line in f:
                try:
                    settlements.append(json.loads(line))
                except:
                    continue

    # Filter out excluded trades and those needing manual review for performance metrics
    valid_settlements = [s for s in settlements if not s.get("exclude_from_learning", False) and s["result"] != "NEEDS_MANUAL_REVIEW"]
    
    summary = {
        "total_settled_trades": len(valid_settlements),
        "wins": sum(1 for s in valid_settlements if s["result"] == "WON"),
        "losses": sum(1 for s in valid_settlements if s["result"] == "LOST"),
        "win_rate": 0,
        "total_simulated_pnl": round(sum(s["simulated_pnl"] for s in valid_settlements), 4),
        "average_edge": 0,
        "average_entry_price": 0,
        "best_trade": None,
        "worst_trade": None,
        "pending_trades": pending_count,
        "excluded_trades": len(settlements) - len(valid_settlements),
        "warnings": [],
        "safety": {"no_real_trading": True}
    }

    if summary["total_settled_trades"] > 0:
        summary["win_rate"] = round(summary["wins"] / summary["total_settled_trades"], 4)
        # Use `or 0` to guard against None edge/price values in settlement records
        summary["average_edge"] = round(
            sum((s.get("edge") or 0) for s in settlements)
            / summary["total_settled_trades"], 4
        )
        summary["average_entry_price"] = round(
            sum((s.get("simulated_entry_price") or 0) for s in settlements)
            / summary["total_settled_trades"], 4
        )
        
        # Best/Worst by PnL
        sorted_by_pnl = sorted(valid_settlements, key=lambda x: x["simulated_pnl"], reverse=True)
        summary["best_trade"] = sorted_by_pnl[0]
        summary["worst_trade"] = sorted_by_pnl[-1]

    with open(perf_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Performance summary generated at {perf_file}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    settle_paper_trades()

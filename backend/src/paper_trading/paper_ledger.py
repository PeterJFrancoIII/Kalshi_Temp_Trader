import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from shared.artifact_paths import PAPER_LEDGER_FILE

logger = logging.getLogger(__name__)

class PaperLedger:
    def __init__(self, ledger_path: Path = PAPER_LEDGER_FILE):
        self.ledger_path = ledger_path
        self.ledger_data = self._load_ledger()
        
    def _load_ledger(self) -> Dict[str, Any]:
        if not self.ledger_path.exists():
            return {
                "account_balance": 1000.0,
                "trades": [],
                "created_at_utc": datetime.now(timezone.utc).isoformat()
            }
        try:
            with open(self.ledger_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading ledger: {e}")
            return {"account_balance": 1000.0, "trades": []}

    def _save_ledger(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "w") as f:
            json.dump(self.ledger_data, f, indent=2)

    @property
    def trades(self) -> List[Dict[str, Any]]:
        """Read-only view of trades in the ledger."""
        return list(self.ledger_data.get("trades", []))

    def count_open_trades(self) -> int:
        """Number of trades whose status is 'open' (case-insensitive).

        This is the canonical replacement for older callers that scanned
        a `paper_trade_ledger.jsonl` file by line count, which conflated
        "all trades" with "open trades" and silently returned 0 when the
        file was absent in production.
        """
        return sum(
            1
            for trade in self.ledger_data.get("trades", [])
            if str(trade.get("status", "")).lower() == "open"
        )

    def get_summary(self) -> Dict[str, Any]:
        """Calculates daily_pnl, weekly_pnl, and active_trades_by_date for RiskEngine."""
        now = datetime.now(timezone.utc)
        
        daily_pnl = 0.0
        weekly_pnl = 0.0
        active_trades_by_date = {}
        
        for trade in self.ledger_data.get("trades", []):
            try:
                # Use settled_at_utc if available for PnL windowing, otherwise fallback to trade timestamp
                settle_ts_str = trade.get("settled_at_utc")
                pnl_ts = datetime.fromisoformat(settle_ts_str.replace("Z", "+00:00")) if settle_ts_str else None
                trade_ts = datetime.fromisoformat(trade.get("timestamp_utc", "").replace("Z", "+00:00"))
                
                # Window comparison timestamp
                window_ts = pnl_ts if pnl_ts else trade_ts
                
                trade_date = trade.get("target_date")
                pnl = trade.get("pnl", 0.0)
                status = str(trade.get("status", "closed")).lower()
                
                # Time deltas (24h and 7d)
                if (now - window_ts).total_seconds() <= 24 * 3600:
                    daily_pnl += pnl
                if (now - window_ts).total_seconds() <= 7 * 24 * 3600:
                    weekly_pnl += pnl
                    
                # Active trades (open only)
                if status == "open" and trade_date:
                    active_trades_by_date[trade_date] = active_trades_by_date.get(trade_date, 0) + 1
            except Exception as e:
                logger.warning(f"Error parsing trade record in ledger: {e}")

        return {
            "account_balance": self.ledger_data.get("account_balance", 0.0),
            "daily_pnl": daily_pnl,
            "weekly_pnl": weekly_pnl,
            "active_trades_by_date": active_trades_by_date
        }

    def update_trade_status(
        self, 
        market_ticker: str, 
        target_date: str, 
        status: str, 
        pnl: float = 0.0,
        settled_at_utc: Optional[str] = None
    ):
        """Updates the status and PnL of an existing trade."""
        changed = False
        for trade in self.ledger_data.get("trades", []):
            if trade.get("market_ticker") == market_ticker and trade.get("target_date") == target_date:
                trade["status"] = status
                trade["pnl"] = pnl
                if settled_at_utc:
                    trade["settled_at_utc"] = settled_at_utc
                elif status.lower() == "settled" and "settled_at_utc" not in trade:
                    trade["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                changed = True
        
        if changed:
            self._save_ledger()
            logger.info(f"Updated status for {market_ticker} ({target_date}) to {status}")
        else:
            logger.warning(f"No trade found to update: {market_ticker} for {target_date}")

    def record_trade(
        self,
        market_ticker: str,
        target_date: str,
        execution_price: float,
        quantity: int,
        model_probability: Optional[float] = None,
        forecast_bin: Optional[str] = None,
        condition_type: Optional[str] = None,
        threshold_f: Optional[float] = None,
        range_high_f: Optional[float] = None,
        lower_inclusive: Optional[bool] = None,
        upper_inclusive: Optional[bool] = None,
        contract_range_label: Optional[str] = None,
        risk_decision: Optional[Any] = None,
        no_trade_reason: Optional[str] = None,
        weather_gate_status: Optional[str] = None,
    ):
        """Records a new paper trade.

        Args:
            market_ticker: Kalshi market ticker string.
            target_date: YYYY-MM-DD string for the event date.
            execution_price: Simulated fill price (0-1 range).
            quantity: Number of contracts.
            model_probability: The model's estimated probability at trade time.
                Stored for Brier/CRPS scoring at settlement.
            forecast_bin: The forecast bin or condition description (e.g. ">=87").
                Stored for settlement bin-match logic.
        """
        # Fallback boundary extraction if missing
        if lower_inclusive is None or upper_inclusive is None or condition_type is None:
            try:
                from market_data.kalshi_contract_mapper import extract_contract_thresholds
                m = {
                    "ticker": market_ticker,
                    "title": "",
                    "floor_strike": threshold_f,
                    "cap_strike": range_high_f,
                }
                mapping = extract_contract_thresholds(m)
                if lower_inclusive is None:
                    lower_inclusive = mapping.get("lower_inclusive")
                if upper_inclusive is None:
                    upper_inclusive = mapping.get("upper_inclusive")
                if condition_type is None:
                    condition_type = mapping.get("condition_type")
                if threshold_f is None:
                    threshold_f = mapping.get("threshold_f")
                if range_high_f is None:
                    range_high_f = mapping.get("range_high_f")
            except Exception:
                pass

        trade = {
            "market_ticker": market_ticker,
            "target_date": target_date,
            "execution_price": execution_price,
            "quantity": quantity,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": "open",
            "pnl": 0.0,  # Open trade has 0 realized PnL initially
            "model_probability": model_probability,
            "forecast_bin": forecast_bin,
            "condition_type": condition_type,
            "threshold_f": threshold_f,
            "range_high_f": range_high_f,
            "lower_inclusive": lower_inclusive,
            "upper_inclusive": upper_inclusive,
            "contract_range_label": contract_range_label,
            "risk_decision": risk_decision,
            "no_trade_reason": no_trade_reason,
            "weather_gate_status": weather_gate_status,
        }
        self.ledger_data.setdefault("trades", []).append(trade)
        # We don't deduct cost from account_balance right away if we just track PnL upon settlement
        # For a full mock we'd deduct cost and track open positions.
        self._save_ledger()


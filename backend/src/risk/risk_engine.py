import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class RiskDecision:
    def __init__(self, passed: bool, reason: str = "OK"):
        self.passed = passed
        self.reason = reason
        
    def __repr__(self):
        return f"RiskDecision(passed={self.passed}, reason={self.reason})"

def check_kill_switch() -> RiskDecision:
    """Gate 10: Manual Kill Switch."""
    if os.environ.get("KALSHI_KILL_SWITCH", "").lower() == "true":
        return RiskDecision(False, "Blocked by KALSHI_KILL_SWITCH environment variable.")
        
    from shared.artifact_paths import ROOT_DIR
    if (ROOT_DIR / ".kill_switch").exists():
        return RiskDecision(False, "Blocked by .kill_switch file in workspace root.")
        
    return RiskDecision(True)

def check_weather_data_availability(forecast_data: Dict[str, Any]) -> RiskDecision:
    """Gate 1: TWC/NWS Data Availability."""
    if not forecast_data:
        return RiskDecision(False, "No forecast data available.")
        
    warnings = forecast_data.get("warnings", [])
    if any("missing credentials" in w.lower() or "api error" in w.lower() for w in warnings):
        return RiskDecision(False, "Blocked due to API missing credentials or error.")
        
    return RiskDecision(True)

def check_weather_freshness(latest_obs_time_iso: Optional[str]) -> RiskDecision:
    """Gate 2: Weather Freshness."""
    if not latest_obs_time_iso:
        return RiskDecision(False, "Missing latest observation time.")
        
    try:
        obs_dt = datetime.fromisoformat(latest_obs_time_iso.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        if (now_dt - obs_dt).total_seconds() > 90 * 60:
            return RiskDecision(False, f"Weather observation is stale (>90 mins old): {latest_obs_time_iso}")
        return RiskDecision(True)
    except Exception:
        return RiskDecision(False, "Invalid weather observation time format.")

def check_forecast_confidence(forecast_data: Dict[str, Any]) -> RiskDecision:
    """Gate 3: Forecast Confidence."""
    # Look for warnings indicating low confidence or conflicting models
    warnings = forecast_data.get("warnings", [])
    if any("stale" in w.lower() or "low confidence" in w.lower() for w in warnings):
        return RiskDecision(False, "Blocked due to low forecast confidence or stale NWS data.")
    return RiskDecision(True)

def check_near_boundary_settlement(model_prob: float, raw_edge: float) -> RiskDecision:
    """Gate 4: Near-Boundary Settlement Risk."""
    # E.g. if probability is 51% and price is 49%, edge is small but we might be precariously close
    # to a boundary. For this heuristic, if raw_edge < 0.10 and model_prob is near 0.5 (0.4-0.6), block.
    if 0.40 <= model_prob <= 0.60 and raw_edge < 0.10:
        return RiskDecision(False, "Blocked due to near-boundary settlement risk (model prob near 50% and edge is low).")
    return RiskDecision(True)

def check_liquidity_and_spread(yes_ask: Optional[float], yes_bid: Optional[float]) -> RiskDecision:
    """Gate 5: Liquidity/Spread.

    Blocks if:
    - Either price is missing (illiquid market).
    - bid >= ask (crossed or zero-spread market — data integrity failure).
    - Spread > 0.15 (market too wide to trade profitably).
    """
    if yes_ask is None or yes_bid is None:
        return RiskDecision(False, "Missing bid or ask (illiquid market).")

    # CM1: Block crossed markets (bid >= ask). A bid equal to or greater than
    # the ask indicates either a data feed error or a crossed book — neither is
    # safe to trade against.
    if yes_bid >= yes_ask:
        return RiskDecision(
            False,
            f"Crossed or zero-spread market: bid ({yes_bid:.4f}) >= ask ({yes_ask:.4f}). "
            f"Data integrity issue — not safe to trade."
        )

    spread = yes_ask - yes_bid
    if spread > 0.15:
        return RiskDecision(False, f"Bid-ask spread too wide ({spread:.2f} > 0.15).")
    return RiskDecision(True)

def check_fee_adjusted_edge(edge: float, min_edge: float = 0.05) -> RiskDecision:
    """Gate 6: Fee-Adjusted Edge."""
    if edge < min_edge:
        return RiskDecision(False, f"Fee-adjusted edge ({edge:.4f}) below minimum threshold ({min_edge}).")
    return RiskDecision(True)

def check_daily_loss_limit(ledger_summary: Dict[str, float]) -> RiskDecision:
    """Gate 7: Daily Loss Limit."""
    daily_pnl = ledger_summary.get("daily_pnl", 0.0)
    if daily_pnl < -50.0:  # Simulate a $50 paper loss limit
        return RiskDecision(False, f"Daily loss limit exceeded: ${daily_pnl:.2f}")
    return RiskDecision(True)

def check_weekly_drawdown_limit(ledger_summary: Dict[str, float]) -> RiskDecision:
    """Gate 8: Weekly Drawdown Limit."""
    weekly_pnl = ledger_summary.get("weekly_pnl", 0.0)
    if weekly_pnl < -150.0: # Simulate a $150 paper drawdown limit
        return RiskDecision(False, f"Weekly drawdown limit exceeded: ${weekly_pnl:.2f}")
    return RiskDecision(True)

def check_market_concentration(ledger_summary: Dict[str, Any], date_str: str) -> RiskDecision:
    """Gate 9: Market Concentration Limit."""
    active_trades = ledger_summary.get("active_trades_by_date", {})
    count = active_trades.get(date_str, 0)
    if count >= 3:
        return RiskDecision(False, f"Market concentration limit exceeded (>=3 active trades for {date_str}).")
    return RiskDecision(True)

def evaluate_risk_gates(
    forecast_data: Dict[str, Any],
    latest_obs_time_iso: Optional[str],
    model_prob: float,
    executable_price: float,
    yes_ask: Optional[float],
    yes_bid: Optional[float],
    edge: float,
    raw_edge: float,
    ledger_summary: Dict[str, Any],
    target_date_str: str
) -> RiskDecision:
    """
    Evaluates all 10 risk gates in sequence.
    Returns the first failure, or a passing RiskDecision.
    """
    
    # Gate 10
    res = check_kill_switch()
    if not res.passed: return res
    
    # Gate 1
    res = check_weather_data_availability(forecast_data)
    if not res.passed: return res
    
    # Gate 2
    res = check_weather_freshness(latest_obs_time_iso)
    if not res.passed: return res
    
    # Gate 3
    res = check_forecast_confidence(forecast_data)
    if not res.passed: return res
    
    # Gate 4
    res = check_near_boundary_settlement(model_prob, raw_edge)
    if not res.passed: return res
    
    # Gate 5
    res = check_liquidity_and_spread(yes_ask, yes_bid)
    if not res.passed: return res
    
    # Gate 6
    res = check_fee_adjusted_edge(edge)
    if not res.passed: return res
    
    # Gate 7
    res = check_daily_loss_limit(ledger_summary)
    if not res.passed: return res
    
    # Gate 8
    res = check_weekly_drawdown_limit(ledger_summary)
    if not res.passed: return res
    
    # Gate 9
    res = check_market_concentration(ledger_summary, target_date_str)
    if not res.passed: return res
    
    return RiskDecision(True, "All risk gates passed.")

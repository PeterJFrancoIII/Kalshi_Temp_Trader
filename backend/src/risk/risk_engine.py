import os
import re
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

def check_settlement_boundary_risk(
    model_prob: float, 
    raw_edge: float, 
    best_high_f: Optional[float], 
    bin_label: str
) -> RiskDecision:
    """
    Gate 4: Settlement and Boundary Risk.
    
    Mitigates:
    1. 0.5°F–1.0°F rounding/CLI boundary risk.
    2. ~3°F forecast-risk buffer when uncertainty is material (model_prob near 0.5).
    """
    # 1. Material Uncertainty Buffer (3°F)
    # If the probability is near 50%, we are at maximum uncertainty. 
    # In this state, we require the predicted high to be at least 3.0°F away from 
    # the nearest boundary if edge is not extremely high.
    if 0.40 <= model_prob <= 0.60:
        if best_high_f is not None:
            boundaries = [float(n) for n in re.findall(r"(\d+\.?\d*)", bin_label)]
            for b in boundaries:
                if abs(best_high_f - b) < 3.0 and raw_edge < 0.20:
                    return RiskDecision(
                        False, 
                        f"Blocked: Material uncertainty (prob {model_prob:.2f}) requires "
                        f"3°F boundary buffer. Forecast {best_high_f}°F is too close to {b}°F."
                    )
        elif raw_edge < 0.15:
            return RiskDecision(False, "Blocked: Material uncertainty and low edge (<0.15).")

    # 2. Hard Rounding/CLI Buffer (1.0°F)
    # Even if probability is high, if we are within 1°F of a boundary, 
    # a small CLI rounding error or sensor calibration shift could flip the outcome.
    if best_high_f is not None:
        boundaries = [float(n) for n in re.findall(r"(\d+\.?\d*)", bin_label)]
        for b in boundaries:
            if abs(best_high_f - b) <= 1.0 and raw_edge < 0.15:
                return RiskDecision(
                    False, 
                    f"Blocked: Critical boundary risk. Forecast {best_high_f}°F is within "
                    f"1.0°F of boundary {b}°F. Requires >0.15 edge."
                )

    # 3. Legacy small-edge check
    if raw_edge < 0.02:
        return RiskDecision(False, f"Blocked: Raw edge ({raw_edge:.4f}) too small for boundary safety.")

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
    if "daily_pnl" not in ledger_summary:
        return RiskDecision(False, "Gate 7 Fail-Closed: Missing daily PnL data.")
    daily_pnl = ledger_summary.get("daily_pnl", 0.0)
    if daily_pnl < -50.0:  # Simulate a $50 paper loss limit
        return RiskDecision(False, f"Daily loss limit exceeded: ${daily_pnl:.2f}")
    return RiskDecision(True)

def check_weekly_drawdown_limit(ledger_summary: Dict[str, float]) -> RiskDecision:
    """Gate 8: Weekly Drawdown Limit."""
    if "weekly_pnl" not in ledger_summary:
        return RiskDecision(False, "Gate 8 Fail-Closed: Missing weekly PnL data.")
    weekly_pnl = ledger_summary.get("weekly_pnl", 0.0)
    if weekly_pnl < -150.0: # Simulate a $150 paper drawdown limit
        return RiskDecision(False, f"Weekly drawdown limit exceeded: ${weekly_pnl:.2f}")
    return RiskDecision(True)

def check_market_concentration(ledger_summary: Dict[str, Any], date_str: str) -> RiskDecision:
    """Gate 9: Market Concentration Limit."""
    active_trades = ledger_summary.get("active_trades_by_date")
    if active_trades is None:
        return RiskDecision(False, "Gate 9 Fail-Closed: Missing active trades data.")
    count = active_trades.get(date_str, 0)
    if count >= 3:
        return RiskDecision(False, f"Market concentration limit exceeded (>=3 active trades for {date_str}).")
    return RiskDecision(True)

def check_forecast_integrity(
    forecast_data: Dict[str, Any], 
    contract_bins: Optional[List[Any]] = None
) -> RiskDecision:
    """Gate 11: Forecast Integrity (Sum and Bins)."""
    probs = forecast_data.get("probability_bins", {})
    if not probs:
        return RiskDecision(False, "Missing probability bins.")
    
    total = sum(probs.values())
    if not (0.99 <= total <= 1.01):
        return RiskDecision(False, f"Forecast integrity failure: probabilities sum to {total:.4f} (expected ~1.0).")
    
    # If contract_bins are provided, ensure the probability_bins keys match the labels
    if contract_bins:
        contract_labels = set()
        for cb in contract_bins:
            if isinstance(cb, dict):
                label = cb.get("label") or cb.get("contract_bin", {}).get("label")
            else:
                label = getattr(cb, "label", None)
            
            if label:
                contract_labels.add(str(label))
                
        # Check that we have probabilities for all active contracts
        missing = [lbl for lbl in contract_labels if lbl not in probs]
        if missing:
            return RiskDecision(False, f"Missing probabilities for discovered contracts: {', '.join(missing)}")
        
        # Check that we don't have extra probabilities not in contracts (warn only)
        extra = [lbl for lbl in probs if lbl not in contract_labels]
        if extra:
            logger.warning(f"Extra probabilities found not mapping to active contracts: {', '.join(extra)}")
            
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
    target_date_str: str,
    best_high_f: Optional[float] = None,
    bin_label: str = "",
    contract_bins: Optional[List[Any]] = None
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
    res = check_settlement_boundary_risk(model_prob, raw_edge, best_high_f, bin_label)
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

    # Gate 11
    res = check_forecast_integrity(forecast_data, contract_bins)
    if not res.passed: return res
    
    return RiskDecision(True, "All risk gates passed.")

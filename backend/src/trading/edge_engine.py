import math
from datetime import datetime, timezone
from typing import Optional, Tuple

def calculate_fee_adjusted_breakeven(price: float) -> float:
    """
    Calculates the fee-adjusted breakeven probability for a Kalshi contract.
    Based on Kalshi's standard fee formula: fee = 0.07 * price * (1 - price)
    Returns the breakeven probability (cost to acquire).
    """
    if not (0.0 <= price <= 1.0):
        raise ValueError("Price must be between 0.0 and 1.0")
    fee = 0.07 * price * (1.0 - price)
    return round(price + fee, 4)

def calculate_slippage_adjusted_breakeven(price: float, slippage: float = 0.0) -> float:
    """
    Calculates the slippage-adjusted breakeven probability.
    In paper trading, slippage acts as an additional penalty on the execution price.
    """
    return round(price + slippage, 4)

def calculate_expected_value(model_prob: float, cost: float) -> float:
    """
    Computes the expected value of a trade.
    EV = (Probability of Win * Payout) - Cost
    Payout is 1.0 for binary contracts.
    """
    return round((model_prob * 1.0) - cost, 4)

def calculate_speed_to_roi(ev: float, close_time_iso: Optional[str]) -> Tuple[float, Optional[float]]:
    """
    Calculates ROI speed score: Expected Value per unit of time (e.g. per 100 minutes) remaining.
    Returns (score, minutes_to_close).
    """
    if not close_time_iso:
        return 0.0, None
        
    try:
        # Standardize 'Z' to UTC offset
        close_dt = datetime.fromisoformat(close_time_iso.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        diff = close_dt - now_dt
        minutes = max(diff.total_seconds() / 60.0, 1.0) # Floor at 1 minute to avoid div by zero
        
        # Score = EV per 100 minutes
        score = (ev / minutes) * 1000.0 if ev > 0 else 0.0
        return round(score, 2), round(minutes, 1)
    except Exception:
        return 0.0, None

def calculate_edge(model_prob: float, executable_price: float, slippage: float = 0.0) -> Tuple[float, float, float]:
    """
    Comprehensive edge calculation combining fees and slippage.
    Returns (edge, raw_edge, final_breakeven).
    """
    fee_adjusted_breakeven = calculate_fee_adjusted_breakeven(executable_price)
    final_breakeven = calculate_slippage_adjusted_breakeven(fee_adjusted_breakeven, slippage)
    
    raw_edge = model_prob - executable_price
    edge = model_prob - final_breakeven
    
    return round(edge, 4), round(raw_edge, 4), final_breakeven

from typing import Tuple

def check_data_staleness(prediction_ts: int, market_ts: int, current_ts: int, max_age_seconds: int = 300) -> Tuple[bool, str]:
    """
    Checks if the data is too old.
    Returns (is_valid, reason).
    """
    if (current_ts - prediction_ts) > max_age_seconds:
        return False, f"Prediction data is stale. Age: {current_ts - prediction_ts}s > {max_age_seconds}s"
    if (current_ts - market_ts) > max_age_seconds:
        return False, f"Market data is stale. Age: {current_ts - market_ts}s > {max_age_seconds}s"
    return True, ""

def check_spread(yes_ask: int, yes_bid: int, max_spread_cents: int = 10) -> Tuple[bool, str]:
    """
    Checks if the market spread is acceptable.
    """
    spread = yes_ask - yes_bid
    if spread > max_spread_cents:
        return False, f"Spread too wide: {spread}c > {max_spread_cents}c"
    if spread < 0:
        return False, f"Invalid spread: {spread}c (ask < bid)"
    return True, ""

def check_liquidity(available_size: int, min_size: int = 10) -> Tuple[bool, str]:
    """
    Checks if there is enough liquidity to trade.
    """
    if available_size < min_size:
        return False, f"Liquidity too low: {available_size} < {min_size}"
    return True, ""

def check_confidence(confidence: str) -> Tuple[bool, str]:
    """
    Checks if the model confidence is acceptable.
    """
    if confidence.lower() == "low":
        return False, "Confidence is strictly low"
    return True, ""

def check_edge_threshold(edge_after_fees: float, min_edge: float = 0.05) -> Tuple[bool, str]:
    """
    Checks if the edge after fees meets the minimum threshold for a TRADE_CANDIDATE.
    Returns (is_trade_candidate, reason). 
    Note: Failing this gate does not mean REJECT, it might just mean WATCH if edge is positive.
    """
    if edge_after_fees < min_edge:
        return False, f"Edge after fees ({edge_after_fees:.4f}) below threshold ({min_edge:.4f})"
    return True, ""

def check_market_mapping(bin_name: str, valid_bins: set) -> Tuple[bool, str]:
    """
    Checks if the bin name is valid and expected.
    """
    if bin_name not in valid_bins:
        return False, f"Uncertain market mapping for bin: {bin_name}"
    return True, ""

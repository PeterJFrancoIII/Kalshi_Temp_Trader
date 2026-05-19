"""Canonical edge / EV math for paper-trading evaluation.

This module is the single source of truth for:
    - Kalshi fee formula (``0.07 * p * (1 - p)``)
    - Implied probability from a yes_ask quote
    - Raw edge, fee-adjusted edge, slippage-adjusted breakeven
    - Confidence-scaled edge
    - Speed-to-ROI scoring
    - The richer ``compute_edge(...) -> dict`` used by the paper signal
      generator

Older code in :mod:`recommendation.ev` re-exports the helpers below for
backward compatibility; new callers should import from this module
directly.

NO REAL TRADING EXECUTION.
"""

import math
from datetime import datetime, timezone
from typing import Optional, Tuple


# --- Atomic helpers -------------------------------------------------------

def calculate_implied_probability(yes_ask_cents: float) -> float:
    """Convert a Kalshi yes_ask quote (in cents, 0-100) to implied probability.

    Inputs are typically integer cents (e.g. ``45`` → ``0.45``) but any
    numeric value in the ``[0, 100]`` range is accepted.
    """
    return round(yes_ask_cents / 100.0, 4)


def calculate_kalshi_fee(price: float) -> float:
    """Kalshi taker fee in probability terms.

    Single canonical definition of the fee formula. ``0.07 * p * (1 - p)``.
    """
    return round(0.07 * price * (1.0 - price), 4)


def calculate_raw_edge(model_prob: float, market_prob: float) -> float:
    """Pre-fee edge: model probability minus market-implied probability."""
    return round(model_prob - market_prob, 4)


def calculate_edge_after_fees(raw_edge: float, fee: float) -> float:
    """Subtract fees from a raw edge."""
    return round(raw_edge - fee, 4)


def calculate_confidence_adjusted_edge(edge: float, confidence: str) -> float:
    """Scale an edge by model confidence tier.

    Returns ``edge`` for ``high`` confidence, half for ``medium``, a tenth
    for ``low``, and ``0.0`` for anything else (including unknown values).
    """
    confidence = (confidence or "").lower()
    if confidence == "high":
        return round(edge, 4)
    if confidence == "medium":
        return round(edge * 0.5, 4)
    if confidence == "low":
        return round(edge * 0.1, 4)
    return 0.0


# --- Composite helpers ----------------------------------------------------

def calculate_fee_adjusted_breakeven(price: float) -> float:
    """
    Calculates the fee-adjusted breakeven probability for a Kalshi contract.
    Based on Kalshi's standard fee formula: fee = 0.07 * price * (1 - price)
    Returns the breakeven probability (cost to acquire).
    """
    if not (0.0 <= price <= 1.0):
        raise ValueError("Price must be between 0.0 and 1.0")
    fee = calculate_kalshi_fee(price)
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

def compute_edge(
    model_probability: Optional[float],
    yes_ask: Optional[float] = None,
    yes_bid: Optional[float] = None,
    last_price: Optional[float] = None,
    fee_rate: float = 0.07,
    slippage_buffer: float = 0.01
) -> dict:
    """
    Computes fee- and slippage-aware trading edge with rich validations.
    """
    warnings = []
    tradable = True

    # Validate model_probability
    if model_probability is None:
        tradable = False
        warnings.append("model_probability is None")
        p_model = 0.0
    elif not isinstance(model_probability, (int, float)) or not (0.0 <= model_probability <= 1.0):
        tradable = False
        warnings.append(f"Invalid model_probability: {model_probability}")
        p_model = max(0.0, min(1.0, float(model_probability))) if isinstance(model_probability, (int, float)) else 0.0
    else:
        p_model = float(model_probability)

    # Determine executable price
    executable_price = None
    market_prob = None
    if yes_ask is not None:
        executable_price = yes_ask
        market_prob = yes_ask
    elif last_price is not None:
        executable_price = last_price
        market_prob = last_price
        tradable = False
        warnings.append("yes_ask missing; using last_price for diagnostic only")
    else:
        tradable = False
        warnings.append("Both yes_ask and last_price are missing")

    # Validate executable_price
    if executable_price is not None:
        if not isinstance(executable_price, (int, float)) or not (0.0 <= executable_price <= 1.0):
            tradable = False
            warnings.append(f"Invalid executable_price: {executable_price}")
            p_exec = max(0.0, min(1.0, float(executable_price))) if isinstance(executable_price, (int, float)) else 0.0
        else:
            p_exec = float(executable_price)
    else:
        p_exec = 0.0

    # Calculate fee buffer
    fee_buffer = fee_rate * p_exec * (1.0 - p_exec)

    # Breakeven probability
    breakeven_probability = p_exec + fee_buffer + slippage_buffer

    # Clamp breakeven if out of bounds (0, 1) and warn
    if breakeven_probability > 1.0:
        warnings.append(f"Breakeven probability clamped: {breakeven_probability} -> 1.0")
        breakeven_probability = 1.0
    elif breakeven_probability < 0.0:
        warnings.append(f"Breakeven probability clamped: {breakeven_probability} -> 0.0")
        breakeven_probability = 0.0

    raw_edge = p_model - p_exec
    executable_edge = p_model - breakeven_probability

    return {
        "executable_price": round(executable_price, 4) if executable_price is not None else None,
        "market_probability": round(market_prob, 4) if market_prob is not None else None,
        "breakeven_probability": round(breakeven_probability, 4),
        "raw_edge": round(raw_edge, 4),
        "executable_edge": round(executable_edge, 4),
        "fee_buffer": round(fee_buffer, 4),
        "slippage_buffer": round(slippage_buffer, 4),
        "tradable": tradable,
        "warnings": warnings,
        "yes_ask": yes_ask,
        "yes_bid": yes_bid
    }


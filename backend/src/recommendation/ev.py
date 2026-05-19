"""Edge / EV helpers for the recommendation pipeline.

This module is a thin compatibility layer over the canonical math in
:mod:`trading.edge_engine`. It exists so older imports keep working and so
the ``recommendation.recommender`` module can continue using the names it
has always used.

New callers should import from :mod:`trading.edge_engine` directly.

``calculate_edge`` is retained as a deprecated alias for
:func:`trading.edge_engine.calculate_raw_edge`. It returns
``model_prob - implied_prob`` (a scalar) — distinct from
:func:`trading.edge_engine.calculate_edge` which is the fee+slippage-aware
tuple-returning helper. The collision between those two names is exactly
what motivated this consolidation.

NO REAL TRADING EXECUTION.
"""

from trading.edge_engine import (
    calculate_confidence_adjusted_edge,
    calculate_edge_after_fees,
    calculate_implied_probability,
    calculate_kalshi_fee,
    calculate_raw_edge,
)


def calculate_edge(model_prob: float, implied_prob: float) -> float:
    """Deprecated alias for :func:`trading.edge_engine.calculate_raw_edge`.

    Retained because ``recommendation.recommender`` (and its tests) call
    ``ev.calculate_edge(model_prob, implied_prob)``. The signature differs
    from :func:`trading.edge_engine.calculate_edge`, hence the
    consolidation behind one canonical name in ``trading.edge_engine``.
    """
    return calculate_raw_edge(model_prob, implied_prob)


__all__ = [
    "calculate_confidence_adjusted_edge",
    "calculate_edge",
    "calculate_edge_after_fees",
    "calculate_implied_probability",
    "calculate_kalshi_fee",
]

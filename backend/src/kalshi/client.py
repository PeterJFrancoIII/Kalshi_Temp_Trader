"""Deprecated re-export shim.

The canonical read-only Kalshi client lives in
``market_data.kalshi_public_client``. This shim exists only so legacy callers
that still do ``from kalshi.client import KalshiPublicClient`` keep working
during the Phase 2 consolidation. Migrate to::

    from market_data.kalshi_public_client import KalshiPublicClient

This file is scheduled for removal in Phase 3.

No real-money trading code is or will be added here.
"""

import warnings

from market_data.kalshi_public_client import KalshiPublicClient

warnings.warn(
    "kalshi.client is deprecated; import KalshiPublicClient from "
    "market_data.kalshi_public_client instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["KalshiPublicClient"]

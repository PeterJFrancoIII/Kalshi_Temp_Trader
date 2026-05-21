"""
KMIA Kalshi daily high-temperature market open-window classification.

Trading window for market date D (settlement day):
- Opens: 10:00 America/New_York on calendar day D-1
- Closes: 00:59 America/New_York on calendar day D+1 (12:59 AM on D+1)

After 01:00 ET on D+1 the market is CLOSED for paper/active tables.

NO REAL TRADING EXECUTION — classification helpers only.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from zoneinfo import ZoneInfo

from shared.timestamp_utils import extract_embedded_timestamp

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

EASTERN_TZ = ZoneInfo("America/New_York")

MARKET_STATUS_OPEN = "OPEN"
MARKET_STATUS_PRE_OPEN = "PRE_OPEN"
MARKET_STATUS_CLOSED = "CLOSED"
MARKET_STATUS_STALE_MARKET_DATA = "STALE_MARKET_DATA"
MARKET_STATUS_MISSING_FORECAST = "MISSING_FORECAST"
MARKET_STATUS_MISSING_CONTRACTS = "MISSING_CONTRACTS"

DEFAULT_SNAPSHOT_MAX_AGE_MINUTES = 45


def _parse_market_date(market_date: str) -> date:
    return datetime.strptime(market_date, "%Y-%m-%d").date()


def market_open_window_et(market_date: str) -> Dict[str, str]:
    """
    Return open/close instants for Kalshi KMIA high-temp market date D in Eastern time.

    Example D=2026-05-21:
      open_start_et = 2026-05-20T10:00:00-04:00
      open_end_et   = 2026-05-22T00:59:00-04:00
    """
    d = _parse_market_date(market_date)
    open_start = datetime(
        d.year, d.month, d.day, 10, 0, 0, tzinfo=EASTERN_TZ
    ) - timedelta(days=1)
    close_day = d + timedelta(days=1)
    open_end = datetime(
        close_day.year, close_day.month, close_day.day, 0, 59, 0, tzinfo=EASTERN_TZ
    )
    return {
        "open_start_et": open_start.isoformat(),
        "open_end_et": open_end.isoformat(),
    }


def classify_market_window(
    market_date: str,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Classify whether market date D is PRE_OPEN, OPEN, or CLOSED at ``now_utc``.

    Uses America/New_York (DST-aware), never naive UTC calendar-day heuristics.
    """
    if now_utc is None:
        now_utc = datetime.now(EASTERN_TZ).astimezone(EASTERN_TZ)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=EASTERN_TZ)
    now_et = now_utc.astimezone(EASTERN_TZ)

    window = market_open_window_et(market_date)
    open_start = datetime.fromisoformat(window["open_start_et"])
    open_end = datetime.fromisoformat(window["open_end_et"])

    if now_et < open_start:
        window_status = MARKET_STATUS_PRE_OPEN
    elif now_et <= open_end:
        window_status = MARKET_STATUS_OPEN
    else:
        window_status = MARKET_STATUS_CLOSED

    return {
        "market_date": market_date,
        "market_status": window_status,
        "open_start_et": window["open_start_et"],
        "open_end_et": window["open_end_et"],
        "now_et": now_et.isoformat(),
    }


def assess_kalshi_snapshot_freshness(
    snapshot_path: Path,
    now_utc: Optional[datetime] = None,
    max_age_minutes: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Assess market snapshot age using embedded JSON timestamp only (never mtime).
    """
    if now_utc is None:
        now_utc = datetime.now(EASTERN_TZ).astimezone(EASTERN_TZ)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=EASTERN_TZ)

    if max_age_minutes is None:
        env_val = os.environ.get("KALSHI_SNAPSHOT_MAX_AGE_MINUTES")
        max_age_minutes = float(env_val) if env_val else DEFAULT_SNAPSHOT_MAX_AGE_MINUTES

    embedded_ts = extract_embedded_timestamp(snapshot_path)
    warnings = []

    if embedded_ts is None:
        return {
            "fetched_at_utc": None,
            "snapshot_age_minutes": None,
            "max_age_minutes": max_age_minutes,
            "is_stale": True,
            "warnings": [
                f"No embedded timestamp in {snapshot_path.name}; "
                "market snapshot treated as STALE_MARKET_DATA."
            ],
        }

    age_minutes = (now_utc - embedded_ts.astimezone(EASTERN_TZ)).total_seconds() / 60.0
    is_stale = age_minutes > max_age_minutes
    if is_stale:
        warnings.append(
            f"Kalshi market snapshot is {age_minutes:.1f} minutes old "
            f"(max {max_age_minutes:.0f}); flagged STALE_MARKET_DATA."
        )

    return {
        "fetched_at_utc": embedded_ts.isoformat(),
        "snapshot_age_minutes": round(age_minutes, 2),
        "max_age_minutes": max_age_minutes,
        "is_stale": is_stale,
        "warnings": warnings,
    }


def resolve_event_market_status(
    window_status: str,
    snapshot_stale: bool,
    has_contracts: bool,
    has_forecast_distribution: bool,
) -> str:
    """
    Combine window, snapshot freshness, contracts, and forecast into one status.
    """
    if window_status == MARKET_STATUS_CLOSED:
        return MARKET_STATUS_CLOSED
    if window_status == MARKET_STATUS_PRE_OPEN:
        return MARKET_STATUS_PRE_OPEN
    if snapshot_stale:
        return MARKET_STATUS_STALE_MARKET_DATA
    if not has_contracts:
        return MARKET_STATUS_MISSING_CONTRACTS
    if not has_forecast_distribution:
        return MARKET_STATUS_MISSING_FORECAST
    return MARKET_STATUS_OPEN


def is_tradable_market_status(market_status: str) -> bool:
    """True when contracts on this date may receive paper allocation."""
    return market_status == MARKET_STATUS_OPEN


def is_visible_active_market_status(market_status: str) -> bool:
    """True when date should appear in active bins / open-contract tables."""
    return market_status in (
        MARKET_STATUS_OPEN,
        MARKET_STATUS_PRE_OPEN,
        MARKET_STATUS_STALE_MARKET_DATA,
        MARKET_STATUS_MISSING_FORECAST,
        MARKET_STATUS_MISSING_CONTRACTS,
    )

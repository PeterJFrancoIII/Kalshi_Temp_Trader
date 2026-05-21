"""Market-date visibility helpers for Command Center / Active Forecasts UI.

Read-only presentation logic — does not change market window or signal math.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Mirrors shared.kalshi_market_window status strings (UI layer only).
MARKET_STATUS_OPEN = "OPEN"
MARKET_STATUS_PRE_OPEN = "PRE_OPEN"
MARKET_STATUS_CLOSED = "CLOSED"
MARKET_STATUS_STALE_MARKET_DATA = "STALE_MARKET_DATA"
MARKET_STATUS_MISSING_FORECAST = "MISSING_FORECAST"
MARKET_STATUS_MISSING_CONTRACTS = "MISSING_CONTRACTS"

_STATUS_BADGE = {
    MARKET_STATUS_OPEN: "🟢 OPEN",
    MARKET_STATUS_STALE_MARKET_DATA: "🟡 STALE_MARKET_DATA",
    MARKET_STATUS_MISSING_FORECAST: "🟠 MISSING_FORECAST",
    MARKET_STATUS_MISSING_CONTRACTS: "⚪ MISSING_CONTRACTS",
    MARKET_STATUS_PRE_OPEN: "🔵 PRE_OPEN",
    MARKET_STATUS_CLOSED: "⚫ CLOSED",
}


def status_badge(market_status: str) -> str:
    return _STATUS_BADGE.get(market_status or "", f"❓ {market_status or 'UNKNOWN'}")


def is_tradable_status(market_status: str) -> bool:
    return market_status == MARKET_STATUS_OPEN


def partition_market_dates(
    events_by_date: Dict[str, Dict[str, Any]],
    open_market_dates: Optional[List[str]] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Split dates into (primary_active, secondary_pre_open, closed_historical).

    Primary active: open_market_dates first, then other visible non-closed dates.
    """
    open_order = list(open_market_dates or [])
    open_set = set(open_order)

    primary: List[str] = []
    pre_open: List[str] = []
    closed: List[str] = []

    for date in sorted(events_by_date.keys()):
        status = events_by_date[date].get("market_status", "")
        if status == MARKET_STATUS_CLOSED:
            closed.append(date)
        elif status == MARKET_STATUS_PRE_OPEN:
            pre_open.append(date)
        else:
            primary.append(date)

    def _sort_primary(d: str) -> Tuple[int, int, str]:
        if d in open_set:
            return (0, open_order.index(d), d)
        return (1, 0, d)

    primary.sort(key=_sort_primary)
    return primary, pre_open, closed


def build_kalshi_bins_rows(date_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build Kalshi Bins table rows. Never fabricates model probabilities.
    """
    probs: Dict[str, Any] = date_data.get("dynamic_contract_probabilities") or {}
    contracts: List[Dict[str, Any]] = date_data.get("contracts") or []

    rows: List[Dict[str, Any]] = []
    seen_bins: set = set()

    for contract in contracts:
        bin_label = (
            contract.get("forecast_bin_label")
            or contract.get("contract_range")
            or contract.get("ticker")
            or "N/A"
        )
        if bin_label in seen_bins:
            continue
        seen_bins.add(bin_label)
        prob = probs.get(bin_label)
        if prob is None:
            cr = contract.get("contract_range")
            if cr and cr in probs:
                prob = probs[cr]
        rows.append(
            {
                "Kalshi Bin (Range)": bin_label,
                "Model Prob": (float(prob) * 100) if prob is not None else None,
            }
        )

    if rows:
        return rows

    for bin_name, prob in probs.items():
        rows.append(
            {
                "Kalshi Bin (Range)": bin_name,
                "Model Prob": (float(prob) * 100) if prob is not None else None,
            }
        )
    return rows


def status_banner_message(date: str, date_data: Dict[str, Any], market_status: str) -> Optional[str]:
    """Return a user-facing banner for this market status, or None."""
    if market_status == MARKET_STATUS_STALE_MARKET_DATA:
        age = date_data.get("snapshot_age_minutes")
        max_age = date_data.get("max_age_minutes")
        age_part = f" Snapshot age: {age:.0f} min" if age is not None else ""
        max_part = f" (max {max_age:.0f} min)" if max_age is not None else ""
        return (
            "Market snapshot stale — refresh Kalshi snapshot before paper evaluation."
            f"{age_part}{max_part} Not tradable until refreshed."
        )
    if market_status == MARKET_STATUS_MISSING_FORECAST:
        return f"Forecast distribution missing for {date}. Contracts shown without model probabilities."
    if market_status == MARKET_STATUS_MISSING_CONTRACTS:
        return f"No active contracts discovered for {date}."
    if market_status == MARKET_STATUS_CLOSED:
        return "Closed — not used for active allocation or paper money distribution."
    if market_status == MARKET_STATUS_PRE_OPEN:
        return f"Pre-open for {date} — market window not yet active for paper evaluation."
    if market_status == MARKET_STATUS_OPEN:
        return None
    return None


def format_snapshot_age_line(date_data: Dict[str, Any], market_snapshot: Optional[Dict[str, Any]]) -> Optional[str]:
    """One-line snapshot age summary for a date block."""
    parts: List[str] = []
    fetched = date_data.get("snapshot_fetched_at_utc")
    if fetched:
        parts.append(f"fetched {fetched}")
    age = date_data.get("snapshot_age_minutes")
    if age is not None:
        parts.append(f"age {age:.0f} min")
    max_age = date_data.get("max_age_minutes")
    if max_age is None and market_snapshot:
        max_age = market_snapshot.get("max_age_minutes")
    if max_age is not None:
        parts.append(f"max {max_age:.0f} min")
    if not parts and market_snapshot:
        snap_age = market_snapshot.get("snapshot_age_minutes")
        if snap_age is not None:
            parts.append(f"snapshot age {snap_age:.0f} min")
    return " · ".join(parts) if parts else None

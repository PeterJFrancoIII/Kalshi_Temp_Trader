"""
Shared timestamp utilities for point-in-time artifact selection.

These helpers are used by both the backtest coordinator (for replay safety)
and the live paper-signal generator (for snapshot staleness checks).

Rule: embedded JSON timestamps are canonical. Filesystem mtime is NEVER used
for safety-critical ordering decisions.
"""

import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

logger = logging.getLogger(__name__)

EMBEDDED_TIMESTAMP_FIELDS: List[str] = [
    "generated_at_utc",
    "fetched_at_utc",
    "timestamp",
    "created_at",
    "snapshot_time",
    "as_of",
]


def parse_ticker_date(ticker: str) -> Optional[str]:
    """Parses date from ticker like KXHIGHMIA-26MAY06-B84.5
    Returns YYYY-MM-DD string or None.
    """
    if not ticker:
        return None
    match = re.search(r"([0-9]{2})([A-Z]{3})([0-9]{2})", ticker)
    if not match:
        return None
    year_short, mon_str, day_str = match.groups()
    months = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
        "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
    }
    month = months.get(mon_str.upper())
    if not month:
        return None
    return f"20{year_short}-{month}-{day_str}"


def extract_embedded_timestamp(filepath: Path) -> Optional[datetime]:
    """
    Opens a JSON file and extracts the first valid ISO timestamp from the
    known set of embedded timestamp fields.

    Returns a timezone-aware UTC datetime, or None if:
    - the file cannot be opened or parsed as JSON
    - no known timestamp field is found
    - the field value cannot be parsed as an ISO timestamp

    IMPORTANT: This function must never fall back to filesystem mtime.
    Callers must treat a None return as "timestamp unknown — exclude this
    file from point-in-time selection."
    """
    if filepath.suffix.lower() != '.json':
        return None
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Could not read JSON from {filepath}: {e}")
        return None

    for field in EMBEDDED_TIMESTAMP_FIELDS:
        raw = data.get(field)
        if raw and isinstance(raw, str):
            try:
                ts = raw.replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt
            except ValueError:
                logger.warning(
                    f"Field '{field}' in {filepath.name} has unparseable value: {raw!r}"
                )
                continue

    logger.warning(
        f"No valid embedded timestamp found in {filepath.name} "
        f"(tried fields: {EMBEDDED_TIMESTAMP_FIELDS}). "
        f"File excluded from point-in-time selection."
    )
    return None


def select_snapshot_as_of(
    directory: Path,
    glob_pattern: str,
    as_of_time: datetime,
    warn_on_missing_ts: bool = True,
) -> Optional[Path]:
    """
    Selects the most-recent snapshot file whose EMBEDDED timestamp is
    <= as_of_time.

    Rules:
    - Only examines files matching glob_pattern in directory.
    - Reads the embedded timestamp from JSON content (never filesystem mtime).
    - Files with missing or unparseable embedded timestamps are EXCLUDED and
      a warning is logged.
    - Returns the file with the latest eligible embedded timestamp, or None.
    """
    if not directory.exists():
        logger.warning(f"Snapshot directory does not exist: {directory}")
        return None

    candidates: List[Tuple[datetime, Path]] = []

    for filepath in directory.glob(glob_pattern):
        if filepath.suffix.lower() != '.json':
            continue
        embedded_ts = extract_embedded_timestamp(filepath)
        if embedded_ts is None:
            if warn_on_missing_ts:
                logger.warning(
                    f"Skipping {filepath.name}: no valid embedded timestamp. "
                    f"Set warn_on_missing_ts=False to suppress."
                )
            continue
        if embedded_ts <= as_of_time:
            candidates.append((embedded_ts, filepath))
        else:
            logger.debug(
                f"Excluding {filepath.name}: embedded timestamp {embedded_ts} "
                f"is after as_of_time {as_of_time}."
            )

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    chosen_ts, chosen_path = candidates[0]
    logger.info(
        f"Selected snapshot {chosen_path.name} "
        f"(embedded_ts={chosen_ts.isoformat()}, as_of={as_of_time.isoformat()})"
    )
    return chosen_path


def extract_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """
    Parses a datetime object from a filename containing standard date/time pattern.
    Supports formats like:
      - kmia_forecast_YYYY-MM-DD_rules_vX_HHMMSS.md / .json
      - kmia_comparison_YYYY-MM-DD_HHMMSS.md
      - kmia_daily_status_YYYY-MM-DD.json / .md
      - kmia_daily_workflow_YYYY-MM-DD.log
      - run_YYYYMMDD_HHMMSS (backtest run directories)
    """
    # 1. Match YYYY-MM-DD and HHMMSS (e.g. 2026-05-12 and 205608)
    match = re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d{6})", filename)
    if match:
        date_str, time_str = match.groups()
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # 2. Match YYYYMMDD_HHMMSS (e.g., 20260515_003705)
    match_run = re.search(r"(\d{8})_(\d{6})", filename)
    if match_run:
        date_str, time_str = match_run.groups()
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # 3. Match YYYY-MM-DD (e.g. 2026-05-12)
    match_date = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if match_date:
        date_str = match_date.group(1)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return None


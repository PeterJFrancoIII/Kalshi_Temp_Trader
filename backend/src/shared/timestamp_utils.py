"""
Shared timestamp utilities for point-in-time artifact selection.

These helpers are used by both the backtest coordinator (for replay safety)
and the live paper-signal generator (for snapshot staleness checks).

Rule: embedded JSON timestamps are canonical. Filesystem mtime is NEVER used
for safety-critical ordering decisions.
"""

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

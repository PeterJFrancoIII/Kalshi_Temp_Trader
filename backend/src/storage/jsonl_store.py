"""Simple JSONL storage handler with POSIX advisory file locking.

Multiple processes (cron jobs, scheduler ticks, ad-hoc scripts) may write
to the same JSONL file concurrently in the operations pipeline. Without
locking, an append-from-process-A interleaved with a read-modify-write
update-from-process-B can lose records.

This module wraps :mod:`fcntl` advisory locks around every write. Reads
take a shared lock so they don't block each other but do block during a
concurrent write. On non-POSIX platforms (or when ``fcntl`` import
fails), locking degrades to a no-op and a one-time warning is logged.

NO REAL TRADING EXECUTION.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List

logger = logging.getLogger(__name__)

try:
    import fcntl

    _FCNTL_AVAILABLE = True
except ImportError:  # pragma: no cover - Windows/non-POSIX path
    fcntl = None  # type: ignore[assignment]
    _FCNTL_AVAILABLE = False
    logger.warning(
        "fcntl is unavailable; JSONLStore is running without file locking. "
        "Concurrent writers may interleave records."
    )


@contextmanager
def _locked(file_handle, exclusive: bool) -> Iterator[None]:
    """Acquire an advisory lock on ``file_handle`` for the block body.

    Exclusive locks (LOCK_EX) are used for writes; shared locks (LOCK_SH)
    for reads. The lock is released automatically when the file is
    closed, but we release explicitly so callers can reuse the handle.
    """
    if not _FCNTL_AVAILABLE:
        yield
        return
    flag = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    fcntl.flock(file_handle.fileno(), flag)
    try:
        yield
    finally:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)


class JSONLStore:
    """JSONL file with advisory file locking around every read and write."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def append_record(self, record: Dict[str, Any]) -> None:
        """Append ``record`` as one JSON line. Holds an exclusive lock."""
        with open(self.file_path, "a", encoding="utf-8") as f:
            with _locked(f, exclusive=True):
                f.write(json.dumps(record) + "\n")
                f.flush()

    def load_records(self) -> List[Dict[str, Any]]:
        """Load all records. Holds a shared lock during the read."""
        if not os.path.exists(self.file_path):
            return []

        records: List[Dict[str, Any]] = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            with _locked(f, exclusive=False):
                for line in f:
                    if line.strip():
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return records

    def update_record(
        self,
        match_key: str,
        match_value: Any,
        updated_fields: Dict[str, Any],
    ) -> bool:
        """Update the first record where ``record[match_key] == match_value``.

        Rewrites the whole file under an exclusive lock to keep the
        read-modify-write atomic relative to other JSONLStore callers on
        the same path. Returns ``True`` if a record was modified.
        """
        if not os.path.exists(self.file_path):
            return False

        # Open r+ so the same handle serves both read and rewrite under
        # one continuous lock acquisition.
        with open(self.file_path, "r+", encoding="utf-8") as f:
            with _locked(f, exclusive=True):
                records: List[Dict[str, Any]] = []
                for line in f:
                    if line.strip():
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

                updated = False
                for i, record in enumerate(records):
                    if record.get(match_key) == match_value:
                        records[i].update(updated_fields)
                        updated = True
                        break

                if updated:
                    f.seek(0)
                    f.truncate()
                    for record in records:
                        f.write(json.dumps(record) + "\n")
                    f.flush()

                return updated

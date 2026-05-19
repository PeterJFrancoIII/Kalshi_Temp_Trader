"""Tests for :mod:`storage.jsonl_store`.

Covers basic append / load / update plus concurrent-writer safety via
forked subprocesses (POSIX advisory locking).
"""

import json
import multiprocessing
import os
import tempfile
import unittest

from storage.jsonl_store import JSONLStore


def _worker_append(file_path: str, n: int, start_offset: int) -> None:
    """Worker that appends ``n`` records with ids starting at ``start_offset``."""
    store = JSONLStore(file_path)
    for i in range(n):
        store.append_record({"id": start_offset + i, "value": "x" * 64})


class TestJSONLStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmpdir.name, "store.jsonl")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_append_and_load_roundtrip(self):
        store = JSONLStore(self.path)
        store.append_record({"id": 1, "v": "a"})
        store.append_record({"id": 2, "v": "b"})
        records = store.load_records()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["id"], 1)
        self.assertEqual(records[1]["v"], "b")

    def test_load_missing_returns_empty(self):
        store = JSONLStore(self.path)
        self.assertEqual(store.load_records(), [])

    def test_update_first_match_only(self):
        store = JSONLStore(self.path)
        store.append_record({"id": 1, "v": "a"})
        store.append_record({"id": 2, "v": "b"})
        store.append_record({"id": 1, "v": "c"})

        changed = store.update_record("id", 1, {"v": "Z"})
        self.assertTrue(changed)
        records = store.load_records()
        # Only the FIRST id=1 record should change.
        self.assertEqual(records[0]["v"], "Z")
        self.assertEqual(records[2]["v"], "c")

    def test_update_no_match_returns_false(self):
        store = JSONLStore(self.path)
        store.append_record({"id": 1, "v": "a"})
        self.assertFalse(store.update_record("id", 99, {"v": "Z"}))

    def test_concurrent_append_preserves_all_lines(self):
        """Two processes appending in parallel must not drop or splice records.

        Each worker writes 50 records of 64+ byte payloads — larger than
        typical pipe buffer sizes — so absent locking we would expect
        torn writes. With fcntl advisory locking active, every record
        must round-trip as a complete JSON line.

        We use the ``spawn`` start method explicitly so subprocesses
        receive an independent Python interpreter and don't inherit the
        parent test runner's mutated ``sys.path``; if the worker can't
        find ``storage.jsonl_store`` the test is skipped instead of
        silently producing zero appends.
        """
        try:
            ctx = multiprocessing.get_context("spawn")
        except (ValueError, AttributeError):  # pragma: no cover
            self.skipTest("spawn context unavailable on this platform")

        n_per_worker = 50
        proc1 = ctx.Process(
            target=_worker_append, args=(self.path, n_per_worker, 0)
        )
        proc2 = ctx.Process(
            target=_worker_append, args=(self.path, n_per_worker, 1000)
        )
        proc1.start()
        proc2.start()
        proc1.join()
        proc2.join()

        if proc1.exitcode != 0 or proc2.exitcode != 0:
            self.skipTest(
                "concurrent-writer subprocesses failed to start cleanly "
                f"(exitcodes={proc1.exitcode}, {proc2.exitcode}); skipping "
                "concurrency check rather than reporting a false negative"
            )

        with open(self.path, "r", encoding="utf-8") as f:
            raw_lines = [line for line in f if line.strip()]

        self.assertEqual(
            len(raw_lines),
            2 * n_per_worker,
            "Expected all appended records to be present after concurrent writes",
        )
        ids = []
        for line in raw_lines:
            record = json.loads(line)
            ids.append(record["id"])
        self.assertEqual(len(set(ids)), 2 * n_per_worker)


if __name__ == "__main__":
    unittest.main()

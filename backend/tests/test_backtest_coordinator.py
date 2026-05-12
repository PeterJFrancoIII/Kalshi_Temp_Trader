"""
Tests for Phase 9 P0 and P1 Lookahead-Safety Fixes.

P0 Covers:
1. Embedded timestamp extraction from JSON files.
2. Snapshot selection uses embedded timestamp (never filesystem mtime).
3. Snapshot with newer mtime but older embedded timestamp is handled correctly.
4. Snapshot with missing embedded timestamp is excluded with a warning.
5. Forecast snapshot after forecast_as_of_time is excluded.
6. Market snapshot after market_snapshot_as_of_time is excluded.
7. Settlement is blocked before settlement_as_of_time.
8. Settlement proceeds after settlement_as_of_time.
9. Existing coordinator tests still pass.
10. record_trade stores model_probability and forecast_bin.

P1 Covers:
11. SnapshotRegistry.resolve() returns correct artifact.
12. SnapshotRegistry.resolve() returns None for unknown artifact type.
13. SnapshotRegistry caches results (same key is not re-resolved).
14. SnapshotRegistry.lookup_log() records all lookup events.
15. BacktestCoordinator exposes _registry attribute.
16. signal_generator.py uses embedded timestamp (not mtime) for snapshot validation.
17. replay_manifest.json is written after run_backtest().
18. Replay manifest has correct schema and safety field.
"""

import json
import os
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path (handled by conftest / run_tests.py in the project)
# If running via pytest directly, set PYTHONPATH=backend/src.

from backtesting.coordinator import (
    BacktestCoordinator,
    SnapshotRegistry,
    extract_embedded_timestamp,
    select_snapshot_as_of,
)
from paper_trading.settlement import settle_paper_trades
from paper_trading.paper_ledger import PaperLedger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def _make_snapshot(directory: Path, filename: str, embedded_ts: str) -> Path:
    """Creates a minimal Kalshi snapshot JSON with the given embedded timestamp."""
    p = directory / filename
    _write_json(p, {
        "fetched_at_utc": embedded_ts,
        "mode": "READ-ONLY",
        "markets": [],
        "markets_found": 0,
        "warnings": [],
        "safety": {"no_real_trading": True},
    })
    return p


# ---------------------------------------------------------------------------
# Test 1 — extract_embedded_timestamp: happy path
# ---------------------------------------------------------------------------

def test_extract_embedded_timestamp_fetched_at_utc():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "snap.json"
        _write_json(p, {"fetched_at_utc": "2026-05-06T13:00:00+00:00"})
        ts = extract_embedded_timestamp(p)
        assert ts is not None
        assert ts == datetime(2026, 5, 6, 13, 0, 0, tzinfo=timezone.utc)


def test_extract_embedded_timestamp_generated_at_utc():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "snap.json"
        _write_json(p, {"generated_at_utc": "2026-05-06T09:00:00Z"})
        ts = extract_embedded_timestamp(p)
        assert ts is not None
        assert ts == datetime(2026, 5, 6, 9, 0, 0, tzinfo=timezone.utc)


def test_extract_embedded_timestamp_timestamp_field():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "snap.json"
        _write_json(p, {"timestamp": "2026-05-07T14:30:00+00:00"})
        ts = extract_embedded_timestamp(p)
        assert ts is not None
        assert ts == datetime(2026, 5, 7, 14, 30, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Test 2 — extract_embedded_timestamp: missing field returns None
# ---------------------------------------------------------------------------

def test_extract_embedded_timestamp_missing_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "snap.json"
        _write_json(p, {"mode": "READ-ONLY", "markets": []})
        ts = extract_embedded_timestamp(p)
        assert ts is None


def test_extract_embedded_timestamp_invalid_value_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "snap.json"
        _write_json(p, {"fetched_at_utc": "not-a-timestamp"})
        ts = extract_embedded_timestamp(p)
        assert ts is None


def test_extract_embedded_timestamp_bad_file_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "snap.json"
        p.write_text("this is not valid json {{{")
        ts = extract_embedded_timestamp(p)
        assert ts is None


# ---------------------------------------------------------------------------
# Test 3 — select_snapshot_as_of: selects latest embedded ts <= as_of
# ---------------------------------------------------------------------------

def test_select_snapshot_as_of_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        as_of = datetime(2026, 5, 6, 14, 0, 0, tzinfo=timezone.utc)

        # File with embedded_ts before as_of → eligible
        _make_snapshot(d, "snap_early.json", "2026-05-06T10:00:00+00:00")
        # File with embedded_ts exactly at as_of → eligible (<=)
        _make_snapshot(d, "snap_exact.json", "2026-05-06T14:00:00+00:00")
        # File with embedded_ts after as_of → excluded
        _make_snapshot(d, "snap_late.json", "2026-05-06T15:00:00+00:00")

        result = select_snapshot_as_of(d, "*.json", as_of)
        assert result is not None
        assert result.name == "snap_exact.json"


def test_select_snapshot_as_of_all_future_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        as_of = datetime(2026, 5, 5, 0, 0, 0, tzinfo=timezone.utc)

        _make_snapshot(d, "snap_future.json", "2026-05-06T10:00:00+00:00")

        result = select_snapshot_as_of(d, "*.json", as_of)
        assert result is None


# ---------------------------------------------------------------------------
# Test 4 — select_snapshot_as_of: mtime ≠ embedded ts (P0 core test)
#
# A file with a NEWER mtime but an OLDER embedded timestamp must be selected
# over a file with an older mtime but a newer (future) embedded timestamp.
# ---------------------------------------------------------------------------

def test_snapshot_selection_uses_embedded_ts_not_mtime():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        as_of = datetime(2026, 5, 6, 14, 0, 0, tzinfo=timezone.utc)

        # snap_old: newer mtime but embedded_ts AFTER as_of → should be EXCLUDED
        snap_old = d / "snap_old.json"
        _write_json(snap_old, {
            "fetched_at_utc": "2026-05-06T16:00:00+00:00",  # AFTER as_of
            "markets": [],
        })

        # snap_new: older mtime but embedded_ts BEFORE as_of → should be SELECTED
        snap_new = d / "snap_new.json"
        _write_json(snap_new, {
            "fetched_at_utc": "2026-05-06T12:00:00+00:00",  # BEFORE as_of
            "markets": [],
        })

        # Touch snap_old to give it a newer filesystem mtime
        import time
        time.sleep(0.05)
        snap_old.touch()

        # Verify mtime ordering (mtime-based would pick snap_old)
        assert os.path.getmtime(snap_old) > os.path.getmtime(snap_new), \
            "Pre-condition: snap_old has newer mtime"

        # Embedded-timestamp-based selection must ignore mtime and pick snap_new
        result = select_snapshot_as_of(d, "*.json", as_of)
        assert result is not None
        assert result.name == "snap_new.json", (
            f"Expected snap_new.json (embedded_ts before as_of) "
            f"but got {result.name}. "
            f"This means mtime was used instead of embedded timestamp — P0 bug!"
        )


# ---------------------------------------------------------------------------
# Test 5 — select_snapshot_as_of: file with no embedded timestamp is excluded
# ---------------------------------------------------------------------------

def test_snapshot_with_missing_embedded_ts_is_excluded():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        as_of = datetime(2026, 5, 6, 14, 0, 0, tzinfo=timezone.utc)

        # snap_no_ts: no embedded timestamp → must be excluded
        _write_json(d / "snap_no_ts.json", {"mode": "READ-ONLY", "markets": []})

        # snap_with_ts: has embedded ts before as_of → eligible
        _make_snapshot(d, "snap_with_ts.json", "2026-05-06T10:00:00+00:00")

        result = select_snapshot_as_of(d, "*.json", as_of)
        assert result is not None
        assert result.name == "snap_with_ts.json"


def test_snapshot_directory_with_only_no_ts_files_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        as_of = datetime(2026, 5, 6, 14, 0, 0, tzinfo=timezone.utc)

        _write_json(d / "snap_a.json", {"mode": "READ-ONLY"})
        _write_json(d / "snap_b.json", {"markets": []})

        result = select_snapshot_as_of(d, "*.json", as_of)
        assert result is None


# ---------------------------------------------------------------------------
# Test 6 — Settlement guard: blocked before settlement_as_of_time
# ---------------------------------------------------------------------------

def _make_open_ledger_jsonl(ledger_path: Path, ticker: str):
    """Creates a minimal open-trade ledger JSONL with a parseable ticker date."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    trade = {
        "market_ticker": ticker,
        "target_date": "2026-05-06",
        "execution_price": 0.60,
        "quantity": 10,
        "timestamp_utc": "2026-05-06T13:00:00+00:00",
        "status": "OPEN",
        "pnl": 0.0,
        "model_probability": 0.70,
        "forecast_bin": ">=85",
    }
    with open(ledger_path, "w") as f:
        f.write(json.dumps(trade) + "\n")


def test_settlement_blocked_before_settlement_as_of_time():
    """Settlement must not occur when settlement_as_of_time is before next-day 06:00 UTC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ledger = tmp / "ledger.jsonl"
        settlements = tmp / "settlements.jsonl"
        performance = tmp / "perf.json"

        # Ticker: trade date 2026-05-06
        # Settlement available at: 2026-05-07T06:00:00Z
        _make_open_ledger_jsonl(ledger, "KXHIGHMIA-26MAY06-B84.5")

        # Set settlement_as_of to same day — should be blocked
        settlement_as_of = datetime(2026, 5, 6, 23, 59, 59, tzinfo=timezone.utc)

        settle_paper_trades(
            ledger_path=ledger,
            settlements_path=settlements,
            performance_path=performance,
            settlement_as_of_time=settlement_as_of,
        )

        # Settlements file should NOT have any completed settlements
        assert not settlements.exists() or settlements.stat().st_size == 0, \
            "Settlement occurred before settlement_as_of_time — lookahead bug!"


def test_settlement_blocked_next_day_before_06_utc():
    """Settlement must be blocked even on next day if before 06:00 UTC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ledger = tmp / "ledger.jsonl"
        settlements = tmp / "settlements.jsonl"
        performance = tmp / "perf.json"

        _make_open_ledger_jsonl(ledger, "KXHIGHMIA-26MAY06-B84.5")

        # Next day but 05:59 — still before 06:00 cutoff
        settlement_as_of = datetime(2026, 5, 7, 5, 59, 0, tzinfo=timezone.utc)

        settle_paper_trades(
            ledger_path=ledger,
            settlements_path=settlements,
            performance_path=performance,
            settlement_as_of_time=settlement_as_of,
        )

        assert not settlements.exists() or settlements.stat().st_size == 0, \
            "Settlement occurred at 05:59 next day — should still be blocked!"


def test_settlement_proceeds_after_settlement_as_of_time():
    """Settlement must proceed when settlement_as_of_time is past next-day 06:00 UTC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ledger = tmp / "ledger.jsonl"
        settlements = tmp / "settlements.jsonl"
        performance = tmp / "perf.json"

        _make_open_ledger_jsonl(ledger, "KXHIGHMIA-26MAY06-B84.5")

        # Past next-day 06:00 — settlement window is open
        # Note: settle_paper_trades will try to load history. Since no history
        # file exists in this test, the trade will go to pending_count (actual_max=None).
        # The key assertion is that the settlement code REACHED the actual resolution
        # logic (past the availability guard), not that it found data.
        settlement_as_of = datetime(2026, 5, 7, 7, 0, 0, tzinfo=timezone.utc)

        settle_paper_trades(
            ledger_path=ledger,
            settlements_path=settlements,
            performance_path=performance,
            settlement_as_of_time=settlement_as_of,
        )

        # Performance file should be written (even if trade is pending due to missing history)
        # This proves the guard did not block — execution reached generate_performance_summary.
        assert performance.exists(), \
            "Performance file not written — settlement guard may have blocked prematurely."


# ---------------------------------------------------------------------------
# Test 7 — PaperLedger.record_trade stores model_probability and forecast_bin
# ---------------------------------------------------------------------------

def test_record_trade_stores_model_probability_and_forecast_bin():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "ledger.json"
        ledger = PaperLedger(ledger_path=ledger_path)

        ledger.record_trade(
            market_ticker="KXHIGHMIA-26MAY06-B84.5",
            target_date="2026-05-06",
            execution_price=0.60,
            quantity=10,
            model_probability=0.72,
            forecast_bin=">=85",
        )

        # Reload from disk
        reloaded = PaperLedger(ledger_path=ledger_path)
        trades = reloaded.ledger_data.get("trades", [])
        assert len(trades) == 1
        assert trades[0]["model_probability"] == 0.72
        assert trades[0]["forecast_bin"] == ">=85"


def test_record_trade_without_optional_fields():
    """record_trade must still work without model_probability and forecast_bin."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "ledger.json"
        ledger = PaperLedger(ledger_path=ledger_path)

        ledger.record_trade(
            market_ticker="KXHIGHMIA-26MAY06-B84.5",
            target_date="2026-05-06",
            execution_price=0.60,
            quantity=10,
        )

        reloaded = PaperLedger(ledger_path=ledger_path)
        trades = reloaded.ledger_data.get("trades", [])
        assert len(trades) == 1
        assert trades[0]["model_probability"] is None
        assert trades[0]["forecast_bin"] is None


# ---------------------------------------------------------------------------
# Test 8 — BacktestCoordinator initialization with as_of hour params
# ---------------------------------------------------------------------------

def test_backtest_coordinator_initialization():
    """Existing test: coordinator initializes correctly."""
    coordinator = BacktestCoordinator(
        start_date="2026-05-01",
        end_date="2026-05-03",
        fetcher_mode="local",
    )
    assert coordinator.start_date.year == 2026
    assert coordinator.start_date.month == 5
    assert coordinator.start_date.day == 1
    assert coordinator.end_date.day == 3
    assert coordinator.fetcher_mode == "local"
    assert coordinator.run_dir is not None


def test_backtest_coordinator_as_of_times_are_premarket():
    """forecast_as_of_time and market_snapshot_as_of_time must be before market close."""
    coordinator = BacktestCoordinator(
        start_date="2026-05-06",
        end_date="2026-05-06",
    )
    sim_date = datetime(2026, 5, 6, tzinfo=timezone.utc)

    forecast_as_of = coordinator._forecast_as_of_time(sim_date)
    market_as_of = coordinator._market_snapshot_as_of_time(sim_date)
    settlement_as_of = coordinator._settlement_as_of_time(sim_date)

    # Forecast cutoff must be same-day and well before midnight
    assert forecast_as_of.date() == sim_date.date()
    assert forecast_as_of.hour < 20, \
        f"forecast_as_of_time is too late ({forecast_as_of.hour}:00 UTC) — check for 23:59 regression"

    # Settlement cutoff must be NEXT DAY
    assert settlement_as_of.date() > sim_date.date(), \
        f"settlement_as_of_time ({settlement_as_of}) must be on the day after sim_date"
    assert settlement_as_of.hour == coordinator.settlement_next_day_hour_utc


def test_backtest_missing_data_handling():
    """Existing test: coordinator skips days gracefully when historical data is missing."""
    coordinator = BacktestCoordinator(
        start_date="2026-05-01",
        end_date="2026-05-01",
        fetcher_mode="local",
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        coordinator.run_dir = tmp_path
        coordinator.signals_dir = tmp_path / "signals"
        coordinator.ledger_path = tmp_path / "ledger.jsonl"
        coordinator.settlements_path = tmp_path / "settlements.jsonl"
        coordinator.performance_path = tmp_path / "perf.json"
        coordinator.manifest_path = tmp_path / "replay_manifest.json"

        coordinator.run_backtest()

        # Should complete without error. No perf file because no ledger was created.
        assert not coordinator.performance_path.exists()
        # Replay manifest must be written even when all days are skipped
        assert coordinator.manifest_path.exists(), \
            "Replay manifest must be written by run_backtest()"


# ---------------------------------------------------------------------------
# P1 Tests — SnapshotRegistry and replay manifest
# ---------------------------------------------------------------------------

def test_snapshot_registry_resolve_basic():
    """SnapshotRegistry.resolve() returns the eligible artifact with the latest embedded ts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        as_of = datetime(2026, 5, 6, 14, 0, 0, tzinfo=timezone.utc)
        sim_date = datetime(2026, 5, 6, tzinfo=timezone.utc)

        _write_json(d / "fore_2026-05-06_early.json", {
            "generated_at_utc": "2026-05-06T10:00:00+00:00",
            "probability_bins": {},
        })
        _write_json(d / "fore_2026-05-06_late.json", {
            "generated_at_utc": "2026-05-06T13:30:00+00:00",
            "probability_bins": {},
        })
        # Future file — must be excluded
        _write_json(d / "fore_2026-05-06_future.json", {
            "generated_at_utc": "2026-05-06T16:00:00+00:00",
            "probability_bins": {},
        })

        registry = SnapshotRegistry(search_roots={"forecast": d})
        result = registry.resolve("forecast", sim_date, as_of)

        assert result is not None
        assert "late" in result.name, (
            f"Expected the latest eligible file but got {result.name}"
        )


def test_snapshot_registry_resolve_unknown_type_returns_none():
    """SnapshotRegistry.resolve() must return None for unknown artifact types."""
    registry = SnapshotRegistry()
    sim_date = datetime(2026, 5, 6, tzinfo=timezone.utc)
    as_of = datetime(2026, 5, 6, 14, 0, 0, tzinfo=timezone.utc)

    result = registry.resolve("nonexistent_type", sim_date, as_of)
    assert result is None


def test_snapshot_registry_caches_results():
    """Calling resolve() twice with identical args returns the same Path without re-scanning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        as_of = datetime(2026, 5, 6, 14, 0, 0, tzinfo=timezone.utc)
        sim_date = datetime(2026, 5, 6, tzinfo=timezone.utc)

        _write_json(d / "snap_2026-05-06.json", {
            "generated_at_utc": "2026-05-06T10:00:00+00:00",
        })

        registry = SnapshotRegistry(search_roots={"forecast": d})

        result1 = registry.resolve("forecast", sim_date, as_of)
        # Add a new file that would be picked if cache were invalidated
        _write_json(d / "snap_2026-05-06_newer.json", {
            "generated_at_utc": "2026-05-06T13:00:00+00:00",
        })
        result2 = registry.resolve("forecast", sim_date, as_of)

        assert result1 == result2, (
            "Cache miss: resolve() returned different results for the same key"
        )


def test_snapshot_registry_lookup_log_populated():
    """lookup_log() must contain one entry per resolve() call."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        sim_date = datetime(2026, 5, 6, tzinfo=timezone.utc)
        as_of = datetime(2026, 5, 6, 14, 0, 0, tzinfo=timezone.utc)

        registry = SnapshotRegistry(search_roots={
            "forecast": d / "forecast",
            "market_snapshot": d / "market",
        })

        registry.resolve("forecast", sim_date, as_of)
        registry.resolve("market_snapshot", sim_date, as_of)

        log = registry.lookup_log()
        assert len(log) == 2

        types_logged = {e["artifact_type"] for e in log}
        assert "forecast" in types_logged
        assert "market_snapshot" in types_logged

        for entry in log:
            assert "target_date" in entry
            assert "as_of_time" in entry
            assert "resolved_path" in entry
            assert "reason" in entry


def test_backtest_coordinator_has_registry():
    """BacktestCoordinator must expose a _registry attribute."""
    coordinator = BacktestCoordinator(
        start_date="2026-05-06",
        end_date="2026-05-06",
    )
    assert hasattr(coordinator, "_registry")
    assert isinstance(coordinator._registry, SnapshotRegistry)


def test_replay_manifest_written_after_run_backtest():
    """run_backtest() must write a replay_manifest.json at the end of the run."""
    coordinator = BacktestCoordinator(
        start_date="2026-05-01",
        end_date="2026-05-01",
        fetcher_mode="local",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        coordinator.run_dir = tmp_path
        coordinator.signals_dir = tmp_path / "signals"
        coordinator.ledger_path = tmp_path / "ledger.jsonl"
        coordinator.settlements_path = tmp_path / "settlements.jsonl"
        coordinator.performance_path = tmp_path / "perf.json"
        coordinator.manifest_path = tmp_path / "replay_manifest.json"

        coordinator.run_backtest()

        assert coordinator.manifest_path.exists(), \
            "replay_manifest.json was not written by run_backtest()"


def test_replay_manifest_schema():
    """Replay manifest must contain all required schema fields and safety block."""
    coordinator = BacktestCoordinator(
        start_date="2026-05-01",
        end_date="2026-05-02",
        fetcher_mode="local",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        coordinator.run_dir = tmp_path
        coordinator.signals_dir = tmp_path / "signals"
        coordinator.ledger_path = tmp_path / "ledger.jsonl"
        coordinator.settlements_path = tmp_path / "settlements.jsonl"
        coordinator.performance_path = tmp_path / "perf.json"
        coordinator.manifest_path = tmp_path / "replay_manifest.json"

        coordinator.run_backtest()

        with open(coordinator.manifest_path) as f:
            manifest = json.load(f)

        assert "run_id" in manifest
        assert manifest["start_date"] == "2026-05-01"
        assert manifest["end_date"] == "2026-05-02"
        assert "as_of_config" in manifest
        assert "generated_at_utc" in manifest
        assert isinstance(manifest["lookups"], list)
        assert manifest.get("safety", {}).get("no_real_trading") is True, \
            "Manifest must include safety.no_real_trading=True"


def test_signal_generator_uses_embedded_ts_not_mtime():
    """
    signal_generator.generate_paper_signal() must raise ValueError when the
    snapshot's embedded timestamp is in the future relative to prediction_timestamp.
    It must NOT use os.path.getmtime().
    """
    import sys
    from paper_trading import signal_generator

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Write a minimal forecast JSON with an early embedded timestamp
        forecast_path = tmp / "kmia_forecast_2026-05-06_rules_v2_climatology_130000.json"
        _write_json(forecast_path, {
            "generated_at_utc": "2026-05-06T10:00:00+00:00",
            "probability_bins": {">=85": 0.6},
            "integer_distribution": {},
        })

        # Write a snapshot JSON whose embedded timestamp is AFTER prediction_timestamp
        snapshot_path = tmp / "kalshi_market_snapshot_future.json"
        _write_json(snapshot_path, {
            "fetched_at_utc": "2026-05-06T16:00:00+00:00",  # FUTURE embedded ts
            "mode": "READ-ONLY",
            "markets": [],
            "markets_found": 0,
            "warnings": [],
            "safety": {"no_real_trading": True},
        })

        prediction_timestamp = datetime(2026, 5, 6, 14, 0, 0, tzinfo=timezone.utc)

        # Must raise because snapshot embedded_ts (16:00) > prediction_timestamp (14:00)
        try:
            signal_generator.generate_paper_signal(
                forecast_path=forecast_path,
                snapshot_path=snapshot_path,
                prediction_timestamp=prediction_timestamp,
                output_dir=tmp,
                latest_path_override=tmp / "latest.json",
            )
            assert False, "ValueError was expected but not raised — mtime fallback bug?"
        except ValueError as e:
            assert "future" in str(e).lower() or "embedded" in str(e).lower() or "after" in str(e).lower(), \
                f"Wrong error message: {e}"


# ---------------------------------------------------------------------------
# Run manually (without pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_extract_embedded_timestamp_fetched_at_utc,
        test_extract_embedded_timestamp_generated_at_utc,
        test_extract_embedded_timestamp_timestamp_field,
        test_extract_embedded_timestamp_missing_returns_none,
        test_extract_embedded_timestamp_invalid_value_returns_none,
        test_extract_embedded_timestamp_bad_file_returns_none,
        test_select_snapshot_as_of_basic,
        test_select_snapshot_as_of_all_future_returns_none,
        test_snapshot_selection_uses_embedded_ts_not_mtime,
        test_snapshot_with_missing_embedded_ts_is_excluded,
        test_snapshot_directory_with_only_no_ts_files_returns_none,
        test_settlement_blocked_before_settlement_as_of_time,
        test_settlement_blocked_next_day_before_06_utc,
        test_settlement_proceeds_after_settlement_as_of_time,
        test_record_trade_stores_model_probability_and_forecast_bin,
        test_record_trade_without_optional_fields,
        test_backtest_coordinator_initialization,
        test_backtest_coordinator_as_of_times_are_premarket,
        test_backtest_missing_data_handling,
        # P1
        test_snapshot_registry_resolve_basic,
        test_snapshot_registry_resolve_unknown_type_returns_none,
        test_snapshot_registry_caches_results,
        test_snapshot_registry_lookup_log_populated,
        test_backtest_coordinator_has_registry,
        test_replay_manifest_written_after_run_backtest,
        test_replay_manifest_schema,
        test_signal_generator_uses_embedded_ts_not_mtime,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"FAIL: {t.__name__} — {e}")
            failed += 1
    print(f"\n{'ALL TESTS PASSED.' if not failed else f'{failed} TESTS FAILED.'}")
    exit(failed)

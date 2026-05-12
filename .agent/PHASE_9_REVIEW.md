# Agent 4 — Phase 9 Formal Review Report

**Date:** 2026-05-11  
**Agent:** Agent 4 — Backtesting and Calibration Agent  
**Model:** Claude Sonnet 4.6 (Thinking)  
**Task:** Phase 9 — Backtesting and Calibration formal review  
**Status:** NEEDS_FIXES_BEFORE_CONTINUATION

---

## 1. Inputs Read

- `1_Downloads/Multi-Agent Workflows/Mutl-Agentic Assignments.md`
- `1_Downloads/Timeline_Tasks/Task_Timeline_5.11.26.md`
- `.agent/SHARED_CONTEXT.md`
- `backend/src/backtesting/__init__.py`
- `backend/src/backtesting/coordinator.py`
- `backend/src/calibration/metrics.py`
- `backend/src/paper_trading/settlement.py`
- `backend/src/paper_trading/paper_ledger.py`
- `backend/src/shared/artifact_paths.py`
- `backend/tests/test_backtest_coordinator.py`
- `backend/tests/test_calibration_metrics.py`
- `backend/tests/run_tests.py`
- `scripts/run_backtest.sh`

## 2. Commands Run

- `git status --short` — summarized untracked/modified files
- `bash scripts/run_tests.sh` — full test suite (pass)
- `cd backend && PYTHONPATH=src .venv/bin/python -m pytest tests/test_backtest_coordinator.py -q` — blocked: pytest not installed in venv
- `cd backend && PYTHONPATH=src .venv/bin/python tests/run_tests.py` — blocked: pydantic/deps not in venv
- Various `grep_search` scans for lookahead/safety patterns

## 3. Git Status — Phase 9 Relevant Files

**Untracked (new, not yet committed):**
- `backend/src/backtesting/` (coordinator.py, __init__.py)
- `backend/tests/test_backtest_coordinator.py`
- `scripts/run_backtest.sh`

**Modified (Phase 9 touched):**
- `backend/src/calibration/metrics.py`
- `backend/src/paper_trading/settlement.py`
- `backend/src/shared/artifact_paths.py`
- `backend/tests/test_calibration_metrics.py`
- `backend/tests/run_tests.py`

**Confirmation:** No GitHub push occurred. All work is local-only.

## 4. Test Results

| Test Suite | Result |
|---|---|
| `bash scripts/run_tests.sh` (full suite, system .venv) | **ALL TESTS PASSED** |
| `test_backtest_coordinator_initialization` | **PASS** |
| `test_backtest_missing_data_handling` | **PASS** |
| `pytest backend/tests/test_calibration_metrics.py` | **BLOCKED** — pytest not installed in venv |
| `pytest backend/tests/test_backtest_coordinator.py` | **BLOCKED** — pytest not installed in venv |

Note: pytest is not installed in `backend/.venv` (pip list shows only pip 24.3.1). The test suite runs correctly via `run_tests.py` using the root `.venv` with full dependencies. Network is offline so pip install cannot resolve. Tests that ran via `run_tests.py` all passed including both backtest coordinator tests and all calibration metric tests (imported directly).

---

## 5. Safety Findings

✅ **PASS — No safety violations found in Phase 9 files.**

- `coordinator.py`: No live trading. No order placement. No credentials. Contains `# NO REAL TRADING` inherited via settlement import.
- `settlement.py`: Explicitly marked `# NO REAL TRADING EXECUTION / DRY-RUN / PAPER EVALUATION ONLY`. Safety field `{"no_real_trading": True}` present in every settlement record.
- `paper_ledger.py`: Local JSON writes only. No API calls, no execution paths.
- `run_backtest.sh`: No live flags. No credential injection. Runs coordinator in dry-run mode.
- `metrics.py`: Pure math functions. No I/O, no execution, no credentials.

---

## 6. Lookahead Safety Findings

### ❌ GAP 1 — No `forecast_as_of_time` parameter exists anywhere

The Phase 9 task spec requires every workflow step to accept:
- `target_date`
- `forecast_as_of_time`
- `market_snapshot_as_of_time`
- `weather_observation_as_of_time`
- `settlement_as_of_time`

**None of these `as_of` parameters exist in any source file.** Grep confirmed zero matches across all of `backend/src/`.

### ❌ GAP 2 — Snapshot selection uses `os.path.getmtime` (filesystem mtime), not embedded timestamps

In `coordinator.py` line 146, `_find_historical_snapshot()` uses `os.path.getmtime(f)` to filter snapshots.

**Problem:** File mtime is not a reliable as-of timestamp. If a file is copied, re-saved, or synced via Git/Drive, its mtime changes to the copy time — not the original data-capture time. This creates silent lookahead risk.

**Required fix:** Snapshot selection must parse the embedded `timestamp` field from inside the JSON file, not the filesystem mtime.

### ❌ GAP 3 — Coordinator hardcodes `prediction_timestamp` to end-of-day 23:59:59

At `coordinator.py` line 87:
```python
prediction_timestamp=current_date.replace(hour=23, minute=59, second=59)
```
This passes a 23:59:59 timestamp to `generate_paper_signal`, which means any forecast file from the same day (even late-day runs) will pass the future-check validation. In a real backtest, the prediction is made before market open (~9:30 AM ET). The timestamp should be `09:00` or a configurable `forecast_as_of_time`.

### ⚠️ PARTIAL — `settlement.py` has no `settlement_as_of_time` guard

`settle_paper_trades()` does not accept a `settlement_as_of_time` parameter. In a backtest replay, the coordinator calls settlement at the **end of the same simulated day** (`_run_final_settlement()`), meaning trades theoretically get settled with data that might not have been available yet. No guard prevents using actual KMIA max data before it would be officially published (typically NWS publishes the official daily high the following morning).

### ✅ PASS — No "latest" file fallback in backtest context without comment

`_find_historical_forecast()` at line 127-129 has a `pass` (no-op) fallback for missing historical data. It does **not** silently grab `latest_*` files. The comment explicitly notes "In a strict backtest we wouldn't use this."

### ✅ PASS — `generate_paper_signal` accepts explicit paths

`signal_generator.py` accepts `forecast_path`, `snapshot_path`, and `prediction_timestamp`. The coordinator correctly passes these, avoiding "latest" file lookups in backtest context.

---

## 7. Point-in-Time Artifact Selection Gaps

| Artifact Type | Can select as-of timestamp? | Method | Gap? |
|---|---|---|---|
| Forecast distribution snapshot | ⚠️ Partial | Date-string glob match on filename | No time-of-day precision; no `forecast_as_of_time` param |
| Kalshi market snapshot | ⚠️ Partial | `os.path.getmtime` filtering | Uses filesystem mtime, not embedded timestamp |
| NWS/TWC/weather snapshot | ❌ None | Not wired into coordinator at all | No integration point exists yet |
| Paper signal snapshot | ✅ Yes | Passed explicitly via `latest_path_override` | OK |
| Settlement data | ❌ None | No `settlement_as_of_time` guard | Settles same-day without availability check |

**No point-in-time snapshot registry exists.** There is no centralized structure that maps `(target_date, as_of_time)` → artifact path. Each `_find_historical_*` function implements ad hoc lookup.

---

## 8. Calibration Metrics Findings

| Metric | Implemented? | Notes |
|---|---|---|
| Brier score (multiclass) | ✅ Yes | `brier_score_multiclass()` — correct |
| CRPS for fixed bins | ✅ Yes | `crps_multiclass()` — CDF-based, ordered bins |
| Expected Calibration Error | ✅ Yes | `expected_calibration_error()` — 10-bin bucketing |
| Log loss | ✅ Yes | `log_loss_multiclass()` with epsilon clipping |
| Top-bin hit rate | ✅ Yes | `score_prediction()` returns `top_bin_hit` |
| Aggregate stats | ✅ Yes | `calculate_aggregate_stats()` |
| Reliability bins (per-bin calibration curve) | ❌ Missing | No function produces a reliability diagram data structure |
| Calibration by lead-time bucket | ❌ Missing | No `lead_time_hours` field in metrics output |
| Raw TWC vs. corrected TWC vs. blended comparison | ❌ Missing | `score_prediction()` takes one distribution; no multi-source comparison |
| Brier score by contract threshold | ❌ Missing | `brier_score_multiclass()` uses fixed bins; no per-threshold integration |
| CRPS for continuous daily max (integer-level) | ❌ Missing | Current CRPS operates on fixed bins, not integer-level distribution |

**5 of 11 required calibration metrics are missing.**

---

## 9. Settlement Reconciliation Findings

| Requirement | Status | Notes |
|---|---|---|
| Uses official/approved actual high source | ✅ Pass | `load_history()` from `kmia_daily_history.jsonl` + manual corrections override |
| No settlement before data available | ❌ Gap | No `settlement_as_of_time` guard; can settle same-day in backtest |
| Records expected model probability vs. actual outcome | ⚠️ Partial | `model_probability` stored in settlement record from ledger, but ledger's `record_trade()` does not save `model_probability` or `forecast_bin` — these would be missing for new-style trades |
| Missing/late settlement handled safely | ✅ Pass | `pending_count` tracked; unsettled trades simply left pending |
| PaperLedger stores expected model probability | ❌ Gap | `record_trade()` does not accept or store `model_probability` or `expected_bin` fields |

---

## 10. Gaps Found (Priority Order)

1. **[P0] No `as_of_time` parameters** — None of the 5 required `as_of` parameters (`forecast_as_of_time`, `market_snapshot_as_of_time`, `weather_observation_as_of_time`, `settlement_as_of_time`) exist in coordinator or loaders.

2. **[P0] Snapshot selection uses filesystem mtime** — `_find_historical_snapshot()` uses `os.path.getmtime()` instead of the embedded JSON `timestamp` field. Silent lookahead risk.

3. **[P1] Prediction timestamp hardcoded to 23:59:59** — Backtest treats predictions as made at end-of-day; should use a configurable pre-market time (e.g., `09:00 ET`).

4. **[P1] No settlement availability guard** — `settle_paper_trades()` settles without checking if the official high would have been published yet at the simulated time.

5. **[P1] `PaperLedger.record_trade()` does not store `model_probability` or `forecast_bin`** — These are required for Brier/CRPS scoring at settlement time. The settlement logic retrieves these from the ledger, but they are never written there.

6. **[P2] No point-in-time snapshot registry** — Artifact lookup is ad hoc. A `SnapshotRegistry` mapping `(date, as_of_time)` → path is needed for reproducible replays.

7. **[P2] No replay input manifest** — Backtests produce no manifest listing exactly which artifact files were used for each simulated day, making audit and reproduction impossible.

8. **[P2] Calibration: No reliability diagram data** — `reliability_bins()` function not implemented.

9. **[P2] Calibration: No lead-time bucketing** — Metrics cannot separate performance by hours-before-market.

10. **[P2] Calibration: No multi-source comparison** — Cannot score raw TWC vs. corrected TWC vs. blended distribution separately.

11. **[P3] Venv missing pytest and all dependencies** — `backend/.venv` contains only pip. `pytest` and project requirements must be installed to run isolated tests.

---

## 11. Required Fixes Before Continuation

### Fix 1 (P0): Add `as_of` parameters to coordinator and loaders

- Add `forecast_as_of_time: Optional[datetime]`, `market_snapshot_as_of_time: Optional[datetime]`, `weather_observation_as_of_time: Optional[datetime]`, `settlement_as_of_time: Optional[datetime]` to `BacktestCoordinator.__init__()` and `_simulate_day()`.
- Pass `forecast_as_of_time` to `_find_historical_forecast()` and use it for filename timestamp filtering.
- Pass `market_snapshot_as_of_time` to `_find_historical_snapshot()`.
- Pass `settlement_as_of_time` to `settle_paper_trades()`.

### Fix 2 (P0): Replace mtime with embedded JSON timestamp in snapshot lookup

- In `_find_historical_snapshot()`: open each candidate JSON file and read its embedded `timestamp` field. Filter on that, not `os.path.getmtime()`.

### Fix 3 (P1): Set prediction timestamp to pre-market time (configurable)

- Replace `current_date.replace(hour=23, minute=59, second=59)` with a configurable `forecast_as_of_time` defaulting to `09:00 UTC` (approximately KMIA pre-market).

### Fix 4 (P1): Add settlement availability guard to `settle_paper_trades()`

- Add `settlement_as_of_time: Optional[datetime]` parameter.
- Only settle trades where `settlement_as_of_time > trade_date + 1 day` (official high published next morning).

### Fix 5 (P1): Store `model_probability` and `forecast_bin` in `PaperLedger.record_trade()`

- Add `model_probability: float` and `forecast_bin: str` parameters to `record_trade()`.
- Store them in the trade record JSON.

---

## 12. Recommended Next Implementation Task

**Fix 2 (P0): Replace mtime with embedded JSON timestamp** is the highest-risk silent bug and simplest to fix.

Follow with **Fix 1 (P0): Add `as_of` parameters** as it unlocks all downstream correctness for the full replay pipeline.

**Recommended task sequence:**
1. Fix embedded timestamp lookup in `_find_historical_snapshot()`
2. Add `as_of` parameters to coordinator + loaders
3. Fix prediction timestamp to configurable pre-market time
4. Add settlement availability guard
5. Store `model_probability` and `forecast_bin` in ledger
6. Add point-in-time snapshot registry
7. Add replay input manifest
8. Add reliability diagram, lead-time bucketing, and multi-source calibration to `metrics.py`

---

## 13. Phase 9 Status

**NEEDS_FIXES_BEFORE_CONTINUATION**

The scaffold is structurally sound and has no safety violations. Core calibration metrics (Brier, CRPS, ECE) are implemented and tested. Both backtest coordinator tests pass. However, the P0 lookahead gaps (mtime-based snapshot selection, missing `as_of` parameters, end-of-day prediction timestamp) make the coordinator unsuitable for producing valid, non-leaking backtest results in its current form.

---

## 14. Machine-Readable JSON Summary

```json
{
  "agent": "Agent 4 — Backtesting and Calibration Agent",
  "model": "Claude Sonnet 4.6 (Thinking)",
  "task": "Phase 9 — Backtesting and Calibration formal review",
  "files_inspected": [
    "backend/src/backtesting/__init__.py",
    "backend/src/backtesting/coordinator.py",
    "backend/src/calibration/metrics.py",
    "backend/src/paper_trading/settlement.py",
    "backend/src/paper_trading/paper_ledger.py",
    "backend/src/shared/artifact_paths.py",
    "backend/tests/test_backtest_coordinator.py",
    "backend/tests/test_calibration_metrics.py",
    "backend/tests/run_tests.py",
    "scripts/run_backtest.sh",
    ".agent/SHARED_CONTEXT.md",
    "1_Downloads/Multi-Agent Workflows/Mutl-Agentic Assignments.md",
    "1_Downloads/Timeline_Tasks/Task_Timeline_5.11.26.md"
  ],
  "commands_run": [
    "git status --short",
    "bash scripts/run_tests.sh",
    "grep_search lookahead patterns in coordinator.py",
    "grep_search as_of parameters in backend/src",
    "grep_search mtime usage in coordinator.py",
    "grep_search reliability/lead-time/source-split in metrics.py"
  ],
  "tests_run": [
    {
      "test": "bash scripts/run_tests.sh (full suite via run_tests.py)",
      "result": "ALL TESTS PASSED",
      "includes_phase9": true,
      "backtest_coordinator_tests": "PASS",
      "calibration_metric_tests": "PASS"
    },
    {
      "test": "pytest backend/tests/test_backtest_coordinator.py",
      "result": "BLOCKED — pytest not installed in backend/.venv"
    },
    {
      "test": "pytest backend/tests/test_calibration_metrics.py",
      "result": "BLOCKED — pytest not installed in backend/.venv"
    }
  ],
  "safety_findings": [
    "PASS: No live trading, order placement, or credential leakage in any Phase 9 file",
    "PASS: settlement.py has explicit safety disclaimer and no_real_trading=True in all records",
    "PASS: run_backtest.sh has no live execution flags"
  ],
  "lookahead_safety_findings": [
    "GAP_P0: No forecast_as_of_time, market_snapshot_as_of_time, weather_observation_as_of_time, or settlement_as_of_time parameters exist anywhere in backend/src",
    "GAP_P0: _find_historical_snapshot() uses os.path.getmtime() instead of embedded JSON timestamp — silent lookahead risk on file copy/sync",
    "GAP_P1: prediction_timestamp hardcoded to 23:59:59 in coordinator — should be pre-market time (~09:00 ET)",
    "GAP_P1: settle_paper_trades() has no settlement_as_of_time guard — can settle same-day in backtest",
    "PASS: No silent 'latest' file fallback in backtest context",
    "PASS: generate_paper_signal() accepts explicit forecast_path and snapshot_path"
  ],
  "calibration_metric_findings": [
    "PASS: brier_score_multiclass implemented",
    "PASS: crps_multiclass implemented (fixed-bin CDF-based)",
    "PASS: expected_calibration_error implemented",
    "PASS: log_loss_multiclass implemented",
    "PASS: score_prediction and calculate_aggregate_stats implemented",
    "GAP_P2: No reliability_bins() function for reliability diagram",
    "GAP_P2: No lead_time_hours field or bucketing by lead time",
    "GAP_P2: No multi-source comparison (raw_twc vs corrected_twc vs blended)",
    "GAP_P2: No Brier score by contract threshold (current is fixed-bin only)",
    "GAP_P2: No CRPS over continuous integer-level distribution"
  ],
  "settlement_reconciliation_findings": [
    "PASS: load_history() uses kmia_daily_history.jsonl as official source",
    "PASS: manual corrections override supported",
    "PASS: pending trades tracked safely when actual max unavailable",
    "GAP_P1: No settlement_as_of_time guard — settles same-day in backtest replay",
    "GAP_P1: PaperLedger.record_trade() does not store model_probability or forecast_bin — settlement cannot retrieve them from ledger"
  ],
  "gaps_found": [
    "P0: No as_of_time parameters in coordinator or any loader",
    "P0: Snapshot selection uses filesystem mtime not embedded JSON timestamp",
    "P1: prediction_timestamp hardcoded to 23:59:59 (should be ~09:00 ET pre-market)",
    "P1: No settlement availability guard in settle_paper_trades()",
    "P1: PaperLedger.record_trade() missing model_probability and forecast_bin fields",
    "P2: No point-in-time snapshot registry",
    "P2: No replay input manifest",
    "P2: No reliability diagram function in metrics.py",
    "P2: No lead-time bucketing in calibration",
    "P2: No multi-source (raw TWC / corrected / blended) comparison report",
    "P3: backend/.venv missing pytest and all project dependencies"
  ],
  "required_fixes": [
    "Fix 1 (P0): Add as_of parameters to BacktestCoordinator and all loaders",
    "Fix 2 (P0): Replace os.path.getmtime with embedded JSON timestamp in _find_historical_snapshot()",
    "Fix 3 (P1): Make prediction_timestamp configurable, default to 09:00 ET pre-market",
    "Fix 4 (P1): Add settlement_as_of_time guard to settle_paper_trades()",
    "Fix 5 (P1): Add model_probability and forecast_bin to PaperLedger.record_trade()"
  ],
  "phase_9_status": "NEEDS_FIXES_BEFORE_CONTINUATION",
  "recommended_next_implementation_task": "Fix embedded JSON timestamp lookup in _find_historical_snapshot(), then add as_of parameters to BacktestCoordinator — these two P0 fixes are the prerequisite for all valid backtest replay."
}
```

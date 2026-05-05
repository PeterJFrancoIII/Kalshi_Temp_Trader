# Full Project Review — KMIA Kalshi Temperature Prediction App

**Reviewer**: Opus 4.6 (acting as senior architect, QA lead, and safety reviewer)
**Date**: 2026-05-03
**Project Root**: `/Users/computer/Desktop/App Development/Kalshi`

---

## Executive Summary

The KMIA Kalshi Temperature Prediction App is in a **solid early-MVP state**. The codebase demonstrates thoughtful architecture: a clean separation between ingestion, forecasting, calibration, recommendation, and paper-trading layers. Two forecast models (v1 rules-based, v2 climatology-blended) are implemented and can be run individually or in comparison mode. A 75-test suite passes cleanly via `bash scripts/run_tests.sh`. No real-money trading code exists anywhere in the codebase.

**Key strengths**: Strong safety posture, solid data-source separation (CLIMIA as truth, live data as preliminary), proper impossible-bin zeroing, and a well-structured recommendation/gate system.

**Key risks**: A missing `model_version` column in the DB model will crash non-dry-run saves; a production-critical Pydantic mock in `settlement_check.py` undermines validation; root-level legacy files (`parsers/`, `models/`) create confusion; and the JSONL paper-trading store has no concurrency protection.

**Verdict**:
- ✅ Ready for dry-run forecasting
- ⚠️ Ready for paper trading (with P0/P1 fixes)
- ❌ Not ready for real trading (by design and policy)

---

## System Map

| Module | Location | Responsibility |
| :--- | :--- | :--- |
| **Shared Types** | `backend/src/shared/types.py` | Pydantic models: `TemperatureBins`, `DailyPrediction`, `ClimiaReport`, `LiveObservation`, etc. |
| **Ingestion — CLIMIA** | `backend/src/ingestion/climia_parser.py`, `climia_fetcher.py` | Parse NWS CLIMIA text reports; fetch raw text |
| **Ingestion — Live** | `backend/src/ingestion/kmia_live_fetcher.py`, `kmia_obhistory_parser.py` | Fetch and parse WRH JSON and ObHistory HTML |
| **Ingestion — Historical** | `backend/src/ingestion/local_climatology_loader.py`, `climia_backfill.py` | Load local NOAA CSV, write JSONL |
| **Ingestion — IEM** | `backend/src/ingestion/historical_weather_sources.py` | Fetch from Iowa Environmental Mesonet |
| **Features — Live** | `backend/src/features/live_features.py` | Compute observed max, trends, flags, staleness |
| **Features — Climatology** | `backend/src/features/climatology_features.py` | Historical bin distributions, rolling averages, normals |
| **Forecasting — v1** | `backend/src/forecasting/rules_model.py` | Heuristic rules-based forecast |
| **Forecasting — v2** | `backend/src/forecasting/rules_model_v2.py` | Climatology-blended forecast |
| **Forecasting — Climatology** | `backend/src/forecasting/climatology_model.py` | Climatology prior computation |
| **Forecasting — Bins** | `backend/src/forecasting/bin_converter.py` | `temp_to_bin()`, `bin_to_range()` |
| **Calibration** | `backend/src/calibration/metrics.py`, `comparison.py`, `reports.py` | Brier score, log loss, model comparison, settlement scoring |
| **Dashboard/Reports** | `backend/src/dashboard/report_generator.py` | Markdown + HTML report generation |
| **Kalshi Client** | `backend/src/kalshi/client.py` | Read-only unauthenticated API client |
| **Kalshi Market Mapper** | `backend/src/kalshi/weather_market_mapper.py` | Map Kalshi subtitles to internal bins |
| **Kalshi Orderbook** | `backend/src/kalshi/orderbook.py` | Orderbook metric extraction |
| **Kalshi Discovery** | `backend/src/kalshi/market_discovery.py` | Find Miami daily high markets |
| **Recommendation** | `backend/src/recommendation/` | EV calculation, safety gates, recommendation engine |
| **Paper Trading** | `backend/src/paper_trading/persistence.py`, `simulator.py` | Simulated fills and settlements via JSONL |
| **Storage** | `backend/src/storage/jsonl_store.py` | Generic JSONL append/read/update store |
| **Scheduler** | `backend/src/scheduler/run_daily_prediction.py`, `settlement_check.py` | Daily prediction orchestration, settlement dry-run |
| **DB Models** | `backend/src/db/models.py`, `session.py` | SQLAlchemy ORM: predictions, settlements, calibration, Kalshi markets |

---

## Current Capabilities

What works today:

1. ✅ Live KMIA observation ingestion and parsing (WRH JSON + ObHistory HTML)
2. ✅ CLIMIA report parsing (normal, missing, trace, record, correction detection)
3. ✅ Local NOAA historical file loading (1950–2026, station USW00012839)
4. ✅ Historical JSONL backfill pipeline
5. ✅ Climatology feature computation (same-day history, windowed prior, rolling average)
6. ✅ Forecast Model v1 (rules-based heuristic)
7. ✅ Forecast Model v2 (climatology + forecast blend with weather suppression)
8. ✅ Impossible-bin zeroing (hard constraint)
9. ✅ Probability validation and normalization
10. ✅ Daily prediction pipeline with dry-run, model selection, and comparison mode
11. ✅ Markdown + HTML report generation
12. ✅ CLIMIA settlement workflow (dry-run)
13. ✅ Calibration scoring (Brier, log loss, top-bin hit)
14. ✅ Model comparison with winner fields and deltas
15. ✅ Kalshi read-only client (unauthenticated, public API)
16. ✅ Kalshi market-to-bin mapping
17. ✅ Orderbook metric extraction
18. ✅ Recommendation/EV engine with sequential safety gates
19. ✅ Paper-trading persistence and simulation
20. ✅ 75-test suite (all passing)

---

## Test Status

```
Command: bash scripts/run_tests.sh
Result:  ALL 75 TESTS PASSED (0 failures)

Tests cover:
  - Calibration metrics (7 tests)
  - Kalshi market mapping + safety (6 tests)
  - KMIA live parser + ObHistory (12 tests)
  - CLIMIA parser (4 tests)
  - Temperature bins + rules model v1 (9 tests)
  - Daily prediction loop (5 tests)
  - Settlement check (2 tests)
  - Full pipeline read-only (5 tests)
  - Paper trading (7 tests)
  - Historical backfill (2 tests)
  - Local climatology loader (2 tests)
  - Climatology features (6 tests)
  - Model comparison (6 tests)
  - Rules model v2 (10 tests via unittest)
```

> [!WARNING]
> The test runner (`run_tests.py`) mocks out `pydantic`, `bs4`, `requests`, `sqlalchemy`, `dateutil`, and `pytest` when they are not installed. This means tests can pass even when critical libraries are missing. In production, this masking is dangerous — see P1 issues below.

---

## Architecture Findings

### Strengths

1. **Clean layer separation**: Ingestion → Features → Forecasting → Calibration → Recommendation → Paper Trading is well-structured.
2. **Two forecast models** available with comparison mode.
3. **Hard constraints enforced consistently**: `zero_impossible_bins()` is shared between v1 and v2.
4. **Safety gates** in the recommendation layer are explicit and sequential.
5. **Dry-run mode** works cleanly without a database.
6. **Reports** include both machine-readable (JSON) and human-readable (MD, HTML) formats.

### Weaknesses

1. **Root-level legacy files**: `parsers/climia.py`, `parsers/live_sensor.py`, `models/probability.py` are **abandoned duplicates** of the backend modules. They use different class structures (e.g., `ClimiaParser` class vs. `parse_climia_report` function), import `scipy` (not in requirements), and create confusion about which code is canonical.

2. **Inconsistent import styles**: Some modules use `from src.X.Y import Z` (e.g., `market_discovery.py`, `calibration/metrics.py`, `calibration/comparison.py`), while others use bare `from X.Y import Z`. This works because PYTHONPATH includes `src/`, but `from src.X` will break if run without the parent in the path.

3. **`run_daily_prediction.py` sys.path hacking**: Lines 10-11 insert `../..` into sys.path, then import with `from src.X.Y`. This creates a fragile dual-path situation.

4. **`settlement_check.py` Pydantic mock (line 12-21)**: This file contains a **production-path mock** that replaces Pydantic with a MagicMock if the import fails. This is extremely dangerous — it means the CLIMIA parser and calibration scoring will run without any Pydantic validation in production if pydantic is missing.

5. **`REQUIRED_BINS` defined in 6+ places**: `shared/types.py`, `rules_model.py`, `rules_model_v2.py`, `climatology_model.py`, `climatology_features.py`, `calibration/metrics.py`, `dashboard/report_generator.py`. A single authoritative source should be used.

6. **`DailyPrediction` DB model missing `model_version` column**: The `run_daily_prediction.py` scheduler references `DailyPrediction.model_version` for idempotency checks and saving, but the SQLAlchemy model in `db/models.py` has **no `model_version` column**. This will crash on any non-dry-run execution.

---

## Data Pipeline Findings

### Source Role Separation: ✅ Correct

- **CLIMIA**: Used as final settlement truth via `climia_parser.py` → `get_settlement_max_temp()`.
- **Live WRH/ObHistory**: Marked `is_preliminary=True` in `ParsedObservation`.
- **Local NOAA file**: Used only for historical climatology (station-filtered to USW00012839).
- **Kalshi**: Read-only client, no authentication.

### Data Quality

| Check | Status |
| :--- | :--- |
| Live vs. settlement properly separated | ✅ |
| Missing/malformed CLIMIA handled | ✅ (warnings, None returns) |
| Missing TMAX in historical data handled | ✅ (`quality_flags`, None values) |
| Stale data detection | ✅ (90-min threshold in `live_features.py`) |
| Timezone handling | ⚠️ Mostly correct — uses `dateutil.tz.gettz('US/Eastern')`, but some paths use naive datetimes. `simulator.py` uses `datetime.utcnow()` which returns naive UTC (deprecated in Python 3.12+). |
| Station filtering | ✅ `USW00012839` enforced in `local_climatology_loader.py` |
| JSONL historical output | ✅ Stable, well-structured |

### Issue: Two Historical Data Paths

There are two different JSONL files:
- `backend/data/processed/history/kmia_historical_highs.jsonl` (root-level data)
- `backend/src/backend/data/processed/history/kmia_daily_history.jsonl` (nested inside `src/`)

The scheduler references `backend/data/processed/history/kmia_daily_history.jsonl` (relative to `run_daily_prediction.py`). The nested path inside `src/` is suspicious — it may be an artifact of a test run or misconfigured output path.

---

## Forecasting Findings

### Model v1 (`rules_model.py`)

- ✅ Uses forecast high as baseline with weather suppression
- ✅ Hard floor at observed max
- ✅ Zeroes impossible bins, normalizes
- ✅ All 6 bins always present
- ⚠️ Uses `datetime.now().date().isoformat()` for the date field instead of accepting a target date parameter — this is fine for live use but makes backtesting v1 awkward
- ⚠️ Does not include `model_version` in its output (added by scheduler)

### Model v2 (`rules_model_v2.py`)

- ✅ 45/45/10 climatology-forecast blend
- ✅ Weather suppression applied after blend
- ✅ Hard impossible-bin constraints applied after suppression
- ✅ Normalizes and validates
- ✅ Includes `model_version: "rules_v2_climatology"` in output
- ✅ Lookahead prevention in `climatology_features.py` line 81: excludes same-year records at or after target date
- ✅ Graceful fallback to uniform prior when no history available

### Issue: `best_single_number_f` in v2

Line 169: `best_single_number_f = forecast_high_f if forecast_high_f else 82`. This falls back to 82 even if the peak probability bin is, say, >=87. The "best single number" should arguably be derived from the probability distribution (e.g., weighted mean or mode), not just the forecast input.

---

## Calibration and Model Comparison Findings

### Metrics Implementation

- ✅ `brier_score_multiclass`: Correct formula `sum((p_i - y_i)^2)`
- ✅ `log_loss_multiclass`: Correct with epsilon clipping at `1e-15`
- ✅ `top_bin`: Returns highest-probability bin
- ✅ `validate_probabilities`: Checks bins, range, and sum

### Model Comparison (`comparison.py`)

- ✅ Correct winner logic with tolerance (`1e-12`)
- ✅ Brier/log-loss deltas are `v2 - v1` (negative = v2 better for Brier/log-loss)
- ✅ Summary string generation is deterministic
- ⚠️ `write_comparison_markdown` references `report["v1"].get("probabilities", {})` (line 169) but `score_prediction` returns keys like `final_max_temp_f`, `actual_bin`, etc. — **not** a `probabilities` key. This means the per-bin table in the markdown report will show all zeros. The data is present in the `rules_v1` and `rules_v2_climatology` summary objects but the legacy `v1`/`v2` keys from `score_prediction` don't include raw probabilities.

---

## Kalshi / Recommendation Safety Findings

### Read-Only Status: ✅ Confirmed

- `KalshiPublicClient` only exposes GET methods: `get_events`, `get_markets`, `get_market`, `get_orderbook`.
- No `POST`, `PUT`, `DELETE` methods exist.
- No authentication (no API key, no login, no token).
- Security grep for `create_order`, `submit_order`, `cancel_order`, `place_order`, `market_order` returned **zero results** in application code (only found in a test that verifies their absence).
- No API keys or secrets are hardcoded anywhere in the codebase.

### Recommendation Layer

- ✅ Sequential gates: mapping → confidence → staleness → spread → liquidity → edge
- ✅ Fee calculation uses `0.07 * p * (1-p)` with `p` in probability units (0–1) — correct
- ✅ Implied probability calculated as `yes_ask_cents / 100.0` — correct
- ✅ Every recommendation includes explicit reason strings
- ✅ `TRADE_CANDIDATE` only if edge after fees exceeds threshold (default 5%)
- ✅ Actions are `WATCH`, `TRADE_CANDIDATE`, `REJECT` — no `EXECUTE` or `PLACE` action exists

### Market Mapping

- ⚠️ Coverage is limited to exact text patterns ("78° or lower", "79° to 80°", etc.). Novel Kalshi subtitle formats may produce `uncertain_mapping: True`, which correctly triggers a `REJECT` gate. This is safe but could miss valid markets.

### Orderbook

- ⚠️ The orderbook parser uses `orderbook_fp.yes_dollars` and `no_dollars` — this appears to match Kalshi's API structure, but the field names may change. The code defaults to 0 cents if no bids are present, which is safe.

---

## Paper-Trading Findings

- ✅ No real orders are placed (verified by security scan)
- ✅ Simulated fill logic: fills at ask price if liquidity > 0
- ✅ Settlement logic: determines bin hit, calculates PnL in cents (0–100 scale)
- ✅ PnL = `settlement_value - entry_price` — consistent units (cents)
- ✅ Storage schema is documented in `docs/paper_trading.md`

### Issues

- ⚠️ `simulator.py` uses `datetime.utcnow()` (lines 29, 85) — deprecated in Python 3.12+. Should use `datetime.now(timezone.utc)`.
- ⚠️ JSONL store `update_record` (line 34-52 of `jsonl_store.py`) rewrites the entire file for each update — no file locking or concurrency protection. Documented in the store's docstring but could corrupt data under concurrent access.
- ⚠️ `settle_paper_trade` checks `status == 'FILLED'` but doesn't validate that `target_bin` uses the same bin format as calibration.

---

## Documentation Findings

| Document | Status | Notes |
| :--- | :--- | :--- |
| `README.md` | ✅ Good | Python-first, setup instructions, test command |
| `MASTER_CONTEXT.md` | ✅ Good | Bins, data sources, critical rules, output JSON |
| `CODE_GOVERNANCE.md` | ✅ Good | Safety rules, no real trading, Python-first frontend note |
| `DATA_SOURCES.md` | ✅ Good | Source URLs present |
| `WEATHER_MODEL_SPEC.md` | ✅ Good | Bins, hard constraint, modeling layers |
| `AGENT_WORKPLAN.md` | ✅ Good | Agent ownership is clear |
| `docs/architecture.md` | ✅ Good | Module descriptions match implementation |
| `docs/operational_loop.md` | ✅ Good | CLI examples correct, model selection documented |
| `docs/paper_trading.md` | ✅ Good | Schema documented, no-real-trading warning present |
| `docs/testing_plan.md` | ✅ Good | Test categories documented |
| `docs/calibration.md` | ✅ Present | |
| `docs/model_comparison.md` | ✅ Present | |
| `docs/kalshi_readonly.md` | ✅ Present | |
| `docs/recommendation_layer.md` | ✅ Present | |
| `docs/historical_backfill.md` | ✅ Present | |
| `docs/forecast_model_v2.md` | ✅ Present | |

> [!NOTE]
> React/frontend references have been properly removed or marked as future Streamlit work in `CODE_GOVERNANCE.md` and `README.md`.

---

## Security / Trading Safety Findings

### Explicit Confirmation

| Check | Result |
| :--- | :--- |
| `create_order` in codebase | ❌ Not found (only in test verifying absence) |
| `submit_order` in codebase | ❌ Not found |
| `cancel_order` in codebase | ❌ Not found |
| `place_order` in codebase | ❌ Not found |
| `market_order` in codebase | ❌ Not found |
| API keys hardcoded | ❌ Not found |
| Private keys hardcoded | ❌ Not found |
| `ENABLE_REAL_TRADING` flag | ❌ Not found (by design — not implemented) |
| Authentication in Kalshi client | ❌ Not present — client is fully unauthenticated |
| Dangerous temporary execution paths | ❌ Not found |

**Conclusion**: The codebase is clean of any real-trading execution logic. The Kalshi integration is genuinely read-only.

---

## Prioritized Issues

### P0 — Must Fix Before Next Run

| # | File | Issue | Why It Matters | Fix | Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `backend/src/db/models.py` | `DailyPrediction` model missing `model_version` column | `run_daily_prediction.py` references `DailyPrediction.model_version` for idempotency and save — will crash on any non-dry-run | Add `model_version = Column(String)` to the `DailyPrediction` class | Add test that constructs a `DailyPrediction` with `model_version` |
| 2 | `backend/src/scheduler/settlement_check.py` | Pydantic mock in production path (lines 10-21) | If pydantic is missing, settlement runs with zero validation — silent data corruption | Remove the mock; require pydantic as a hard dependency | Add an import test for `settlement_check` that fails without pydantic |

### P1 — Should Fix Before Paper-Trading Evaluation

| # | File | Issue | Why It Matters | Fix | Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 3 | `backend/tests/run_tests.py` | Mocks out pydantic, bs4, requests, sqlalchemy when missing (lines 11-78) | Tests pass without real validation — gives false confidence | Remove mocks; add a requirements check at the top of `run_tests.py` that exits with a clear message if deps are missing | N/A (environment setup) |
| 4 | Root-level `parsers/`, `models/`, `kalshi/`, `database/`, `tests/` | Legacy/abandoned code at project root | Creates confusion about canonical code location; `models/probability.py` imports `scipy` which isn't in requirements | Delete these directories or move them to an `archive/` folder | N/A |
| 5 | `backend/src/calibration/comparison.py` line 169 | `report["v1"].get("probabilities", {})` — key doesn't exist | Per-bin Markdown comparison table shows all zeros | Pass the original probability dicts into the comparison result or store them under a `probabilities` key | Test that comparison markdown contains non-zero probability values |
| 6 | `backend/src/scheduler/run_daily_prediction.py` lines 10-11 | `sys.path` manipulation + mixed `from src.X` and `from X` imports | Fragile import paths; breaks if PYTHONPATH isn't set exactly right | Standardize all imports to use bare module paths (consistent with PYTHONPATH=src) | N/A (structural) |
| 7 | Multiple files | `REQUIRED_BINS` defined in 6+ separate files | Risk of drift if bins ever change | Import from `shared/types.py` everywhere | Grep test that `REQUIRED_BINS` is only defined once |

### P2 — Should Fix Before Any Manual Trading

| # | File | Issue | Why It Matters | Fix | Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 8 | `backend/src/paper_trading/simulator.py` | Uses `datetime.utcnow()` (deprecated Python 3.12+) | Will emit deprecation warnings; naive datetimes can cause comparison issues | Replace with `datetime.now(timezone.utc)` | Check timestamps are timezone-aware |
| 9 | `backend/src/storage/jsonl_store.py` | `update_record` rewrites entire file with no locking | Concurrent daily-run and settlement could corrupt paper_trades.jsonl | Add `fcntl.flock()` or migrate to SQLite | Document concurrency risk; add lock test |
| 10 | `backend/src/forecasting/rules_model_v2.py` line 169 | `best_single_number_f` defaults to 82 when forecast missing | Doesn't reflect the actual probability distribution | Compute from weighted mean of distribution | Test `best_single_number_f` reflects distribution peak |
| 11 | `backend/src/forecasting/rules_model.py` line 157 | v1 output date is `datetime.now().date().isoformat()` | Cannot backtest v1 for a specific past date | Accept `target_date` parameter (currently ignored) | Test v1 with explicit date parameter |
| 12 | `backend/src/backend/data/processed/history/` | Spurious nested path inside `src/` | Confusing; may contain stale data | Remove or redirect | N/A |

### P3 — Cleanup / Polish

| # | File | Issue | Fix |
| :--- | :--- | :--- | :--- |
| 13 | `backend/src/kalshi/market_discovery.py` line 2 | `from src.kalshi.client import KalshiPublicClient` — uses `src.` prefix | Change to `from kalshi.client import KalshiPublicClient` |
| 14 | `backend/src/calibration/metrics.py` line 3 | `from src.forecasting.bin_converter import temp_to_bin` — uses `src.` prefix | Change to `from forecasting.bin_converter import temp_to_bin` |
| 15 | `backend/src/calibration/comparison.py` line 4 | `from src.calibration.metrics import ...` — uses `src.` prefix | Change to `from calibration.metrics import ...` |
| 16 | `backend/src/features/live_features.py` line 112 | Daylight remaining assumes sunset at 20:00 ET | Use an ephemeris library or seasonal lookup |
| 17 | `backend/src/ingestion/kmia_obhistory_parser.py` line 98 | Re-imports `Tuple` from `typing` inside function body | Remove redundant import |
| 18 | `backend/src/shared/types.py` | `Union` imported but not used after `ClimiaReport.precipitation_in` changed to `Optional[float]` | Remove `Union` from imports |

---

## Recommended Next Tasks

Based on the audit findings, in priority order:

1. **Fix P0: Add `model_version` column to `DailyPrediction` DB model** — Required for non-dry-run operation.

2. **Fix P0: Remove Pydantic mock from `settlement_check.py`** — Settlement must not run with mocked validation.

3. **Fix P1: Remove test-runner dependency mocks** — Replace with a proper dependency check and clear error message.

4. **Fix P1: Clean up root-level legacy files** — Archive or delete `parsers/`, `models/`, `kalshi/`, `database/`, `tests/` at project root.

5. **Fix P1: Fix comparison report Markdown probabilities** — Store original probability dicts in the comparison result so the table renders correctly.

6. **Standardize imports** — Remove all `from src.X` prefixes; use bare module paths consistently with PYTHONPATH=backend/src.

7. **Consolidate `REQUIRED_BINS`** — Import from a single source (`shared/types.py`).

8. **Add v2 to the daily operational loop as default** — v2 is already the default in the CLI; verify it works with the DB path end-to-end (after P0 fix).

9. **Build a weekly calibration aggregation report** — `calculate_aggregate_stats` exists but isn't wired to any scheduled output.

10. **Migrate paper-trading JSONL to SQLite** — Reuse the existing SQLAlchemy infrastructure to get atomicity and concurrency safety.

---

## Files Changed During Review

No source files were modified during this review. The audit is observational only.

---

## Final Recommendation

| Readiness Level | Status | Notes |
| :--- | :--- | :--- |
| **Dry-run forecasting** | ✅ **Ready** | `--dry-run` mode works cleanly with both v1 and v2 |
| **Paper trading** | ⚠️ **Ready with P0 fixes** | Fix DB model_version column and remove settlement_check mock first |
| **Real trading** | ❌ **Not ready** | By design and policy. No trading code exists. No trading code should be added. |

The system's safety posture is strong. The recommendation layer correctly rejects uncertain, stale, low-liquidity, and negative-edge scenarios. The paper-trading simulator operates entirely on local JSONL with no network side effects. The Kalshi client is genuinely read-only with no authentication capability.

**The most advanced acceptable next step is improved paper-trading evaluation and calibration reporting.**

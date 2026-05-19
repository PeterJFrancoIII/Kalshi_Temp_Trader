# KMIA Forecast Workflow Task Sheet

**Date:** 2026-05-11  
**Local-first workflow:** create and review this file on the local Mac / Antigravity workspace before committing or pushing to GitHub.  
**Canonical research source:** `Deep_Research_Consolidated_1-11.md`  
**Mode:** research, dry-run, and paper evaluation only. No live order execution.

---

## Objective

Build a reliable KMIA maximum-temperature probability system for evaluating Kalshi temperature markets in paper mode. The system should use calibrated probability distributions, real station observations, dynamic contract mapping, fee/slippage checks, and hard risk gates before any future live-trading discussion.

**Architecture:**
- `backend/src/` is the exclusive logic folder. No trading logic in `.streamlit`.
- Tests run locally in `backend/tests/`.
- No live trading execution logic is written.
- All code assumes KMIA/Miami International Airport target.

## Timeline Progress & Current Phase

| Phase | Description | Owner | Status |
|---|---|---|---|
| Phase 1 | Database & Code Hygiene Lockdown | Agent 1 (Admin) | ✅ Complete |
| Phase 2 | TWC Probabilistic Forecast Ingestion | Agent 2 (Weather) | ✅ Complete |
| Phase 3 | TWC Daily Max Distribution Scaffold | Agent 3 (Forecast) | ✅ Complete |
| Phase 4 | NWS/KMIA Observation Correction | Agent 2 (Weather) | ✅ Complete |
| Phase 5 | KMIA Distribution Blender | Agent 3 (Forecast) | ✅ Complete |
| Phase 6 | Dynamic Kalshi Contract Mapping | Agent 5 (Kalshi) | ✅ Complete |
| Phase 7 | Kalshi Probability Generator | Agent 5 (Kalshi) | ✅ Complete |
| Phase 8 | Operational Status Evaluator | Agent 6 (Risk) | ✅ Complete |
| Phase 9 | Automated Settlement & Calibration | Agent 4 (Backtest) | ⏳ In Progress |
| Phase 10 | The Live "Dry-Run" Setup | Agent 7 (DevOps) | ⏳ Not Started |
| Phase 11 | Final Review & Lockdown | Agent 8 (Roll-up) | ⏳ Not Started |

---

## Local-First Document Workflow

### Rule

Create or edit docs in the local Mac repo first:

```bash
cd /path/to/Kalshi_Temp_Trader
mkdir -p docs
```

Place this file at:

```text
docs/NEXT_WORKFLOW_TASK_SHEET_2026-05-11.md
```

Then inspect locally:

```bash
git status
git diff -- docs/NEXT_WORKFLOW_TASK_SHEET_2026-05-11.md
```

Only after local review should the document be committed or pushed.

### Do not

- Do not create project docs directly in GitHub before the local workspace has the file.
- Do not rely on GitHub as the source of truth while active development is happening in Antigravity.
- Do not pull remote changes blindly if they may conflict with the local working tree.

---

## Source Doctrine

Use `Deep_Research_Consolidated_1-11.md` as the canonical research source. Its key thesis is that KMIA temperature forecasting must target the official airport high, not a generic Miami forecast. The research prioritizes official probabilistic guidance, high-resolution nowcasting, real-time KMIA observation correction, and calibrated distribution-to-contract probability mapping.

The Weather Company should become a high-priority source. Current public TWC / IBM documentation describes a Probabilistic Forecast API that can return discretized PDFs, probability integrations over specified ranges, percentile extractions, and BMA-enhanced hourly temperature distributions.

Preserve these external references:

- `https://developer.weather.com/docs/probabilistic-forecast`
- `https://developer.weather.com/docs/openapi/probabilistic-hourly-forecast-3-0`
- `https://www.ibm.com/docs/en/environmental-intel-suite?topic=apis-probabilistic-hourly-forecast`

---

## Correct Workflow

```text
TWC probabilistic forecast distribution
+ NWS/KMIA live observation correction
+ NBM/HRRR/NWS regime features
-> calibrated KMIA max-temperature distribution
-> Kalshi active contract discovery
-> dynamic contract-range probability integration
-> fee/slippage-adjusted edge
-> hard risk gates
-> paper decision
-> settlement verification
-> calibration update
```

Forbidden workflow:

```text
weather data -> fixed global bins -> decision
```

Kalshi determines the available tradable ranges for each event. The system must discover active Kalshi contracts first, then integrate the calibrated KMIA temperature distribution across those discovered ranges.

---

## Phase 1 - Stabilize Dry-Run Sandbox

Run locally in Antigravity terminal:

```bash
git status
bash scripts/run_tests.sh
bash scripts/update_nws_live_data.sh
bash scripts/update_kalshi_market_data.sh
bash scripts/run_kmia_daily_workflow.sh
bash scripts/run_web_console.sh
```

Acceptance criteria:

- Tests pass.
- NWS snapshot is generated.
- Kalshi market snapshot is generated.
- Daily workflow completes.
- Dashboard clearly shows paper/dry-run status.
- No live execution path is enabled.

---

## Phase 2 - Add TWC Probabilistic Forecast Ingestion

Create locally:

```text
backend/src/weather/twc_probabilistic_client.py
scripts/update_twc_probabilistic_data.sh
```

The client should support:

- Missing-credential-safe behavior.
- KMIA latitude/longitude targeting.
- Hourly probabilistic temperature forecast retrieval.
- Percentile extraction where available.
- Discretized PDF extraction where available.
- Probability integration over custom ranges where available.
- Raw response archival.
- Structured warnings for unavailable, unauthorized, or incomplete API responses.

Expected snapshot path:

```text
backend/data/processed/weather_twc/latest_twc_probabilistic_kmia_snapshot.json
backend/data/processed/weather_twc/twc_probabilistic_kmia_snapshot_<timestamp>.json
```

Acceptance criteria:

- The script runs without crashing if credentials are missing.
- Successful API responses are archived locally.
- Unit tests cover success, missing credentials, API error, and missing fields.

---

## Phase 3 - Convert TWC Hourly Probabilities Into Daily KMIA Max Distribution

Create locally:

```text
backend/src/forecasting/twc_daily_max_distribution.py
```

The output should be a canonical `TemperatureDistribution` with integer probabilities, optional half-degree probabilities, CDF, percentiles, source provenance, calibration version, and warnings.

Important caveat: TWC calibration applies to hourly temperature distributions, so the daily maximum distribution must be derived and then verified/calibrated against KMIA settlement history.

Acceptance criteria:

- Distribution sums to approximately 1.0.
- Distribution can be integrated into arbitrary Kalshi contract ranges.
- Distribution contains provenance and warnings.
- Tests cover monotonic CDF, probability normalization, and impossible/missing input behavior.

---

## Phase 4 - Add NWS/KMIA Observation Correction

Create locally:

```text
backend/src/forecasting/kmia_observation_bias_corrector.py
```

Use:

- Current KMIA METAR/ASOS.
- KMIA1M/high-frequency observation if available.
- Observed max so far.
- Morning ramp rate.
- Wind direction and speed.
- Cloud cover/ceiling.
- Sensor/freshness flags.

Correction rules:

- Observed max can truncate impossible lower-tail probability.
- Faster-than-expected heating shifts probability warmer.
- Early sea breeze shifts/caps probability cooler.
- Persistent offshore/westerly flow shifts probability warmer.
- Stale or flagged observations reduce confidence and can block paper recommendations.

Acceptance criteria:

- Bias correction is deterministic and auditable.
- Every adjustment produces a reason string.
- Stale observations reduce confidence rather than creating false precision.
- Unit tests cover observed-max truncation, warm ramp, early sea breeze, delayed sea breeze, and stale observation behavior.

---

## Phase 5 - Blend TWC With NBM/HRRR/NWS Features

Create locally:

```text
backend/src/forecasting/kmia_distribution_blender.py
```

Roles:

- TWC probabilistic API: high-weight primary prior when available.
- NBM station percentiles: official fallback and anchor.
- HRRR regime features: sea-breeze/cloud/wind modifiers.
- NWS/WFO Miami AFD: confidence/regime warning modifier.
- KMIA observations: same-day correction and truncation source.

Acceptance criteria:

- TWC available path works.
- TWC unavailable path falls back to NBM/HRRR workflow.
- Blend emits component weights and reasons.
- Final output is one canonical `TemperatureDistribution` object.

---

## Phase 6 - Dynamic Kalshi Contract Mapping

Remove active fixed-bin dependencies from paper logic.

Search locally:

```bash
grep -R "BIN_RANGES\|<=78\|79-80\|81-82\|83-84\|85-86\|>=87" backend/src backend/tests scripts docs | head -100
```

Continue hardening:

```text
backend/src/market_data/kalshi_contract_mapper.py
```

Create locally:

```text
backend/src/forecasting/contract_probability_mapper.py
```

Acceptance criteria:

- Active contracts determine ranges.
- Arbitrary ranges like `91-92`, `>=95`, and `<=89` work.
- Model probability is integrated over each active contract range.
- Static bins are fixture-only.

---

## Phase 7 - Fee/Slippage Edge and Risk Gates

Create locally:

```text
backend/src/trading/edge_engine.py
backend/src/risk/risk_engine.py
```

Edge formula:

```text
edge = calibrated_model_probability - fee_slippage_adjusted_breakeven_probability
```

Risk gates:

1. TWC/NWS data availability.
2. Weather freshness.
3. Forecast confidence.
4. Near-boundary settlement risk.
5. Liquidity/spread.
6. Fee-adjusted edge.
7. Daily loss limit.
8. Weekly drawdown limit.
9. Market concentration limit.
10. Manual kill switch.

Every signal must include a `RiskDecision` and no-trade reason when blocked.

---

## Phase 8 - Refactor Paper Signal Generator

Refactor locally:

```text
backend/src/paper_trading/signal_generator.py
```

New output fields:

```text
market_ticker
contract_range
model_probability
market_probability
breakeven_probability
raw_edge
executable_edge
weather_sources_used
forecast_distribution_source
risk_decision
no_trade_reason
warnings
```

Acceptance criteria:

- No active use of markdown forecast fixed bins.
- Dynamic contract probabilities drive paper decisions.
- TWC probability source is visible in output when used.
- NWS observation correction reason is visible in output when applied.

---

## Phase 9 - Backtesting and Calibration

Every workflow step must accept:

```text
target_date
forecast_as_of_time
market_snapshot_as_of_time
weather_observation_as_of_time
```

Track:

- Raw TWC probability vs. observed KMIA high.
- TWC after NWS/KMIA observation correction.
- TWC+NBM+HRRR blended distribution.
- Brier score by contract threshold.
- CRPS for full daily-max distribution.
- Expected Calibration Error.
- Paper PnL after fees/slippage.

Acceptance criteria:

- Backtests do not use `latest` files by accident.
- Backtests do not see future observations, later model runs, revised CLI values, or post-settlement data.
- Reliability reports separate raw TWC, corrected TWC, and blended model performance.

---

## Phase 10 - Multi-Agent Workflow

Use agents with structured outputs only:

1. TWC Data Agent.
2. NWS/KMIA Observation Agent.
3. Forecast Distribution Agent.
4. Kalshi Market Agent.
5. Edge Agent.
6. Risk Agent.
7. Backtest/Learning Agent.
8. Product Engineer Roll-Up Agent.

Every agent output must include:

```text
Inputs read
Files changed
Tests run
Assumptions
Risks found
Next task
Machine-readable JSON summary
```

Acceptance criteria:

- No agent produces unstructured-only notes.
- Shared context remains short, factual, and citation-friendly.
- Product Engineer agent owns integration sequencing.

---

## Promotion Gate

Next target:

```text
READY FOR TRUSTED PAPER TRADING
```

Requirements:

1. TWC probabilistic ingestion works or fails gracefully with fallback.
2. TWC hourly probabilities convert to a daily KMIA max distribution.
3. NWS/KMIA observations correct or constrain the distribution.
4. Dynamic Kalshi contract mapping is active.
5. No active paper path uses static fixed bins.
6. Weather freshness blocks stale-data recommendations.
7. Fee/slippage-adjusted edge is implemented.
8. RiskDecision blocks unsafe signals.
9. Dashboard explains no-trade reasons.
10. Backtest/replay has no lookahead.
11. Paper ledger records expected vs. actual outcomes.

Do not begin live execution work until paper evaluation is stable and well-calibrated.

---

## Immediate Local Action

On the Mac, save this file at:

```text
docs/NEXT_WORKFLOW_TASK_SHEET_2026-05-11.md
```

Then run:

```bash
git status
git diff -- docs/NEXT_WORKFLOW_TASK_SHEET_2026-05-11.md
```

Keep it local until the Antigravity workspace and GitHub remote are intentionally synchronized.

# KMIA Forecast Workflow Task Sheet

**Date:** 2026-05-11
**Canonical research source:** `Deep_Research_Consolidate_1-10.md`
**Mode:** research, dry-run, and paper evaluation only. No live order execution.

## Objective

Build a reliable KMIA maximum-temperature probability system for evaluating Kalshi temperature markets in paper mode. The system should use calibrated probability distributions, real station observations, dynamic contract mapping, fee/slippage checks, and hard risk gates before any future live-trading discussion.

## Source Doctrine

Use `Deep_Research_Consolidate_1-10.md` as the canonical research source. Its key thesis is that KMIA temperature forecasting must target the official airport high, not a generic Miami forecast. The research prioritizes official probabilistic guidance, high-resolution nowcasting, real-time KMIA observation correction, and calibrated distribution-to-contract probability mapping.

The Weather Company should become a high-priority source. Current public TWC documentation describes a Probabilistic Forecast API that can return discretized PDFs, probability integrations over specified ranges, percentile extractions, and BMA-enhanced hourly temperature distributions.

Preserve these external references:

- `https://developer.weather.com/docs/probabilistic-forecast`
- `https://developer.weather.com/docs/openapi/probabilistic-hourly-forecast-3-0`
- `https://www.ibm.com/docs/en/environmental-intel-suite?topic=apis-probabilistic-hourly-forecast`

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

## Phase 1 - Stabilize Dry-Run Sandbox

Run:

```bash
git pull
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

## Phase 2 - Add TWC Probabilistic Forecast Ingestion

Create:

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

## Phase 3 - Convert TWC Hourly Probabilities Into Daily KMIA Max Distribution

Create:

```text
backend/src/forecasting/twc_daily_max_distribution.py
```

The output should be a canonical `TemperatureDistribution` with integer probabilities, optional half-degree probabilities, CDF, percentiles, source provenance, calibration version, and warnings.

Important caveat: TWC calibration applies to hourly temperature distributions, so the daily maximum distribution must be derived and then verified/calibrated against KMIA settlement history.

## Phase 4 - Add NWS/KMIA Observation Correction

Create:

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

## Phase 5 - Blend TWC With NBM/HRRR/NWS Features

Create:

```text
backend/src/forecasting/kmia_distribution_blender.py
```

Roles:

- TWC probabilistic API: high-weight primary prior when available.
- NBM station percentiles: official fallback and anchor.
- HRRR regime features: sea-breeze/cloud/wind modifiers.
- NWS/WFO Miami AFD: confidence/regime warning modifier.
- KMIA observations: same-day correction and truncation source.

## Phase 6 - Dynamic Kalshi Contract Mapping

Remove active fixed-bin dependencies from paper logic.

Search:

```bash
grep -R "BIN_RANGES\|<=78\|79-80\|81-82\|83-84\|85-86\|>=87" backend/src backend/tests scripts docs | head -100
```

Continue hardening:

```text
backend/src/market_data/kalshi_contract_mapper.py
```

Create:

```text
backend/src/forecasting/contract_probability_mapper.py
```

Acceptance criteria:

- Active contracts determine ranges.
- Arbitrary ranges like `91-92`, `>=95`, and `<=89` work.
- Model probability is integrated over each active contract range.
- Static bins are fixture-only.

## Phase 7 - Fee/Slippage Edge and Risk Gates

Create:

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

## Phase 8 - Refactor Paper Signal Generator

Refactor:

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

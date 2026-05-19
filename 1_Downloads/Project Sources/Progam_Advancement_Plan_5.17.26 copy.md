
## Executive verdict

The GitHub program is a**** **safe research / dry-run MVP** , not yet a trusted paper-trading system. That is the right state. It should stay******Python-first, read-only, and paper-only** while the next work focuses on boring correctness: timestamps, observation freshness, dynamic contract ranges, fee-adjusted edge, fail-closed risk decisions, and settlement-safe paper evaluation.

The simplest advancement path is******not** to merge the large TWC branch wholesale. Instead, build one narrow vertical slice on****`main`:

```text
NWS/KMIA snapshot with freshness
-> simple calibrated-ish integer temperature distribution
-> active Kalshi contract range mapping
-> fee/slippage edge
-> RiskDecision / no-trade reason
-> paper signal JSON
-> dashboard display
```

This aligns with the uploaded project doctrine: target the official KMIA airport high, produce a calibrated distribution first, integrate it over active Kalshi contracts second, and keep all live trading blocked.

## Current GitHub state

The README describes the app as an MVP for predicting the official KMIA daily maximum temperature and explicitly says it does******not** contain real-money trading or execution logic. Code governance reinforces the same scope: Python-first, no real-money orders, Kalshi read-only until approval, no recommendations from stale/missing/malformed data, and no React/frontend expansion during MVP.

The repo’s current forecast core is still a**** **fixed-bin rules model** .****`shared/types.py` defines required bins as** **`<=78`,** **`79-80`,** **`81-82`,** **`83-84`,** **`85-86`, and** **`>=87`.** **`bin_converter.py` hardcodes those same ranges.****`rules_model_v2.py` builds a heuristic distribution by blending climatology, a forecast-centered distribution, and simple weather suppression rules, then zeroes impossible lower bins after the observed high. This is useful MVP scaffolding, but it is not the research-guided target architecture yet.

The NWS live-data layer is partially ahead of the old model.****`nws_live_client.py` builds a richer KMIA snapshot with** **`fetched_at_utc`, latest observation time, recent observation rows, current temperature, observed max so far, forecast high, endpoint status, warnings, and a****`stale_data` flag. However, GitHub still has two open P0 blockers: the NWS live observation table/schema is not trusted enough for operator confidence, and stale-weather blocking is not complete.

The Kalshi side is read-only and reasonably scoped.****`kalshi_public_client.py` uses unauthenticated GET requests, discovers markets, and writes snapshots with** **`no_real_trading`,** **`no_order_execution`, and** **`no_authentication` safety metadata.** **`kalshi_contract_mapper.py` extracts above/below/between thresholds from structured fields, titles, subtitles, and ticker fallback. But** **`signal_generator.py` still parses forecast probabilities from markdown, uses fixed** **`BIN_RANGES`, skips contracts when a boundary cuts through a fixed bin, calculates edge as raw****`model_probability - market_probability`, and has no fee/slippage or risk-gate decision.

The backtest/evaluation path is not point-in-time safe yet.****`daily_status.py`,** **`prediction_quality.py`, and** **`web_console.py` all use latest-file selection by filesystem modification time in places, which conflicts with the uploaded doctrine that backtests must use embedded timestamps and explicit** **`as_of_time` fields rather than****`latest` artifacts or filesystem mtimes. GitHub issue #10 correctly tracks this as a P1 lookahead-safety blocker.

There is a large open PR for TWC and broader architecture work. PR #1 is open, unmerged, non-mergeable, and very large: 83 commits, 144 changed files, 18,744 additions, and 1,097 deletions. It claims to add Weather Company ingestion and console comparison, but it is far too broad for the “keep it simple” direction. Smaller TWC-vs-NWS dashboard PRs #2 and #3 are open and mergeable, but they are UI-oriented and should not jump ahead of the P0 NWS/freshness blockers.

The CI workflow is present but focused: it compiles a few critical modules and runs selected pytest files if present. It does******not** appear to run the full custom** **`bash scripts/run_tests.sh` suite in CI. The local test script itself delegates to** **`backend/tests/run_tests.py`, which has a broad hand-rolled test list and exits only after printing****`ALL TESTS PASSED`. I inspected GitHub statically; I did not execute the repo locally in this pass.

## Main gap against the uploaded research doctrine

The uploaded roadmap says the correct workflow is:

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
```

The current****`main` implementation is closer to:

```text
NWS-ish / dry-run inputs
-> heuristic fixed-bin forecast
-> markdown report
-> fixed-bin approximation against active contracts
-> raw edge
-> paper signal
```

That is a good MVP foundation, but it is not yet the program described in the Project Source files. The most important mismatch is that production paper logic still depends on fixed global bins, while the uploaded doctrine says active Kalshi contracts should determine the ranges and fixed bins should become legacy/display/test-only. GitHub issue #6 currently proposes migrating to another fixed target-bin set, but the research-guided direction should supersede that: centralize**** **contract ranges** , not another production fixed-bin regime.

## Advancement plan: simple, staged, and research-aligned

### Stage 0 — Clean the scope before more coding

Do not merge PR #1 wholesale. Treat it as a reference branch only. Extract at most a few ideas or tests after****`main` is stable. A 144-file, non-mergeable PR is the opposite of the requested simplicity.

Also update the GitHub task sheet/docs to match the uploaded source-of-truth: the uploaded orchestrator says****`Deep_Research_Consolidated_1-11.md` is the canonical corpus, while the GitHub task-sheet commit still references the older****`Deep_Research_Consolidate_1-10.md` name.

### Stage 1 — Close the P0 weather trust blockers first

Implement one canonical NWS/KMIA snapshot contract and make every consumer use it:

```text
backend/data/processed/weather_nws/latest_nws_kmia_snapshot.json
```

Minimum fields:

```text
station
fetched_at_utc
latest_observation_time
current_temp_f
observed_max_so_far_f
forecast_high_f
recent_observations_table
stale_data
endpoint_status
warnings
safety.no_real_trading
```

`nws_live_client.py` is already close. The simple work is to make****`daily_status.py`,** **`web_console.py`, and forecast input loading consume this one snapshot instead of mixing older****`weather_ingestion` status files, markdown parsing, and loose latest-file discovery. This directly closes issue #4 and issue #5.

Acceptance check:

```bash
bash scripts/update_nws_live_data.sh
bash scripts/run_tests.sh
```

The dashboard must show either fresh KMIA observations or a clear no-recommendation state. No stale-data path should produce a “buy/watch” recommendation.

### Stage 2 — Replace production fixed-bin logic with a minimal integer distribution

Do not jump straight to TWC, HRRR, NBM, NGBoost, or complex blending. First introduce a tiny canonical object:

```python
TemperatureDistribution:
    station: "KMIA"
    target_date: date
    forecast_as_of_time: datetime
    integer_distribution: dict[int, float]
    source: str
    warnings: list[str]
    confidence: "low|medium|high"
```

For now, generate it from the existing rules model by spreading probability across integer Fahrenheit values around the forecast high and truncating all integers below observed max so far. Keep the current fixed bins only as display/report compatibility.

This is the smallest step that unlocks dynamic contract mapping without rewriting the whole model.

### Stage 3 — Add dynamic contract probability mapping

Create the missing production mapper:

```text
backend/src/forecasting/contract_probability_mapper.py
```

It should accept:

```text
TemperatureDistribution
Kalshi contract mapping from kalshi_contract_mapper.py
```

And return:

```text
market_ticker
contract_range
lower_inclusive
upper_inclusive
model_probability
warnings
tradable
```

This should integrate integer probability mass directly over the active contract range. It should support****`<=89`,** **`90 or below`,** **`91-92`,** **`93 to 94`,** **`>=95`,** **`95 or above`,** **`>95`, and half-degree boundaries. Unknown or ambiguous contract text should return****`tradable=false`, never a silent probability.

This is the key simplification: one mapper, one distribution, no production fixed-bin translation.

### Stage 4 — Add fee/slippage edge before any “paper buy” language

Implement a small****`edge_engine.py`:

```text
backend/src/trading/edge_engine.py
```

Keep it intentionally boring:

```text
executable_price = yes_ask for a YES paper-buy candidate
breakeven_probability = executable_price + estimated_fee + estimated_slippage
raw_edge = model_probability - market_probability
executable_edge = model_probability - breakeven_probability
```

GitHub issue #11 already captures the need to distinguish bid, ask, last, midpoint, executable price, fees, and slippage. The system should not emit****`PAPER BUY CANDIDATE` from raw edge anymore.

### Stage 5 — Add a fail-closed****`RiskDecision` skeleton

Create the simplest possible risk engine:

```text
backend/src/risk/risk_engine.py
```

Do not implement Kelly sizing, portfolio optimization, or live-trade controls yet. Start with deterministic gates:

```text
manual_kill_switch
weather_snapshot_present
weather_not_stale
forecast_distribution_valid
contract_range_mapped
market_price_present
spread_not_excessive
executable_edge_above_threshold
near_boundary_buffer_ok
paper_only_mode_confirmed
```

Output:

```text
allow: bool
decision: "ALLOW_PAPER" | "BLOCK"
no_trade_reason: str
gate_statuses: dict
warnings: list[str]
```

Issue #12 asks for RiskDecision/RiskGate architecture, and the uploaded orchestrator says risk gates must fail closed. Keep this module small and make every missing field block by default.

### Stage 6 — Refactor paper signals into one JSON artifact

Refactor****`backend/src/paper_trading/signal_generator.py` so it no longer parses markdown forecast reports as its primary source and no longer uses****`BIN_RANGES` for production mapping. Its output should match the uploaded roadmap:

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
safety.no_real_trading=true
```

The dashboard issue #13 should then be satisfied by reading this signal artifact and displaying no-trade reasons, not by inventing dashboard-only logic.

### Stage 7 — Fix paper ledger and settlement range semantics

Current settlement still scores against****`forecast_bin` and fixed bins. Move paper ledger entries to:

```text
contract_range
forecast_bin_label optional/display only
actual_official_high_f
settlement_source
settlement_as_of_time
expected_probability
entry_price
fees_slippage_assumption
risk_decision
result
simulated_pnl
```

The settlement function should evaluate whether the official high falls inside the stored contract range. It should not rely on****`condition_type` alone and should not require fixed forecast bins to determine wins/losses.

### Stage 8 — Make backtesting point-in-time safe before calibration claims

Only after the signal path is deterministic should you build replay. The minimum replay interface is:

```text
target_date
forecast_as_of_time
market_snapshot_as_of_time
weather_observation_as_of_time
settlement_as_of_time
```

Add a manifest for every replay day:

```text
artifact_type
resolved_path
embedded_timestamp
as_of_time
included_or_excluded
reason
```

Do not use****`latest_*` or filesystem mtime in replay. Issue #10 already frames the danger correctly: using later observations, corrected CLI, later forecasts, or later market snapshots invalidates any quality claim.

### Stage 9 — Add TWC probabilistic ingestion only after the baseline is safe

TWC should remain high priority, but not first. The research says TWC probabilistic output can become a valuable prior, but the program’s current blockers are more basic: NWS freshness, dynamic mapping, fee-adjusted edge, risk decisions, and lookahead safety.

When ready, create a small new PR with only:

```text
backend/src/weather/twc_probabilistic_client.py
scripts/update_twc_probabilistic_data.sh
backend/tests/test_twc_probabilistic_client.py
```

Missing credentials should produce a valid warning snapshot, not a crash. Do not merge broad dashboard, skills, agent, risk, backtest, and TWC changes in one branch.

## Immediate next PR I would build

**PR title:** `Fix NWS freshness contract and fail-closed paper status`

Files touched:

```text
backend/src/weather/nws_live_client.py
backend/src/status/daily_status.py
backend/src/web_console.py
backend/src/shared/types.py
backend/tests/test_nws_live_client.py
backend/tests/test_daily_status.py
backend/tests/test_web_console_logic.py
docs/NWS_LIVE_DATA.md
```

Definition of done:

```text
1. latest_nws_kmia_snapshot.json has populated observation rows or explicit warnings.
2. stale/missing NWS data produces no-recommendation/no-trade status.
3. dashboard shows fresh/stale/error state accurately.
4. no production code uses stale weather as fresh.
5. bash scripts/run_tests.sh passes locally.
6. no live trading code is added.
```

This keeps the program simple and advances the highest-confidence dependency first.

## Final go/no-go

`LOCAL_CONTINUATION_GO` for weather freshness/schema hardening, dynamic range mapping, edge engine, and fail-closed risk skeleton.

`PAPER_EVALUATION_NO_GO` for trusted paper trading until issues #4, #5, #10, #11, #12, and #13 are resolved in the mainline path.

`REAL_TRADING_NO_GO` remains unchanged.

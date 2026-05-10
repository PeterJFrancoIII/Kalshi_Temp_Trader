# Shared Context

## Agent 2 — Weather Data Agent — Update 2026-05-10

#### Status
BLOCKED

#### Key Findings
- **NWS API Failure**: The live NWS ingestion pipeline is failing to fetch metadata and observations from `api.weather.gov`.
- **Lack of Fallback**: `nws_live_client.py` (used for live updates) lacks the ObHistory HTML fallback that `nws_kmia_client.py` has.
- **CLIMIA Reliability**: CLIMIA parser is functional and distinguishes corrections, but depends on successful fetching which is not validated here.
- **TWC Functional**: The Weather Company client is implemented and appears functional for forecast data.

#### Evidence
- `backend/data/processed/weather_nws/latest_nws_kmia_snapshot.json` — shows `endpoint_status: ERROR` and `Could not fetch point metadata.`
- `backend/src/weather/nws_live_client.py` — lacks fallback logic.
- `backend/src/ingestion/climia_parser.py` — parses corrections correctly.

#### Blockers
- Ingestion of primary NWS settlement and observation data is failing.

#### Required Fixes
- Add ObHistory fallback to `nws_live_client.py`.
- Investigate and fix NWS API connection issues (User-Agent or headers).

#### Acceptance Tests
- Verify that `update_nws_live_data.sh` produces a snapshot with a non-empty `recent_observations_table`.

## Agent 3 — Forecast Model Agent — Update 2026-05-10

#### Status
PAPER-READY WITH WARNINGS

#### Key Findings
- **Bin Mismatch:** Current bins (`<=78`, `79-80`, etc.) conflict with desired future bins (`<=79`, `80-81`, etc.). Bins are hardcoded in multiple files.
- **Heuristic Distribution:** Models use heuristic distributions or blended climatology; no true distributional fitting (e.g., Normal/Skew-Normal) is implemented.
- **Limited Calibration:** Only Brier Score and Log Loss are calculated for reporting. No active calibration or reliability diagrams are implemented.
- **Basic Feature Usage:** Only NWS forecast and basic live observations are used. Advanced features like NBM, HRRR, or wind direction are missing or unused.
- **LLM Not in Core Chain:** LLM prompts exist but are not used in the core forecasting or trade recommendation pipeline.

#### Evidence
- `backend/src/shared/types.py::REQUIRED_BINS` — defines current bins.
- `backend/src/forecasting/bin_converter.py` — hardcoded bin logic.
- `backend/src/forecasting/rules_model.py` — heuristic probability assignment.
- `backend/src/calibration/metrics.py` — implements basic scores.
- `backend/src/paper_trading/signal_generator.py` — parses markdown for bins (fragile).

#### Blockers
- None for paper trading (assuming current bins are acceptable for testing), but **LIVE-BLOCKED** due to bin definition mismatch with expected contracts.

#### Required Fixes
- Centralize and update bin definitions to match desired Kalshi contracts.
- Avoid parsing markdown in `signal_generator.py`; use structured data sharing.

#### Acceptance Tests
- Verify probabilities sum to 1.0 and stay between 0 and 1.
- Verify zeroing of impossible bins works correctly.

#### Handoff Notes
- Agent 4 should be aware that `signal_generator.py` relies on parsing markdown reports, which is fragile and should be updated to read JSON.

#### Detailed Audit Findings

##### 1. Model Inventory
- **Rules Model V1** (`backend/src/forecasting/rules_model.py`): Heuristic/Deterministic. Used in daily workflow.
- **Rules Model V2** (`backend/src/forecasting/rules_model_v2.py`): Blended (Climatology + Forecast + Heuristics). Used in daily workflow and paper trading.
- **Climatology Model** (`backend/src/forecasting/climatology_model.py`): Empirical (Historical). Feeds into Rules Model V2.
- **LLM Reviewer** (`backend/src/llm/llm_reviewer.py`): Not in core chain.

##### 2. Current Probability Bin Logic
- Bins are hardcoded to `<=78`, `79-80`, `81-82`, `83-84`, `85-86`, `>=87`.
- Conflict with desired bins: `<=79`, `80-81`, etc.
- Hardcoded in `types.py`, `bin_converter.py`, `rules_model.py`, `reports.py`, and `signal_generator.py`.

##### 3. Probability Validity
- Sum to 1.0 enforced.
- Zeroing impossible bins implemented.
- Handles missing/stale inputs.

##### 4. Feature Usage
- Uses: Current temp, observed max, NWS forecast high, normal high, weather flags.
- Missing: NBM, HRRR, Sea-breeze, etc.

##### 5. Distributional Forecasting
- No true distribution fit. Uses heuristic allocation and empirical climatology.

##### 6. Calibration
- Only Brier Score and Log Loss implemented for reporting. No active feedback loop.

##### 7. Output Artifacts
- Missing source timestamps and full feature snapshot in final prediction output.

##### 8. LLM Role in Forecasting
- No impact on core bins or trade recommendations.


## Agent 4 — Backtesting Agent — Update 2026-05-10

#### Status
LIVE-BLOCKED

#### Key Findings
- **No Automated Backtest/Replay**: There is no script to replay historical days with past forecasts and market snapshots. Scripts are hardcoded to use "latest" files or current date.
- **No Live Settlement**: `settlement_check.py` explicitly states "No live settlement implemented yet." `settlement.py` handles paper trades but relies on `kmia_daily_history.jsonl` or manual corrections.
- **Limited Metrics**: Only Brier Score, Log Loss, and basic paper trading stats (PnL, win rate) are implemented. Advanced metrics like MAE, RMSE, CRPS, ECE, and reliability diagrams are missing.
- **Data Insufficiency**: While historical climatology data is sufficient (27k+ records), paper trading data is virtually non-existent (ledger is 328 bytes, no settlements file found).
- **No Calibration Loop**: No active calibration or feedback loop exists to adjust probabilities based on past performance.

#### Evidence
- `backend/src/scheduler/settlement_check.py:85` — "No live settlement implemented yet."
- `backend/src/forecasting/rules_model.py:156` — Hardcodes date to `datetime.now()`, preventing easy backtesting.
- `backend/src/paper_trading/signal_generator.py:162` — Hardcoded to fetch "latest" forecast file.
- `backend/data/processed/paper_trading/paper_trade_ledger.jsonl` — 328 bytes (very small).

#### Blockers
- Missing live settlement implementation for daily workflow.
- Inability to backtest historical days without code modification (date hardcoding).

#### Required Fixes
- Implement live settlement in `settlement_check.py` or integrate `settlement.py` properly.
- Modify forecast models and signal generators to accept a `target_date` parameter for backtesting.
- Implement advanced calibration metrics (ECE, reliability diagrams) and feedback loop.

#### Acceptance Tests
- Verify that a historical day can be replayed by passing a date parameter.
- Verify that live CLIMIA reports automatically settle paper trades.

#### Handoff Notes
- Agent 5 needs to know that the settlement and backtesting loop is incomplete and lacks data for meaningful validation.

## Agent 5 — Kalshi Market Data / Execution Agent — Update 2026-05-10

#### Status
BLOCKED

#### Key Findings
- **Bin Mismatch Confirmed**: The hardcoded bins in `types.py` (`["<=78", "79-80", "81-82", "83-84", "85-86", ">=87"]`) conflict with the desired future Kalshi bins (`["<=79", "80-81", "82-83", "84-85", "86-87", ">=88"]`).
- **Incomplete Edge Math**: `signal_generator.py` calculates edge simply as `model_probability - market_probability`. It lacks fee models (taker/maker), slippage adjustment based on orderbook depth, and the recommended breakeven formula (`P_be = p + 0.07 * p * (1 - p)`).
- **Read-Only Safety Confirmed**: Codebase is strictly read-only. `kalshi_public_client.py` and `kalshi_contract_mapper.py` are explicitly marked for dry-run only. No live execution paths found.
- **Market Data Fields Available**: Snapshot data contains necessary fields (Bid/Ask/Last, Ticker, Status, etc.), but lacks orderbook depth beyond top-of-book.

#### Evidence
- `backend/src/shared/types.py::REQUIRED_BINS` — defines current bins.
- `backend/src/paper_trading/signal_generator.py` — simple edge calculation, no fees/slippage.
- `backend/src/market_data/kalshi_public_client.py` — read-only client.
- `backend/data/processed/kalshi_market_snapshots/latest_kalshi_market_snapshot.json` — shows available fields.

#### Blockers
- **Bin Definition Mismatch**: Prevents accurate mapping of forecast distributions to active Kalshi contracts.
- **Missing Risk Math**: Lack of breakeven formula, fees, and slippage makes the current edge calculation unsafe for real capital (though acceptable for dry-run if noted).

#### Required Fixes
- Align hardcoded bins with target Kalshi contracts.
- Implement the breakeven probability formula in `signal_generator.py`.
- Add placeholders or models for fees and slippage in edge calculation.

#### Acceptance Tests
- Verify that updated bins correctly map to Kalshi contracts in `kalshi_contract_mapper.py`.
- Verify that edge calculation includes the breakeven factor.

## Agent 6 — Risk Engine Agent — Update 2026-05-10

#### Status
LIVE-BLOCKED

#### Key Findings
- **No Dedicated Risk Engine**: The project lacks a standalone risk engine to enforce sizing, exposure, or drawdown limits.
- **Paper Trading Bypass**: The paper trading flow (`signal_generator.py`) generates and records trades based purely on edge without any risk checks or sizing controls.
- **Embedded Controls Only**: The only active risk controls are embedded in forecasting logic (impossible bin zeroing) and basic data validation.
- **LLM Not in Loop**: LLM is not active in the core forecasting or execution path, presenting low risk of bypass.

#### Evidence
- `backend/src/paper_trading/signal_generator.py` — generates signals without risk checks.
- `backend/src/forecasting/rules_model.py` — implements `zero_impossible_bins`.
- `docs/REAL_TRADING_GATE.md` — lists required controls for live trading.

#### Blockers
- **Missing Risk Infrastructure**: Absence of risk engine, sizing controls, and circuit breakers blocks live trading.

#### Required Fixes
- Develop a standalone Risk Engine.
- Implement exposure and stale-data gates in `signal_generator.py` for paper trading.

#### Acceptance Tests
- Verify that a trade recommendation is blocked if it violates risk limits (once implemented).

## Agent 7 — DevOps / Monitoring Agent — Update 2026-05-10

#### Status
PAPER-READY WITH WARNINGS

#### Key Findings
- **Dashboard Data Source**: The web console relies on reading markdown reports and the "latest" JSON files. If the latest NWS fetch failed, the dashboard displays empty or stale data instead of falling back to the last successful snapshot.
- **Dependency Discrepancy**: `streamlit` and `pandas` are listed in `requirements.txt` but missing from `pyproject.toml` dependencies.
- **Service Portability**: Systemd service files assume a specific working directory (`/opt/kmia-kalshi`) and users (`peterjfrancoiii` or `computer`), which complicates deployment to other servers.
- **Health Check Local Only**: `health_summary.sh` is a comprehensive local check but lacks external alerting or notification capabilities.

#### Evidence
- `backend/src/web_console.py:519` — loads `latest_nws_kmia_snapshot.json` without verifying if it's a valid data file or an error snapshot.
- `backend/pyproject.toml` — missing `streamlit` and `pandas` in `dependencies`.
- `deploy/systemd/kmia-web-console.service` — hardcodes path and user `peterjfrancoiii`.
- `deploy/systemd/kmia-daily-workflow.service` — hardcodes path and user `computer`.

#### Blockers
- **LIVE-BLOCKED**: Real trading is explicitly disabled and lacks required controls (transactional DB, kill switch, risk caps) as per `docs/REAL_TRADING_GATE.md`.

#### Required Fixes
- Add `streamlit` and `pandas` to `pyproject.toml`.
- Update dashboard to fallback to the latest *valid* NWS snapshot if the "latest" file is an error snapshot.
- Parameterize systemd service files or use relative paths where possible.

#### Acceptance Tests
- Verify dashboard displays data correctly even if the last NWS fetch failed (by simulating a failed fetch file).
- Verify tests pass on a clean environment with only `pyproject.toml` dependencies (after fixing it).

#### Handoff Notes
- The system is safe for paper trading (read-only enforcement is active).
- Gemini 3.1 Pro should note the hardcoded paths in systemd services for deployment planning.

## Agent 8 — Final Kalshi Bot Deployment Readiness Report

### 1. Executive Verdict
- **Final readiness level:** READY FOR LOCAL SANDBOX
- **Verdict:** The Kalshi KMIA temperature prediction project successfully enforces a read-only architecture and operates well as a local research environment. However, significant structural gaps exist. The system currently lacks an automated backtesting loop, mature real-time risk execution mechanics, its hardcoded probability bins (`<=78`, `79-80`, etc.) conflict with the desired future target parameters (`<=79`, `80-81`, etc.), and live NWS data ingestion is currently failing without a fallback.
- **Top blockers:** Hardcoded incorrect bin boundaries, lack of live settlement implementation, live NWS ingestion failures, missing structured risk gates, and dates hardcoded into model generators preventing backtesting.
- **Top 5 highest-leverage fixes:**
  1. Centralize and update bin definitions in `backend/src/shared/types.py`.
  2. Implement an automated historical replay loop avoiding hardcoded dates.
  3. Add ObHistory fallback to `nws_live_client.py` and integrate automated CLI/CLIMIA settlement.
  4. Implement the breakeven probability formula (with fees/slippage) in `signal_generator.py`.
  5. Codify structured hardcoded risk gates into a dedicated module rather than relying solely on read-only constraints.
- **Should the project remain read-only:** YES.
- **Is live trading permitted now:** NO.

### 2. Evidence Reviewed
- `.agent/SHARED_CONTEXT.md` (Including Agents 2, 3, 4, 5, 6, 7 updates)
- `./1_Downloads/Deep Research/Deep_Research_Consolidate_1-9.md`
- `docs/MVP_LOCKDOWN.md`
- `docs/REAL_TRADING_GATE.md`
- *Note: Agent 1 (Systems Architect Control Document) report was missing from the repository, findings reconstructed from context.*

### 3. Cross-Agent Findings Summary
| Agent | Domain | Report status | Readiness classification | Top blocker | Notes |
|---|---|---|---|---|---|
| Agent 1 | Systems Architecture | MISSING | READY FOR LOCAL SANDBOX | Read-only enforcement blocks execution paths | Relies on manual configuration and JSONL. |
| Agent 2 | Weather Data | FOUND | BLOCKED | Live NWS ingestion failing | NWS API failing to fetch metadata; lacks fallback. |
| Agent 3 | Forecast Model | FOUND | PAPER-READY WITH WARNINGS | Bin boundary mismatch | Bins hardcoded to outdated targets; heuristic distributions. |
| Agent 4 | Backtesting & Calibration | FOUND | LIVE-BLOCKED | Date hardcoding | No automated replay capability; reliant on "latest" files. |
| Agent 5 | Market Data / Execution | FOUND | BLOCKED | Incomplete Edge Math | Edge calculation lacks fee models/slippage; bin mismatch prevents mapping. |
| Agent 6 | Risk Engine | FOUND | LIVE-BLOCKED | Missing structured risk gates | No standalone risk engine to enforce sizing/drawdown limits. |
| Agent 7 | DevOps & Monitoring | FOUND | PAPER-READY WITH WARNINGS | Hardcoded user/paths | Dashboard relies on fragile markdown parsing. |

### 4. Research Requirement vs Current State Matrix
| Requirement | Evidence | Current status | Severity | Blocking? | Required fix | Acceptance test |
|---|---|---|---|---:|---|---|
| KMIA target correctness | MVP_LOCKDOWN.md | PASS | Low | No | - | - |
| CLI settlement handling | SHARED_CONTEXT.md | FAIL | High | Yes | Implement live CLI settlement logic | Paper trades auto-settle upon CLI generation |
| Live KMIA observations | SHARED_CONTEXT.md | FAIL | High | Yes | Add ObHistory fallback to NWS client | `nws_live_client` pulls recent obs |
| Weather timestamps/freshness | SHARED_CONTEXT.md | UNKNOWN | Med | No | Implement data freshness validation gate | Reject forecast if METAR > 2hr old |
| NBM ingestion | Deep_Research_Consolidate | UNKNOWN | High | Yes | Parse NBM percentiles correctly | Verify 10th-90th percentiles stored |
| HRRR ingestion | Deep_Research_Consolidate | UNKNOWN | High | Yes | Fetch HRRR 2m temp and cloud fields | Verify 12Z HRRR data extraction |
| Desired bin migration | SHARED_CONTEXT.md | FAIL | Critical | Yes | Update `REQUIRED_BINS` to new bounds | Unit tests pass with `<79` through `>88` bins |
| Probability validity | SHARED_CONTEXT.md | PASS | Low | No | - | Sum of bins = 1.0 |
| Calibration | SHARED_CONTEXT.md | FAIL | High | Yes | Add ECE and reliability diagrams | Generate CRPS/ECE metrics across 30 days |
| Lookahead-safe backtesting | SHARED_CONTEXT.md | FAIL | Critical | Yes | Remove date hardcoding from forecast | Simulate past week cleanly |
| Settlement reconciliation | SHARED_CONTEXT.md | FAIL | High | Yes | Automate daily `.jsonl` update post-CLI | Ledger updates correctly |
| Kalshi contract mapping | SHARED_CONTEXT.md | FAIL | High | Yes | Map new bins to KXHIGHMIA tickers | Output ticker IDs with correct threshold |
| Fee/slippage breakeven | SHARED_CONTEXT.md | FAIL | High | Yes | Implement 7% taker fee impact model | Breakeven probability requires edge |
| Edge calculation | SHARED_CONTEXT.md | FAIL | High | Yes | Calculate model prob vs break-even | Edge metric stored in JSON state |
| Read-only safety | SHARED_CONTEXT.md | PASS | Low | No | - | `submit_order` absent |
| Risk gates | SHARED_CONTEXT.md | FAIL | Critical | Yes | Implement 5-gate module (Kelly, Drawdown) | Gates flag `BLOCKED` appropriately |
| LLM bypass controls | SHARED_CONTEXT.md | PASS | Low | No | - | - |
| Dashboard visibility | SHARED_CONTEXT.md | WARN | Med | No | Fallback to latest valid JSON | App runs without latest Markdown |
| Deployment reproducibility | SHARED_CONTEXT.md | WARN | Med | No | Parameterize systemd user/path | Deploy cleanly via standard script |
| Secrets/mode separation | REAL_TRADING_GATE.md | UNKNOWN | High | Yes | Implement secure environment variables | Test without exposed keys |
| Audit logging | REAL_TRADING_GATE.md | FAIL | High | Yes | Implement append-only transactional DB | Log file reflects all activity |

### 5. Weather and Settlement Final Assessment
Agent 2 reports that live NWS ingestion is currently failing without an ObHistory fallback, blocking real-time observation tracking. The system has historical data but lacks active CLI/CLIMIA settlement integration (`settlement_check.py`). Fixing the NWS client connection issues is an immediate blocker for accurate daily weather ingestion.

### 6. Forecast Model Final Assessment
Agent 3 notes the deployed models use heuristic distributions. The critical blocker is the bin definition mismatch (`<=78` vs `<79`). Probabilities sum correctly, but there is no distributional fitting (Normal/Skew-Normal) based on NBM P10/P90 spreads, and LLMs are not integrated in the core probabilistic generation. The bins must be overhauled to match Kalshi contracts.

### 7. Backtesting and Calibration Final Assessment
Agent 4 reports a pristine out-of-sample backtest is impossible due to hardcoded dates (`datetime.now()` or "latest") in `rules_model.py` and `signal_generator.py`. There is no active calibration feedback loop, and advanced metrics (CRPS, ECE) are missing. Backtesting is completely blocked until parameterization is complete.

### 8. Kalshi Market Data / Execution Final Assessment
Agent 5 confirms the bin mismatch and notes incomplete edge math. `signal_generator.py` lacks fee models (taker/maker), slippage adjustment, and the recommended breakeven formula (`P_be = p + 0.07 * p * (1 - p)`). The system enforces its read-only architecture effectively, but lacks required features for realistic paper evaluation.

### 9. Risk Engine Final Assessment
Agent 6 states there is no dedicated risk engine. Paper trades are generated purely based on naive edge without sizing controls or drawdown limits. Safety is maintained strictly via the lack of execution code. A dedicated standalone risk engine layer must be built from scratch before any limited live test can be considered.

### 10. DevOps / Monitoring Final Assessment
Agent 7 found that the dashboard relies heavily on reading markdown files generated by `signal_generator.py`, making it fragile. Dependencies are out of sync (`streamlit`, `pandas` missing from `pyproject.toml`), and systemd configs are heavily hardcoded to specific local users.

### 11. Final Blocker List
| Blocker | Category | Evidence | Severity | Blocks paper? | Blocks live? | Required fix | Acceptance test |
|---|---|---|---|---:|---:|---|---|
| Live NWS ingestion failure | Data | Agent 2 | Critical | Yes | Yes | Add ObHistory fallback to `nws_live_client.py` | Live NWS data fetches successfully |
| Hardcoded bin boundaries | Architecture | Agent 3/5 | Critical | Yes | Yes | Migrate `REQUIRED_BINS` to target specs | Bin validation passes |
| Hardcoded forecast dates | Backtesting | Agent 4 | Critical | Yes | Yes | Parameterize target dates | Backtest runs out-of-sample |
| Missing CLI settlement | Data/Settlement | Agent 4 | High | Yes | Yes | Implement daily auto-settlement | Paper trades reconcile |
| Incomplete edge math | Execution | Agent 5 | High | Yes | Yes | Add fee/slippage models to edge calculation | Edge accounts for 7% equivalent fee |
| No formalized risk gates | Risk | Agent 6 | Critical | No | Yes | Implement Drawdown, Liquidity, Freshness gates | Risk rules successfully trigger |
| Missing WebSocket path | Execution | Deep_Research | High | No | Yes | Construct local orderbook replica | Live book latency < 500ms |
| Uncalibrated distributions | Forecasting | Agent 3/4 | High | No | Yes | Implement CORP/Isotonic calibration | Reliability plots approach identity line |

### 12. Risk Register
| Risk | Category | Probability | Impact | Detection | Mitigation | Deployment gate |
|---|---|---|---|---|---|---|
| Wrong settlement target | Settlement | Low | High | Post-trade check | Strict CLI parsing | Stage 1 |
| Stale weather data | Data | Med | High | Timestamp validation | Ingestion freshness gate | Stage 1 |
| NWS API Outage | Data | High | High | ObHistory check | Implement HTML fallback parser | Stage 1 |
| Incorrect bin mapping | Market | High | Critical | Code Review | Update `REQUIRED_BINS` | Stage 0 |
| Uncalibrated probabilities | Model | High | High | ECE monitoring | Implement Isotonic calibration | Stage 3 |
| Lookahead leakage | Backtesting | Med | Critical | Code Review | Strictly scope input timestamps | Stage 3 |
| Fee/slippage omission | Execution | High | High | Edge calc test | Integrate Breakeven math | Stage 4 |
| Contract mapping error | Execution | Med | High | Ticker validator | Unit test KXHIGHMIA logic | Stage 4 |
| LLM bypass | Risk | Low | Critical | Code Review | LLMs isolated from execution code | Stage 5 |
| Missing risk gate | Risk | High | Critical | Test Suite | Formal RiskEngine interface | Stage 5 |
| Broken dashboard | Monitoring | Med | Low | UI integration test | Switch to structured JSON | Stage 6 |
| Secret exposure | DevOps | Low | Critical | Env scan | Secret management | Stage 8 |
| Deployment drift | DevOps | Med | Med | CI/CD sync | Relative paths / parameterized config | Stage 8 |
| Order reconciliation failure | Execution | Med | High | Ledger validation | Transactional DB migration | Stage 8 |
| Overfitting small sample | Model | High | High | Out-of-sample test | Reserve holdout data strictly | Stage 3 |

### 13. Staged Deployment Roadmap

#### Stage 0 — Freeze and Audit Baseline
- **Objective:** Secure the existing read-only MVP and address immediate critical bugs.
- **Tasks:** Fix `pyproject.toml` dependencies; update `REQUIRED_BINS` to target specs.
- **Acceptance criteria:** Environment installs cleanly via `pip install .`; core tests pass with new bin logic.
- **Failure conditions:** Bin mapping alters historical records corruptively.

#### Stage 1 — Data Integrity and Settlement Correctness
- **Objective:** Achieve reliable daily weather data processing.
- **Tasks:** Add ObHistory fallback to `nws_live_client.py`; build `settlement_check.py` to scrape NWS CLI.
- **Acceptance criteria:** Live NWS data fetches reliably; yesterday's high is confirmed automatically.
- **Failure conditions:** Failure to parse revised CLI vs preliminary CLI or API outages block updates.

#### Stage 2 — Forecast Probability Engine
- **Objective:** Overhaul heuristic distributions with statistical best practices.
- **Tasks:** Integrate NBM P10/P90 values into a Normal/Skew-Normal generator.
- **Acceptance criteria:** Model probabilities natively sum to 1.0; impossible bins zeroed.
- **Failure conditions:** Fat tails predict 88°F on a 65°F winter day.

#### Stage 3 — Backtesting and Calibration
- **Objective:** Enable valid simulation over historical holds.
- **Tasks:** Parameterize the forecast pipeline with `target_date`; implement ECE and Reliability Diagrams.
- **Acceptance criteria:** Can loop over May 2025–April 2026 generating out-of-sample predictions.
- **Failure conditions:** Pipeline crashes on missing data days or leaks future knowledge.

#### Stage 4 — Market Data and Edge Calculation
- **Objective:** Introduce realistic trading friction.
- **Tasks:** Add Kalshi fee formula to edge calculations (`P_be = p + 0.07 * p * (1 - p)`); parse orderbook liquidity.
- **Acceptance criteria:** `model_edge = P_model - P_breakeven_market` calculation outputs correctly.
- **Failure conditions:** Ignoring spread leads to negative expected-value signals.

#### Stage 5 — Hard-Coded Risk Engine
- **Objective:** Fortify the codebase against erratic execution.
- **Tasks:** Build a dedicated `RiskEngine` module for Drawdown, Liquidity, Concentration, and Freshness gates.
- **Acceptance criteria:** Test suite proves simulated dangerous orders are rejected.
- **Failure conditions:** Discretionary override capabilities exist.

#### Stage 6 — Monitoring and Operator Console
- **Objective:** Unify situational awareness safely.
- **Tasks:** Refactor Streamlit dashboard to use structured JSON state.
- **Acceptance criteria:** Dashboard gracefully handles missing datasets or API outages.
- **Failure conditions:** UI crashes on a missing `latest_forecast.md` file.

#### Stage 7 — Paper Trading Validation
- **Objective:** Confirm PnL stability in the local simulated environment.
- **Tasks:** Let the parameterized system run autonomously matching predictions vs market snapshots.
- **Acceptance criteria:** 30 days of positive PnL in simulation.
- **Failure conditions:** System exhibits massive drawdown in simulation.

#### Stage 8 — Limited Live Readiness
- **Objective:** Begin strictly controlled, sub-dollar execution paths.
- **Tasks:** Migrate to transactional DB; implement Kalshi API WebSocket feeds; build kill switches.
- **Acceptance criteria:** Successful sub-dollar real-money trade, fully audited and reconciled.
- **Failure conditions:** Execution delays, unhandled timeouts, token exposure.

#### Stage 9 — Production Hardening
- **Objective:** Scale up to normal risk caps.
- **Tasks:** Complete security audit, refine calibration loop.
- **Acceptance criteria:** System runs 30 days hands-off with steady PnL.
- **Failure conditions:** Edge deterioration.

### 14. Exact Next 10 Engineering Tasks
1. **Fix pyproject.toml dependencies.**
   - *Files:* `pyproject.toml`
   - *Why:* Prevents environment setup failures in `streamlit` and `pandas`.
   - *Test:* Run `pip install .` on fresh venv. Supports Stage 0.
2. **Update REQUIRED_BINS.**
   - *Files:* `backend/src/shared/types.py`, `backend/src/forecasting/bin_converter.py`
   - *Why:* Unblocks accurate model output generation.
   - *Test:* Validate bins `= ['<=79', '80-81', '82-83', '84-85', '86-87', '>=88']`. Supports Stage 0.
3. **Add ObHistory fallback to NWS Live Client.**
   - *Files:* `backend/src/weather/nws_live_client.py`
   - *Why:* Fixes the current failing ingestion pipeline.
   - *Test:* `update_nws_live_data.sh` produces non-empty observation table. Supports Stage 1.
4. **Implement automated CLI/CLIMIA settlement.**
   - *Files:* `backend/src/scheduler/settlement_check.py`
   - *Why:* Manual entry limits scale and backtesting speed.
   - *Test:* Scrapes and logs correct historical settlement values. Supports Stage 1.
5. **Parameterize forecast models with target_date.**
   - *Files:* `backend/src/forecasting/rules_model.py`
   - *Why:* Unblocks the backtesting replay loop.
   - *Test:* Run forecast for historical date without leaking future data. Supports Stage 3.
6. **Calculate Fee-Adjusted Breakeven Edge.**
   - *Files:* `backend/src/paper_trading/signal_generator.py`
   - *Why:* Prevents negative-EV paper trades by accurately modeling market friction.
   - *Test:* Edge calculation incorporates breakeven formula. Supports Stage 4.
7. **Decouple signal_generator.py from Markdown.**
   - *Files:* `backend/src/paper_trading/signal_generator.py`
   - *Why:* Current logic is fragile.
   - *Test:* System ingests JSON output directly. Supports Stage 6.
8. **Integrate NBM v5.0 Percentile Ingestion.**
   - *Files:* `backend/src/data/nws_parser.py`
   - *Why:* Foundational baseline for probabilistic forecasting.
   - *Test:* Extracts 10th-90th percentiles for KMIA. Supports Stage 2.
9. **Develop ECE and Reliability Diagrams Metric.**
   - *Files:* `backend/src/calibration/metrics.py`
   - *Why:* Ensures model probabilities match reality.
   - *Test:* Generates numeric ECE score. Supports Stage 3.
10. **Implement Basic Hardcoded Risk Engine Module.**
    - *Files:* `backend/src/risk/engine.py` (New)
    - *Why:* Formalizes safety protocols currently absent from the system.
    - *Test:* Unit tests reject simulated dangerous orders. Supports Stage 5.

### 15. Test Plan
| Test area | Test name | Purpose | Files/modules | Required before paper? | Required before live? |
|---|---|---|---|---:|---:|
| Target | `test_bin_mapping_structure` | Validates new boundaries | `types.py` | Yes | Yes |
| Data | `test_nws_fallback_parser` | Validates ObHistory html parse | `nws_live_client.py` | Yes | Yes |
| Settlement | `test_climia_auto_ingest` | Ensures data is fetched | `settlement_check.py` | Yes | Yes |
| Forecasting | `test_probability_sums_to_one` | Validates distribution | `rules_model.py` | Yes | Yes |
| Backtesting | `test_strict_lookahead_gate` | Prevents future leakage | `rules_model.py` | Yes | Yes |
| Execution | `test_fee_breakeven_math` | Confirms edge sanity | `signal_generator.py` | Yes | Yes |
| Risk | `test_stale_data_rejection` | Checks freshness gate | `engine.py` | Yes | Yes |
| Monitoring | `test_dashboard_missing_data_fallback` | Validates error handling | `web_console.py` | Yes | Yes |

### 16. Final Go / No-Go Decision
- **Current readiness level:** READY FOR LOCAL SANDBOX
- **Continue paper research:** YES
- **Allow paper trading:** NO (Must complete Stage 0, 1, 3, and 4 first).
- **Allow live trading:** NO
- **Next promotion target:** READY FOR PAPER TRADING
- **Exact conditions for promotion:** Bin mapping resolved, NWS ingestion fixed (fallback), parameterized backtesting complete, automated live settlement operational, and fee/slippage logic integrated into models.

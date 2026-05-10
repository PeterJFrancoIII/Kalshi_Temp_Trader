# Shared Agent Context — Kalshi Temp Trader

This file is the shared working context for the multi-agent audit of the KMIA Kalshi temperature project.

All agents must read this file before starting their assigned audit. Each agent must append or update only their assigned section with concise findings, evidence pointers, blockers, and handoff notes.

## Model Assignments

- Project Admin / Orchestrator Agent: Gemini 3.1 Pro
- Specialist Agents: Gemini 3 Flash

Gemini 3.1 Pro owns architecture-level reasoning, conflict resolution, final readiness classification, deployment roadmap, and final go/no-go decision.

Gemini 3 Flash agents own focused subsystem audits, evidence collection, PASS/PARTIAL/FAIL/UNKNOWN findings, specific fixes, and acceptance tests.

## Core Project Objective

Audit and improve the `Kalshi_Temp_Trader` project so it can safely progress from a KMIA research / paper-trading system toward a production-grade automated Kalshi trading bot, if and only if every deployment gate is satisfied.

Primary research source:

- `Deep_Research_Consolidate_1-9.md`

Primary repo:

- `PeterJFrancoIII/Kalshi_Temp_Trader`

Current baseline from Agent 1:

- Current repo status: `RESEARCH_MVP`
- Current safety posture: real-money trading disabled
- Current market access: read-only
- Current readiness: `READY FOR LOCAL SANDBOX / PAPER-RESEARCH REVIEW`, not live-ready

## Non-Negotiable Requirements

The system must eventually prove all of the following before any live deployment:

1. Correct target: official KMIA daily maximum temperature, not generic Miami weather.
2. Correct settlement handling: distinguish METAR, ASOS, 5-minute observations, preliminary CLI, final/corrected CLI, and settlement revisions.
3. Timestamped and freshness-checked weather data.
4. KMIA observation ingestion available to model and dashboard.
5. Probabilistic forecast output, not only deterministic highs.
6. Correct Kalshi settlement-bin conversion.
7. User target bins: `<=79`, `80-81`, `82-83`, `84-85`, `86-87`, `>=88`.
8. Calibration metrics and reliability validation before live trading.
9. Correct KXHIGHMIA contract mapping.
10. Fee/slippage-aware breakeven and edge calculation.
11. Hard-coded risk gates that cannot be bypassed by LLMs.
12. Sandbox/live separation.
13. Order reconciliation before any live execution.
14. Full audit logs for every recommendation, decision, order, and settlement.
15. Operator dashboard showing data freshness, model outputs, market state, and risk gates.

## Global Blockers

Any of these blocks live trading:

- Wrong station or settlement target.
- Missing KMIA live observation ingestion.
- Missing CLI/final settlement handling.
- Missing timestamps or freshness checks.
- Missing stale-data no-trade gate.
- Deterministic-only forecast.
- Missing calibrated bin probabilities.
- Current-bin / target-bin mismatch unresolved.
- Incorrect Kalshi contract mapping.
- Missing fee/slippage-adjusted breakeven.
- Missing hard-coded risk gates.
- Any risk bypass path.
- Any LLM-controlled sizing or execution authority.
- No sandbox/live separation.
- No order reconciliation.
- No audit logging.
- Any real-money trading path before explicit real-trading gate approval.

## Shared Evidence Standard

Every material claim must include exact evidence:

- File path.
- Function/class name.
- Config key.
- Script name.
- Test name.
- Data artifact path.
- Runtime log or dashboard artifact, if available.

Status labels:

- `PASS` = implemented, connected, and directly verified with evidence.
- `PARTIAL` = exists but incomplete, untested, disconnected, stale-risky, or unclear.
- `FAIL` = missing or wrong.
- `UNKNOWN` = not enough evidence yet.

## Shared Write Protocol

Each agent must update only their own section below.

Use this format:

```markdown
### Agent N — <Name> — Update YYYY-MM-DD

#### Status
<one of: BLOCKED, PAPER-READY WITH WARNINGS, PAPER-READY, LIVE-BLOCKED, LIVE-READY, LOCAL-ONLY, SAFE READ-ONLY>

#### Key Findings
- ...

#### Evidence
- `path/to/file.py::function_name` — finding.

#### Blockers
- ...

#### Required Fixes
- ...

#### Acceptance Tests
- ...

#### Handoff Notes
- What the next agent needs to know.
```

Do not overwrite another agent's section. If changing a prior conclusion, add a new dated update and explain why.

## Agent Run Order

1. Agent 1 — Project Admin / Orchestrator — Gemini 3.1 Pro — COMPLETE
2. Agent 2 — Weather Data Agent — Gemini 3 Flash — NEXT / IN PROGRESS
3. Agent 3 — Forecast Model Agent — Gemini 3 Flash
4. Agent 4 — Backtesting Agent — Gemini 3 Flash
5. Agent 5 — Kalshi Market Data / Execution Agent — Gemini 3 Flash
6. Agent 6 — Risk Engine Agent — Gemini 3 Flash
7. Agent 7 — DevOps / Monitoring Agent — Gemini 3 Flash
8. Final Roll-Up — Project Admin / Orchestrator — Gemini 3.1 Pro

## Agent 1 — Project Admin / Orchestrator — Update 2026-05-10

#### Status
READY FOR LOCAL SANDBOX / PAPER-RESEARCH REVIEW; not live-ready.

#### Key Findings
- Repo metadata identifies the project as `RESEARCH_MVP`.
- Existing governance states real-money trading is disabled and market access is read-only.
- Current architecture should be treated as research/paper infrastructure until specialist audits prove otherwise.
- Agent 2 must run before Agent 3 because weather/settlement correctness is foundational.

#### Evidence
- `.agent/MACHINE_INDEX.yaml` — `status: RESEARCH_MVP`, `real_money_trading: false`, `market_access: read-only`, `allowed_station: KMIA`.
- `.agent/MASTER_DESCRIPTOR.md` — describes MVP Research & Paper-Trading phase and read-only safety layer.
- `.agent/rules/10-safety.yaml` — forbids real-money trading, order execution functions, API secrets/private keys, and automatic execution.
- `backend/src/shared/types.py` — defines KMIA-specific schemas and current bins.
- `backend/src/forecasting/rules_model.py` — rules-based forecast and impossible-bin zeroing.
- `backend/src/ingestion/kmia_live_fetcher.py` — NWS observation/obhistory fetch functions.
- `backend/src/ingestion/climia_parser.py` — CLI/CLIMIA parser.
- `backend/src/market_data/kalshi_contract_mapper.py` — KXHIGHMIA filtering and dry-run comment.

#### Blockers
- No live trading allowed under current safety rules.
- Specialist audits still required for weather data, forecasting, backtesting, market mapping, risk, and DevOps.
- Current bins differ from requested future bins.

#### Required Fixes
- Complete Agent 2 weather-data audit.
- Complete Agent 3 model/bin/calibration audit.
- Complete remaining specialist audits before final deployment decision.

#### Acceptance Tests
- Each agent produces structured report with exact file/function evidence.
- Final Gemini 3.1 Pro roll-up reconciles all findings into one readiness decision.

#### Handoff Notes
- Agent 2 should focus on KMIA live observations, CLIMIA settlement, timestamp/freshness, NWS forecast pipeline, snapshot schema flow, and the Streamlit NWS live table bug.

## Agent 2 — Weather Data Agent

_Pending._

## Agent 3 — Forecast Model Agent

_Pending._

## Agent 4 — Backtesting Agent

_Pending._

## Agent 5 — Kalshi Market Data / Execution Agent

_Pending._

## Agent 6 — Risk Engine Agent

_Pending._

## Agent 7 — DevOps / Monitoring Agent

_Pending._

## Final Roll-Up — Project Admin / Orchestrator

_Pending._

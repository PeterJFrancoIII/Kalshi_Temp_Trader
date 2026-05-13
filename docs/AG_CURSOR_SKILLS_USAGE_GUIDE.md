# AG/Cursor Skills Usage Guide

## 1. Purpose
This file maps reusable Skills to each project agent role in the Kalshi KMIA forecasting and trading paper-evaluation system. It ensures that agents invoke the correct specialized logic and adhere to project-specific constraints.

## 2. Required Shared Skills for All Agents
All agents must have access to and use these core skills for standard development tasks:
- **writing-plans**: For creating implementation plans before execution.
- **executing-plans**: For tracking progress against plans.
- **systematic-debugging**: For resolving test failures or bugs.
- **verification-before-completion**: For ensuring work is complete and tested.
- **tdd**: For test-driven development.

## 3. Optional Shared Skills
- **using-git-worktrees**: For managing concurrent work on different branches.
- **finishing-a-development-branch**: For cleanup and merge readiness.
- **improve-codebase-architecture**: For refactoring and design improvements.
- **webapp-testing**: Required where UI or browser testing is involved.

## 4. Agent-Specific Skills
Map specialized skills to specific agent roles:
- **Agent 1** (Governance & Reviewer): `improve-codebase-architecture`, `finishing-a-development-branch`, `kalshi-agent-governance-rollup`
- **Agent 2** (Weather Data Ingestion): `kalshi-weather-settlement-safety`
- **Agent 3** (Forecast Modeling): `kmia-probability-modeling`
- **Agent 4** (Backtesting & Calibration): `point-in-time-backtesting`
- **Agent 5** (Market Discovery & Mapping): `kalshi-contract-range-mapping`
- **Agent 6** (Risk Engine): `risk-gate-auditor`
- **Agent 7** (UI/Console): `webapp-testing`
- **Agent 8** (Final Roll-up & Go/No-Go): `improve-codebase-architecture`, `kalshi-agent-governance-rollup`, `risk-gate-auditor`

## 5. Standard Prompt Pattern
When prompting an agent, use the following template to enforce constraints and required reporting:

> Use the following Skills: [list]. First inspect relevant files. Do not modify code until you produce a plan. Do not commit. Do not push. This project is dry-run/paper-evaluation only. Report inputs read, files inspected, files changed, tests run, safety findings, lookahead findings, risks, next task, and machine-readable JSON.

## 6. Example Prompts

### Agent 2: Weather Timestamp Audit
> Use the following Skills: `kalshi-weather-settlement-safety`, `writing-plans`. Inspect the recent weather data files in the data directory. Verify that all files have embedded JSON timestamps and that no files are being selected based on filesystem mtime. Do not modify code. This project is dry-run/paper-evaluation only. Produce a report with safety findings and a machine-readable JSON summary.

### Agent 3: Probability Distribution Implementation
> Use the following Skills: `kmia-probability-modeling`, `writing-plans`, `tdd`. Implement the probability distribution blender for the KMIA model. Ensure the output is a `Dict[int, float]` summing to ~1.0. Do not use legacy fixed bins. Do not modify code until you produce a plan approved by Agent 1. This project is dry-run/paper-evaluation only.

### Agent 4: Point-in-Time Backtest Audit
> Use the following Skills: `point-in-time-backtesting`, `writing-plans`. Audit the backtesting coordinator to ensure it strictly uses embedded timestamps and excludes any artifacts created after the simulated cutoff. Verify that a `replay_manifest.json` is recorded. Do not modify code. This project is dry-run/paper-evaluation only.

### Agent 5: Contract Mapping Audit
> Use the following Skills: `kalshi-contract-range-mapping`, `writing-plans`. Audit the `weather_market_mapper` to ensure it parses active contract ranges dynamically from contract text. Verify that ambiguous contracts are marked untradable. Do not modify code. This project is dry-run/paper-evaluation only.

### Agent 6: Risk Gate Audit
> Use the following Skills: `risk-gate-auditor`, `writing-plans`. Audit the risk engine to ensure all gates fail closed on missing weather timestamps or stale data. Verify that no live trading methods are exposed. Do not modify code. This project is dry-run/paper-evaluation only.

### Agent 8: Roll-up Audit
> Use the following Skills: `kalshi-agent-governance-rollup`, `writing-plans`. Perform a final roll-up audit of the system before declaring paper-evaluation readiness. Review the safety findings from all previous agents and verify Agent 1 approvals. This project is dry-run/paper-evaluation only.

## 7. Red Lines
Do NOT cross these boundaries under any circumstances:
- **No live trading** or real money risk.
- **No order execution** (placement or cancellation).
- **No HTTP write methods** to trading APIs.
- **No filesystem mtime** for point-in-time backtesting.
- **No fixed global bins** for active contract mapping in production logic.
- **No "latest" artifacts** in historical replay.
- **No synthetic risk inputs** that bypass fail-closed gates.

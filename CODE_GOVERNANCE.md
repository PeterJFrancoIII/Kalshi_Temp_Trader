# Code Governance Rules

## Language Decision

The MVP is Python-first.

All ingestion, parsing, forecasting, calibration, Kalshi read-only integration, recommendation logic, scheduling, and testing must be written in Python.

Do not create a React/frontend app until the Python forecasting and calibration pipeline is stable.

If a dashboard is needed in MVP, use Streamlit or a simple Python-generated report first.

## Build Philosophy

This is a financial-adjacent forecasting app. Code must be auditable, deterministic where possible, and safe by default.

The MVP must not place real-money trades.

## Safety Rules

1. No real-money order placement in MVP.
2. Kalshi integration is read-only until explicitly approved.
3. Any future trading code must be isolated behind a feature flag:
   - ENABLE_REAL_TRADING=false by default
4. Any future order placement must use:
   - limit orders only
   - maximum daily risk limit
   - maximum per-trade risk limit
   - kill switch
   - full audit logs
5. No market orders in automated mode.
6. No trading if data is stale, missing, malformed, or contradictory.
7. No trade recommendation if probability bins fail validation.

## Agent Coordination Rules

1. Each agent must read:
   - MASTER_CONTEXT.md
   - CODE_GOVERNANCE.md
   - DATA_SOURCES.md
   - WEATHER_MODEL_SPEC.md
2. Each agent must only work in assigned folders.
3. Do not overwrite files owned by another agent unless the workplan explicitly says so.
4. Shared types must be changed only by the Project Architect Agent.
5. Database schema changes must go through the Database Agent.
6. Each agent must create or update tests for their module.
7. Every module must expose a small, typed interface.
8. No agent should introduce hidden global state.
9. No agent should hardcode secrets.
10. All external data fetchers must store raw responses for debugging.

## Code Style

Backend:

- Python 3.11+
- Prefer typed functions.
- Use Pydantic models or dataclasses for structured data.
- Use pytest for tests.
- Use clear module boundaries.

Frontend:

- MVP is strictly Python-first. No React or frontend application should be created.
- Streamlit (Python) is the designated option for any future dashboard needs.
- If React is required well beyond MVP, TypeScript and Tailwind will be used.

## Required Validation

All prediction outputs must pass:

- Required bins present.
- All probabilities between 0 and 1.
- Probabilities sum between 0.995 and 1.005.
- Impossible lower bins zeroed out.
- Station is KMIA.
- Metric is daily_max_temperature_f.
- Date is valid.
- Data freshness fields present.

## Logging

Every daily run must log:

- data sources fetched
- source timestamps
- parser warnings
- forecast inputs
- probability output
- LLM review output
- Kalshi market snapshot, if available
- recommendation decision
- final settlement result

## Testing Requirements

Every agent must provide tests.

Minimum tests:

- parser tests
- schema validation tests
- impossible-bin zeroing tests
- probability-sum tests
- stale-data detection tests
- settlement validation tests

## Prohibited in MVP

- Real-money trading
- Auto-execution
- Multi-station expansion
- Rain markets
- Low-temperature markets
- Non-weather Kalshi markets
- Untracked manual overrides

## Real Trading Transition

Transitioning from the current research MVP to any form of real-money execution is strictly forbidden without a formal project phase shift and architecture review. 

See [docs/REAL_TRADING_GATE.md](docs/REAL_TRADING_GATE.md) for the mandatory evidence and technical controls required before any discussion of real trading.

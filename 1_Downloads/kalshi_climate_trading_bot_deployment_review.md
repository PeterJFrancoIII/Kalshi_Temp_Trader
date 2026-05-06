# Kalshi Climate Trading Bot Deployment Review

## Deployment review verdict

The Gemini report is **useful as an architecture and research input**, but it is **not safe to deploy directly into live autonomous trading**. Treat it as a blueprint for a **paper/shadow-mode deployment first**, then graduate to live trading only after the settlement, weather, model, risk, and execution assumptions are independently validated.

The connected GitHub surface was checked. Searches for “Kalshi” and “trading bot” returned no installed repo, and the visible installed repositories do not appear to include the Kalshi Climate Trading Bot. That means this document can prepare the deployment plan and integration backlog now, but the actual existing Antigravity-built system cannot be safely patched, PR’d, or deployed until the actual repo/branch is connected or uploaded.

## What from the report is deployable

### 1. Kalshi market/orderbook layer

The report correctly emphasizes reciprocal pricing: Kalshi orderbook responses expose Yes and No bids, and implied asks must be derived from the opposite-side bid.

Implementation requirement:

```text
yes_ask = 100 - no_bid
no_ask  = 100 - yes_bid
```

### 2. Authenticated API and WebSocket infrastructure

The bot needs both REST and WebSocket clients. The production system should include:

- RSA-PSS signing utility
- Authenticated REST client
- Authenticated WebSocket client
- reconnect and heartbeat handling
- snapshot and delta reconciliation
- rate-limit aware fallback behavior

### 3. Dynamic market discovery

The report’s recommendation to retrieve markets dynamically rather than hardcoding tickers is correct.

This should become a market-universe service that stores:

- market ticker
- event ticker
- series ticker
- expiration
- contract terms URL
- rule snapshot/hash
- station mapping
- city
- active/inactive status

### 4. Weather ingestion and settlement pipeline

The NWS-first approach is sound. The production bot should ingest official and near-real-time weather sources, but final settlement logic must be reconciled against the specific source used by the relevant Kalshi contract.

Required capabilities:

- NWS forecast ingestion
- station observation ingestion
- hourly temperature aggregation
- daily maximum calculation
- climate report reconciliation
- station anomaly detection
- fallback handling for missing/stale observations

### 5. Telemetry-first architecture

The recommended split between ingestion, decisioning, execution, risk, telemetry, and console is the right pattern.

The trading loop must not depend on UI rendering, and all decisions, orders, fills, risk changes, and data-quality flags should be persisted before any live order is placed.

## What must be corrected or validated before live trading

### 1. Do not trust the quoted edge metrics yet

The following metrics in the report are useful targets, but they must be reproduced on our own historical market snapshots, forecasts, observations, and resolved Kalshi outcomes:

- 1.27x uncertainty factor
- Sharpe 4.9
- model Brier score
- market Brier score
- PIT/KS calibration statistics

These should not drive real-money position sizing until independently reproduced.

### 2. Contract terms must be snapshotted per market

The report’s Local Standard Time, DST, and midnight-high discussion is important, but live code should not rely on generalized rules.

Each active market should store:

- exact contract terms URL
- contract terms hash
- settlement station
- settlement source
- settlement time window
- date/time interpretation
- daylight-saving behavior
- discovered timestamp

### 3. Weather observations need official reconciliation

NWS API observations are useful operationally, but final settlement reconciliation should compare:

- raw hourly observations
- aggregated local-day maximum
- NWS daily climate report
- archived climate data where available
- Kalshi settlement result

### 4. Treat the MADIS issue as a data-quality risk

The report’s warning about null or unreliable max/min fields should be implemented as a broader data-quality framework, not a single hardcoded assumption.

The system should flag:

- null max/min fields
- missing observations
- stale observations
- sudden spikes
- station divergence
- inconsistent time windows
- incomplete daily data

### 5. ATR-style stops need adaptation for binary contracts

ATR-style stops are directionally useful, but temperature contracts are binary, bounded, and sometimes illiquid.

The risk engine should prioritize:

- expected-value deterioration
- bid/ask spread
- order book depth
- time-to-expiration
- max market loss
- max daily loss
- model confidence
- stale data
- forced halt conditions

## Prepared deployment plan

### Phase 0 — Repo and safety freeze

Before touching code:

- Create a deployment branch, for example `deploy/kalshi-climate-shadow-v1`.
- Confirm the app’s current runtime stack, scheduler, database, and existing secrets handling.
- Ensure no API keys or RSA private keys are committed.
- Add `.env.example`, but never actual Kalshi credentials.
- Default every new trading module to `DRY_RUN=true`.

### Phase 1 — Read-only Kalshi integration

Implement:

- RSA-PSS signing utility
- read-only account/auth smoke test
- `/markets` discovery for weather/high-temperature markets
- market metadata persistence
- contract terms snapshot field
- unit tests for timestamp, path signing, query-string exclusion, and header generation

Deployment gate:

- No order placement code enabled yet.

### Phase 2 — WebSocket orderbook service

Implement:

- WebSocket authenticated connection
- subscribe/unsubscribe manager
- snapshot and delta local book maintenance
- reciprocal bid/ask normalization
- spread/depth anomaly detection
- REST reconciliation fallback

Normalized fields:

```text
yes_bid
no_bid
yes_ask = 100 - no_bid
no_ask  = 100 - yes_bid
mid_yes = (yes_bid + yes_ask) / 2
mid_no  = (no_bid + no_ask) / 2
```

Deployment gate:

- Local book must match REST snapshots over a multi-hour test window.

### Phase 3 — Weather and settlement service

Implement:

- city/market-to-station config
- primary and alternate station monitoring
- hourly observation aggregation
- daily high calculation using the correct local settlement window
- CLI/NCEI reconciliation job
- data-quality flags

Data-quality flags:

- missing observation
- stale observation
- station divergence
- suspicious spike
- settlement-window ambiguity

Deployment gate:

- Reproduce known resolved outcomes before any trading.

### Phase 4 — Strategy shell in shadow mode

Implement:

- model interface that accepts market, weather, time, and book features
- probability output in the preferred 2-degree bins
- EV calculator
- signal logger
- no live orders

Preferred probability bins:

```text
<=79
80-81
82-83
84-85
86-87
>=88
```

Deployment gate:

- Shadow signals must be logged against market prices and later scored against settlement.

### Phase 5 — Risk engine

Implement hard constraints before execution:

- global kill switch
- per-market max exposure
- per-city max exposure
- daily loss limit
- max drawdown halt
- open-order cap
- min liquidity/depth
- max spread
- min model edge
- fractional Kelly cap
- halt state requiring manual reset

Recommended default:

- Use very conservative fractional Kelly sizing during pilot.
- Do not allow full Kelly sizing in live mode.

Deployment gate:

- Simulated bad data, bad fills, stale books, and network failures must trigger safe behavior.

### Phase 6 — Paper trading

Implement:

- simulated order placement and fills
- fill assumptions by bid/ask side
- slippage model
- P&L by market/city/day
- reconciliation dashboard
- “would-have-traded” logs

Deployment gate:

- Paper trading should run across enough resolved markets to show calibration, not just profit.

### Phase 7 — Live restricted pilot

Only after the prior gates pass:

- enable live orders on a tiny allowlist
- start with very small max notional
- use maker-only or controlled limit orders first
- require manual approval for the first live session
- keep automatic halt thresholds tight
- continue shadow-mode comparison alongside live decisions

## Implementation backlog for the existing system

Use this as the PR stack once the actual repo is available.

### PR 1 — `kalshi_client`

Scope:

- auth signer
- REST client
- read-only smoke tests
- typed response models

Acceptance criteria:

- Auth smoke test passes.
- No secrets are committed.
- Query strings are excluded from signed path where required.
- Timestamp uses milliseconds.

### PR 2 — `market_universe`

Scope:

- dynamic `/markets` discovery
- weather series filters
- market terms snapshotting
- station mapping config

Acceptance criteria:

- Active high-temperature markets are discoverable without hardcoded daily tickers.
- Every stored market has metadata sufficient for settlement reconciliation.

### PR 3 — `orderbook_service`

Scope:

- WebSocket manager
- local book store
- bid/ask derivation
- reconciliation checks

Acceptance criteria:

- Local orderbook survives reconnects.
- Derived asks are stored explicitly.
- REST reconciliation detects drift.

### PR 4 — `weather_service`

Scope:

- NWS API client
- station observations
- daily max aggregation
- CLI/NCEI reconciliation hooks

Acceptance criteria:

- Daily highs are calculated from hourly observations.
- Missing/stale/anomalous data is flagged.
- Alternative stations can be monitored.

### PR 5 — `strategy_shadow`

Scope:

- model interface
- EV engine
- 2-degree bin probability output
- shadow signal table

Acceptance criteria:

- No live order placement.
- Every signal includes feature snapshot, model probability, market price, EV, and timestamp.

### PR 6 — `risk_engine`

Scope:

- fractional Kelly sizing
- hard caps
- circuit breakers
- kill switch
- manual reset state

Acceptance criteria:

- Risk engine blocks orders independently of strategy.
- Halt state persists across restart.
- Kill switch cancels open orders and blocks new orders.

### PR 7 — `execution_manager`

Scope:

- paper execution first
- live execution behind feature flag
- order lifecycle tracking
- idempotent client order IDs

Acceptance criteria:

- Live trading is impossible unless explicitly enabled.
- Orders are idempotent.
- Reconciliation handles partial fills, cancellations, and rejected orders.

### PR 8 — `console`

Scope:

- portfolio metrics
- current market scanner
- model probability vs. market price
- decision logs
- risk state
- halt/reset controls

Acceptance criteria:

- UI is read-only by default.
- Risk controls are separated from display logic.
- Trading loop does not depend on dashboard uptime.

### PR 9 — `deployment`

Scope:

- Docker or production process manager
- health checks
- structured logs
- alerting hooks
- backup/recovery procedure

Acceptance criteria:

- Bot can restart without losing open-order or risk state.
- Logs are structured and queryable.
- Heartbeat and failure alerts are emitted.

## Current deploy status

### Ready now

- Architecture review
- Implementation backlog
- Shadow-mode deployment plan

### Not ready yet

- Live autonomous trading

### Blocked

The actual Kalshi bot repo or branch is not currently accessible in the connected GitHub environment. The GitHub connector exposed unrelated repositories and did not show a Kalshi Climate Trading Bot repo.

To proceed with implementation, provide one of the following:

- connect the correct GitHub repository
- share the repository URL if it is already connected but named unexpectedly
- upload the project as a zip
- provide the Antigravity project folder contents

Once the actual codebase is available, this plan can be converted into exact file-level changes and a deployable PR stack.

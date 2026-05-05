---
title: "LLM-Run Kalshi Climate Quant Trading System"
version: "1.0"
date: "2026-05-05"
project: "Kalshi Miami / climate temperature-bin forecasting and trading automation"
intended_reader: "Gemini Deep Research, Antigravity agent, quantitative developer, system architect"
operating_environment: "Home-based small Linux server"
primary_builder: "Antigravity IDE"
primary_llm_actor: "Gemini 3.1 Pro High or equivalent agentic coding model"
mode_targets:
  - paper_trading
  - live_trading_with_button_gated_activation
  - research_backtesting
  - signal_quality_monitoring
regulatory_and_safety_note: "This is an engineering and research plan, not financial advice. Live trading should remain disabled until backtesting, paper trading, risk limits, and manual approvals are proven."
---

# 1. Executive Summary

This project is a probabilistic weather-to-market trading system for Kalshi climate and temperature-bin markets. The current work has focused on forecasting daily maximum temperature bins, initially for Miami / MIA, and comparing those probabilities against Kalshi market prices. The next rebuild should turn the prototype into a clean, modular, auditable system that can run on a home Linux server, continuously ingest weather data and Kalshi market data, produce calibrated bin probabilities, decide whether signal quality is high enough to trade, and run either paper trading or live trading behind explicit controls.

The critical lesson from the May 5, 2026 miss is that deterministic bin prediction is not enough. At roughly T-minus 12 hours, the estimated max bin was 84-85F, but the realized high was 88F. This is not just a one-off error. It exposes a structural need for full probability distributions, uncertainty-aware decisioning, upper-tail calibration, live observation nowcasting, and no-trade gating when the signal is weak or weather variables are unstable.

The rebuild should be organized into four independent layers:

1. Weather prediction layer: outputs calibrated probabilities for each bin.
2. Kalshi market-data layer: discovers relevant markets, maps contracts to bins, streams order books and trades, and normalizes prices.
3. Strategy and risk layer: compares model probabilities to executable market prices, decides whether edge exists, and blocks trades under poor signal quality.
4. Execution and monitoring layer: paper trades by default, live trades only after explicit activation, persistent logs, alerts, kill switches, and post-event settlement analysis.

The system should not be “LLM guesses trades.” The LLM should be the orchestrator, code maintainer, research assistant, and anomaly reviewer. The quantitative core should be deterministic, tested Python services with explicit schemas, reproducible data, and strict safety boundaries.

# 2. Current System as We Have It

## 2.1 What has already been accomplished

The project has already established the core conceptual stack:

- A target market type: Kalshi high-temperature / climate binary contracts.
- A target station / city: initially Miami International Airport, MIA.
- A target variable: daily maximum temperature in Fahrenheit.
- Standard bins:
  - <=79
  - 80-81
  - 82-83
  - 84-85
  - 86-87
  - >=88
- A historical station dataset: MIA daily history from 1950-01-01 through 2026-04-30.
- A key empirical finding: recent same-season Miami max temperatures are materially hotter than the long-run historical baseline.
- A known failure case: T-minus 12 hour forecast centered too low, predicting 84-85F while the realized result was 88F.
- A first rebuild specification: probability distributions over bins instead of deterministic single-bin forecasts.
- A first Kalshi API integration specification: separate market discovery, bin mapping, order-book ingestion, trade ingestion, and strategy comparison.

## 2.2 What the system currently tries to do

The project is trying to answer this repeated question:

> For a given Kalshi daily temperature contract event, what is the true probability of each settlement bin, and is the market price sufficiently wrong to justify a trade after spread, fees, slippage, uncertainty, and risk limits?

The system should eventually produce an event-level object like this:

```yaml
prediction_event:
  location: MIA
  event_date: 2026-05-05
  as_of_time_local: "2026-05-04 20:00:00 America/New_York"
  horizon_hours: 12
  probabilities:
    "<=79": 0.01
    "80-81": 0.03
    "82-83": 0.08
    "84-85": 0.20
    "86-87": 0.28
    ">=88": 0.40
  signal_quality:
    score: 0.74
    decision: tradable
    reason: "Forecast guidance and live trend support upper-tail risk."
```

And a market-joined object like this:

```yaml
market_join:
  bin: ">=88"
  model_probability: 0.40
  yes_bid: 0.27
  yes_ask: 0.31
  spread: 0.04
  edge_vs_ask: 0.09
  liquidity_score: 0.68
  action: "paper_buy_yes"
```

# 3. Why the May 5 Miss Matters

The May 5 miss is a design-defining failure case. A model that says the most likely bin is 84-85F but the event settles at 88F can fail in three different ways:

1. Forecast bias: the raw temperature expectation was too low.
2. Distribution error: the model may have had the right central estimate but too little upper-tail probability.
3. Trading error: the strategy may have overcommitted to a narrow bin instead of respecting uncertainty.

For Kalshi bin contracts, a 3-4 degree error is large because the payoff boundary is discrete. A small weather miss can become a total contract miss. Therefore, the system should be optimized for calibrated bin probabilities, not just mean absolute temperature error.

The rebuilt system must answer:

- What is the probability of each bin?
- How uncertain is the forecast at this horizon?
- Is the market price wrong enough to overcome uncertainty and transaction costs?
- Are weather variables stable enough to trade today?
- Should the system refuse to trade because the signal is low quality?

# 4. Desired End State

## 4.1 Product vision

Build a local-first, Linux-hosted, LLM-supervised quantitative trading platform for Kalshi climate markets.

The system should have:

- Automated Kalshi market discovery.
- Automated contract-to-bin mapping.
- Live WebSocket market data ingestion.
- REST fallback and periodic snapshots.
- Weather model ingestion and nowcasting.
- Full probability distributions over settlement bins.
- Strategy logic with edge, liquidity, and risk thresholds.
- Paper trading mode.
- Live trading mode available only through a deliberate UI switch.
- Daily postmortems comparing forecast, market price, trade decision, and settlement.
- A no-trade engine for poor signal quality days.
- A dashboard for local monitoring.
- LLM-assisted research, debugging, documentation, and anomaly review.

## 4.2 What “fully LLM run” should mean

The LLM should not be the sole black-box decision maker. Instead, the LLM should operate as an agent around deterministic infrastructure.

Recommended role split:

```yaml
llm_responsibilities:
  - read logs and explain anomalies
  - propose model improvements
  - generate code changes in Antigravity
  - maintain documentation
  - write daily postmortems
  - inspect poor-signal cases
  - recommend research experiments
  - summarize backtest results
  - flag suspicious market or weather data

non_llm_deterministic_responsibilities:
  - data ingestion
  - authentication and secret handling
  - probability calculation
  - calibration
  - backtesting
  - signal-quality scoring
  - order sizing
  - risk limits
  - live order placement
  - kill switches
  - audit logging
```

The LLM may recommend trades, but the actual execution decision should pass through deterministic gates.

# 5. External API and Data Assumptions

## 5.1 Kalshi API

The system should use Kalshi REST for discovery, snapshots, account state, and order actions, and Kalshi WebSocket for fast market updates. Kalshi’s current WebSocket documentation says connections require authentication during the handshake and can subscribe to channels including `ticker`, `trade`, `orderbook_delta`, and market lifecycle streams. WebSocket private/user channels include fill and market-position related updates. The system should therefore use WebSocket as the primary real-time source and REST as bootstrap / reconciliation. 

Kalshi authenticated requests use headers including `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-TIMESTAMP`, and `KALSHI-ACCESS-SIGNATURE`, with signatures based on request components and RSA-PSS SHA256. The private key must be stored outside the repository, preferably in environment variables, an encrypted secret file, or a local secret manager.

Kalshi rate limits are token-based for authenticated requests; most authenticated requests have a default token cost and account tier determines token budget per second. The bot must include a rate-limit-aware scheduler, request queue, retry policy, and backoff.

## 5.2 Weather data

The system should support multiple weather inputs:

- Historical station observations.
- Same-day and same-season analogs.
- Forecast model guidance.
- National Weather Service or other public forecast products.
- Live observations from the settlement station or nearest valid source.
- Hourly temperature trend.
- Dew point, cloud cover, wind direction/speed, sea breeze indicators, rain/storm timing, frontal boundaries, and heat-index-related regime indicators.

The exact weather APIs can be selected during implementation, but the architecture should isolate weather providers behind adapters.

# 6. Clean Architecture

## 6.1 Service map

```yaml
services:
  kalshi_market_discovery:
    purpose: "Find active climate/temperature markets and map contracts to bins."
    cadence: "1-5 minutes during active events; on lifecycle event immediately."

  kalshi_market_stream:
    purpose: "Maintain live order books and trades via WebSocket."
    cadence: "real time"

  weather_ingestor:
    purpose: "Pull historical, forecast, and live observation data."
    cadence: "5-15 minutes normally; 1-3 minutes near event close if supported."

  feature_builder:
    purpose: "Generate model features from weather, climatology, forecast guidance, and live trend."
    cadence: "after each weather update"

  probability_model:
    purpose: "Emit calibrated probability distribution over bins."
    cadence: "after each feature update"

  signal_quality_engine:
    purpose: "Decide whether today is tradable."
    cadence: "after each model update and market update"

  strategy_engine:
    purpose: "Compare model probabilities to market prices and generate candidate actions."
    cadence: "continuous or event-driven"

  execution_engine:
    purpose: "Paper or live order placement subject to risk limits."
    cadence: "event-driven"

  risk_engine:
    purpose: "Position sizing, exposure caps, kill switch, loss limits, duplicate-order prevention."
    cadence: "before every order and periodically"

  dashboard:
    purpose: "Local UI with event state, probabilities, prices, mode switch, logs, and alerts."
    cadence: "continuous"

  llm_research_agent:
    purpose: "Explain, improve, audit, and propose changes; never bypass deterministic risk gates."
    cadence: "scheduled and on anomaly"
```

## 6.2 Recommended repository layout

```text
kalshi-climate-bot/
  README.md
  pyproject.toml
  .env.example
  config/
    locations.yaml
    bins.yaml
    market_bin_overrides.yaml
    risk_limits.yaml
    strategy_profiles.yaml
    data_sources.yaml
  src/
    kalshi_client/
      auth.py
      rest.py
      websocket.py
      market_discovery.py
      orderbook.py
      schemas.py
    weather/
      historical.py
      forecast_providers.py
      live_observations.py
      station_metadata.py
      schemas.py
    modeling/
      features.py
      climatology.py
      forecast_blend.py
      calibration.py
      probability_model.py
      backtest.py
      metrics.py
    strategy/
      edge.py
      signal_quality.py
      sizing.py
      risk.py
      decision.py
    execution/
      paper_broker.py
      live_broker.py
      order_manager.py
      reconciliation.py
    storage/
      db.py
      migrations/
      parquet_writer.py
    dashboard/
      app.py
      components/
    llm_ops/
      prompts/
      daily_postmortem.md
      anomaly_review.md
      code_review_checklist.md
    scripts/
      run_market_stream.py
      run_weather_update.py
      run_backtest.py
      run_dashboard.py
      daily_report.py
  tests/
    test_bin_mapping.py
    test_orderbook_rebuild.py
    test_probability_calibration.py
    test_signal_quality.py
    test_risk_limits.py
    test_paper_execution.py
  data/
    raw/
    processed/
    backtests/
  logs/
```

# 7. Data Model

## 7.1 Temperature bin schema

```yaml
bins:
  - label: "<=79"
    min_f: null
    max_f: 79
  - label: "80-81"
    min_f: 80
    max_f: 81
  - label: "82-83"
    min_f: 82
    max_f: 83
  - label: "84-85"
    min_f: 84
    max_f: 85
  - label: "86-87"
    min_f: 86
    max_f: 87
  - label: ">=88"
    min_f: 88
    max_f: null
```

## 7.2 Prediction record

```yaml
prediction_record:
  prediction_id: uuid
  location_id: MIA
  station_id: USW00012839
  event_date: YYYY-MM-DD
  as_of_utc: timestamp
  horizon_hours: float
  model_version: string
  feature_version: string
  probabilities:
    "<=79": float
    "80-81": float
    "82-83": float
    "84-85": float
    "86-87": float
    ">=88": float
  expected_tmax_f: float
  p10_tmax_f: float
  p50_tmax_f: float
  p90_tmax_f: float
  uncertainty_score: float
  signal_quality_score: float
  tradability: tradable | monitor_only | no_trade
  no_trade_reasons: list[string]
```

## 7.3 Kalshi market record

```yaml
kalshi_market_record:
  observed_at_utc: timestamp
  event_ticker: string
  market_ticker: string
  location_id: MIA
  event_date: YYYY-MM-DD
  bin_label: string
  yes_bid: float
  yes_ask: float
  no_bid: float
  no_ask: float
  last_trade_price: float | null
  volume: float | null
  open_interest: float | null
  spread: float
  midpoint: float
  top_depth_yes: float
  top_depth_no: float
  liquidity_score: float
  source: websocket | rest_snapshot
```

## 7.4 Trade decision record

```yaml
trade_decision:
  decision_id: uuid
  as_of_utc: timestamp
  mode: paper | live
  event_ticker: string
  market_ticker: string
  bin_label: string
  model_probability: float
  market_yes_ask: float
  market_yes_bid: float
  fair_value_edge: float
  executable_edge_after_costs: float
  signal_quality_score: float
  liquidity_score: float
  risk_check: pass | fail
  action: no_trade | alert | paper_buy_yes | paper_sell_yes | live_buy_yes | live_sell_yes
  proposed_quantity: int
  max_loss_if_wrong: float
  reasons: list[string]
```

# 8. Weather Modeling Plan

## 8.1 Modeling objective

The objective is not to predict one temperature. It is to produce a calibrated probability distribution over settlement bins.

The correct scoring targets are:

- Log loss by bin.
- Brier score by bin.
- Calibration error.
- Reliability by horizon.
- Realized return after spread/fees/slippage in backtest.
- Drawdown and event-level concentration.

## 8.2 Baseline model

Start with a transparent ensemble:

```yaml
baseline_ensemble:
  inputs:
    - recent same-day-of-year climatology
    - recent same-season climatology
    - full-history climatology with low weight
    - latest forecast high
    - forecast bias correction by horizon
    - live observed temperature trend
    - time-of-day remaining heating potential
  output:
    - continuous distribution over TMAX
    - converted probability mass across Kalshi bins
```

## 8.3 Better model candidates

After the baseline is stable, compare:

- Quantile regression.
- Gradient boosted trees.
- Bayesian model averaging.
- Analog ensemble.
- Forecast-provider ensemble with learned horizon-specific bias.
- Online calibration layer that updates with recent forecast errors.
- Tail model for `>=88F` and other open-ended upper bins.

## 8.4 Features to add

```yaml
feature_groups:
  climatology:
    - day_of_year
    - rolling 7/15/30 day seasonal analogs
    - recent-year weighted analogs
    - ENSO or regime indicators if useful

  forecast_guidance:
    - forecast high
    - hourly forecast max
    - model spread across providers
    - last forecast revision direction
    - forecast issue time

  live_observation:
    - current temperature
    - current dew point
    - current wind speed
    - current wind direction
    - current cloud cover
    - temperature change last 1h/3h/6h
    - max so far today
    - heating hours remaining

  local_weather_regime:
    - sea breeze timing proxy
    - storm probability
    - cloud/rain timing
    - frontal boundary flag
    - wind from ocean vs inland

  market_features_for_analysis_only:
    - Kalshi midpoint
    - spread
    - volume
    - price momentum
    - orderbook imbalance
```

Important: market features should not be mixed into the weather model unless the goal is explicitly to predict settlement using both weather and market information. Keep a pure weather probability and a market-implied probability separate.

# 9. Signal Quality and No-Trade Engine

The system must decide when not to trade. This is central.

## 9.1 Reasons to block trading

```yaml
no_trade_reasons:
  weather_uncertainty:
    - forecast providers disagree by more than threshold
    - storm/cloud timing dominates max temperature outcome
    - sea breeze timing uncertain
    - current observed trend conflicts with forecast
    - model distribution is too flat across bins
    - top two bins are nearly tied and market edge is small

  data_quality:
    - missing live observations
    - stale weather data
    - stale Kalshi WebSocket
    - orderbook snapshot mismatch
    - ambiguous market-to-bin mapping
    - station/rules mismatch not verified

  market_quality:
    - spread too wide
    - insufficient depth
    - no recent trades
    - market close too near
    - price moved before bot could act

  risk_limits:
    - daily max loss reached
    - event exposure cap reached
    - correlated exposure too high
    - open order count too high
    - live mode disabled
```

## 9.2 Signal quality score

```yaml
signal_quality_score:
  range: 0_to_1
  components:
    forecast_agreement: 0.25
    live_observation_confirmation: 0.20
    model_calibration_confidence: 0.20
    market_liquidity: 0.15
    bin_boundary_safety: 0.10
    data_freshness: 0.10
  decision_thresholds:
    score_below_0_50: no_trade
    score_0_50_to_0_70: monitor_or_paper_only
    score_above_0_70: eligible_for_trade_if_edge_and_risk_pass
```

## 9.3 Boundary safety

The system should be cautious when the continuous temperature distribution is centered near a bin boundary. For example, if expected max is 87.8F, the `86-87` and `>=88` settlement difference may depend on rounding, station measurement details, or a small late-day move. This should reduce signal quality unless the market price is very wrong.

# 10. Kalshi Market Integration

## 10.1 Market discovery

The system should continuously discover open markets by series ticker, event metadata, and keyword fallbacks. Candidate series tickers should be configurable because Kalshi naming can change.

```yaml
market_discovery:
  primary_method: "GET /markets with series_ticker and status=open"
  fallback_method: "keyword scan for location and temperature market terms"
  required_validation:
    - event date matches target date
    - settlement rules match expected station/location
    - contract titles map cleanly to configured bins
    - all expected bins are present or missing bins are explicitly handled
```

## 10.2 Bin mapping

The market-title parser must convert human-readable Kalshi contract text into normalized bins.

Examples:

```yaml
mapping_examples:
  "84 or 85 degrees": "84-85"
  "88 degrees or above": ">=88"
  "79 degrees or below": "<=79"
  "Between 80 and 81": "80-81"
```

Ambiguous titles must be blocked for manual review.

## 10.3 Market data streaming

Recommended data flow:

1. Fetch REST snapshot for each active market.
2. Open authenticated WebSocket.
3. Subscribe to ticker, trade, orderbook_delta, and lifecycle channels.
4. Rebuild local order books from snapshots plus deltas.
5. Periodically reconcile with REST snapshots.
6. If checksum, sequence, or freshness checks fail, mark market data stale and block trading until rebuilt.

## 10.4 Rate-limit handling

The bot must not blindly poll. It needs:

- Token-budget-aware request scheduling.
- Exponential backoff with jitter.
- REST snapshots only when needed or scheduled.
- WebSocket first for rapid updates.
- Separate queues for market data, account state, and order actions.

# 11. Strategy Logic

## 11.1 Edge calculation

For a YES buy:

```yaml
edge_vs_ask: model_probability - yes_ask - estimated_fees - slippage_buffer - calibration_buffer
```

A trade should only be considered if:

```yaml
trade_gate:
  model_probability: known
  market_yes_ask: known
  edge_after_costs: above_threshold
  signal_quality_score: above_threshold
  liquidity_score: above_threshold
  risk_limits: pass
  market_mapping: verified
  mode: paper_or_live_enabled
```

## 11.2 Example decision logic

```yaml
if signal_quality_score < 0.50:
  action: no_trade
elif mode == paper and edge_after_costs > threshold:
  action: paper_trade
elif mode == live and live_trading_enabled and edge_after_costs > threshold and risk_passes:
  action: live_trade
else:
  action: monitor
```

## 11.3 Position sizing

Use fractional Kelly only as a research reference; live sizing should be much more conservative.

Recommended initial sizing:

```yaml
paper_trading:
  max_contracts_per_trade: 10
  max_event_exposure: 50
  max_daily_loss: 100

live_trading_initial:
  max_contracts_per_trade: 1_to_5
  max_event_exposure: very_small
  max_daily_loss: hard_cap
  require_manual_enable_each_day: true
```

# 12. Paper Trading and Live Trading Modes

## 12.1 Paper trading

Paper trading should simulate:

- Executable bid/ask prices.
- Partial fills.
- Slippage.
- Fees.
- Queue uncertainty.
- Cancel/replace behavior.
- Settlement.

Paper trading should never assume midpoint fills.

## 12.2 Live trading

Live trading should require:

- API credentials present.
- Live mode switched on in dashboard.
- Daily manual enable.
- Small exposure limits.
- Kill switch visible on dashboard.
- Automatic halt if data stale, error rate high, or loss limit hit.
- Full audit log for every order intent and order response.

## 12.3 Button design

The UI should have separate controls:

```yaml
mode_controls:
  data_only:
    description: "No simulated or real orders."
  paper_trading:
    description: "Simulated orders only."
  live_armed:
    description: "Live credentials loaded, but no order unless final confirmation enabled."
  live_trading:
    description: "Live order placement allowed subject to risk gates."
  kill_switch:
    description: "Immediately cancels open orders and blocks new orders."
```

The button should not simply toggle from paper to live without warnings and constraints.

# 13. Home Linux Server Deployment

## 13.1 Recommended hardware

A small Linux server is sufficient because the system is lightweight.

Recommended minimum:

- 4 CPU cores.
- 8-16 GB RAM.
- SSD storage.
- Reliable internet.
- UPS battery backup if live trading.
- Ethernet preferred over Wi-Fi.

## 13.2 Recommended software stack

```yaml
software_stack:
  os: Ubuntu Server LTS or Debian stable
  language: Python 3.11+
  services:
    - Docker Compose
    - PostgreSQL or SQLite for MVP
    - DuckDB / Parquet for research data
    - Redis optional for queues
    - FastAPI backend
    - Streamlit or lightweight React dashboard
    - systemd or Docker restart policies
  observability:
    - structured JSON logs
    - Prometheus optional
    - Grafana optional
    - email/SMS/Discord alerts optional
```

## 13.3 Deployment services

```yaml
docker_compose_services:
  bot_core:
    runs: strategy, risk, execution orchestration
  kalshi_stream:
    runs: websocket ingestion and orderbook state
  weather_worker:
    runs: weather updates and feature generation
  dashboard:
    runs: local UI
  db:
    runs: postgres
  scheduler:
    runs: periodic jobs and daily reports
```

# 14. LLM / Antigravity Development Plan

## 14.1 How Antigravity should build this

Antigravity should not attempt to build the whole system in one pass. It should implement milestones with tests.

```yaml
milestones:
  1_market_data_mvp:
    objective: "Connect to Kalshi demo/public data, discover markets, parse bins, store snapshots."
    tests:
      - bin parser tests
      - market schema tests
      - stale data detection tests

  2_weather_model_mvp:
    objective: "Load historical data, build baseline climatology + forecast input model, output bin probabilities."
    tests:
      - probabilities sum to 1
      - bins map correctly
      - backtest runs chronologically

  3_join_and_dashboard:
    objective: "Show model probabilities vs market prices in dashboard."
    tests:
      - market/prediction join works
      - no ambiguous ticker mapping

  4_paper_trading:
    objective: "Simulate trades from executable prices with logs and settlement."
    tests:
      - no midpoint fill assumption
      - settlement PnL correct
      - risk caps enforced

  5_signal_quality_engine:
    objective: "Block poor-signal days."
    tests:
      - missing weather blocks trading
      - stale websocket blocks trading
      - wide spreads block trading
      - low forecast agreement blocks trading

  6_live_trading_demo_environment:
    objective: "Use demo API or tiny-size live mode with hard caps."
    tests:
      - credentials not logged
      - kill switch works
      - duplicate order prevention

  7_live_trading_limited_release:
    objective: "Enable live trading only after documented paper results."
    tests:
      - daily manual enable required
      - max loss enforced
      - all decisions auditable
```

## 14.2 Recommended prompts for Gemini Deep Research

Use this report as the input and ask Gemini Deep Research:

```text
Research and design a robust local-first quantitative trading system for Kalshi climate / temperature-bin markets. The system should run on a small Linux server, use Python, ingest Kalshi REST/WebSocket market data, ingest weather forecasts and live observations, output calibrated probabilities across discrete temperature bins, run paper trading and live trading behind risk gates, and include an LLM agent for research and maintenance but not unchecked order execution. Focus on architecture, APIs, data schemas, risk controls, no-trade signal quality logic, backtesting, and deployment. Identify failure modes and propose a staged build plan suitable for Antigravity IDE with Gemini 3.1 Pro High as the coding agent.
```

Follow-up research questions:

```text
1. What are the best public or low-cost weather APIs for real-time station-level daily high prediction near Kalshi settlement stations?
2. How should a model calibrate probability distributions over discrete temperature bins at T-24h, T-12h, T-6h, T-3h, and T-1h?
3. What is the correct way to reconstruct Kalshi order books from REST snapshots and WebSocket deltas?
4. How should fees, spreads, partial fills, and slippage be modeled in Kalshi paper trading?
5. What risk controls are appropriate for small-account prediction-market trading bots?
6. How can an LLM agent safely review logs and propose code changes without directly bypassing deterministic trading gates?
```

# 15. Backtesting Plan

## 15.1 Weather backtest

Backtest must be chronological, not random-split.

Evaluate by horizon:

- T-48h
- T-24h
- T-12h
- T-6h
- T-3h
- T-1h

Metrics:

- Bin log loss.
- Brier score.
- Calibration by bin.
- Upper-tail calibration.
- Accuracy of top bin.
- Probability assigned to realized bin.
- Error around boundaries.

## 15.2 Trading backtest

Market data backtest should use historical Kalshi prices when available. If full historical order books are unavailable, separate weather backtest from trading simulation and do not overstate results.

Trading metrics:

- Net PnL after fees.
- ROI on capital at risk.
- Maximum drawdown.
- Hit rate by edge bucket.
- Calibration of model edge vs realized returns.
- Number of no-trade days.
- Performance by horizon.
- Performance by market liquidity.
- Performance by weather regime.

# 16. Daily Operating Workflow

```yaml
daily_workflow:
  morning:
    - discover active Kalshi markets
    - verify bin mapping and settlement rules
    - fetch weather forecasts
    - generate initial probabilities
    - set mode to data_only or paper by default

  intraday:
    - update live weather observations
    - update probabilities
    - stream Kalshi order books and trades
    - recalculate edge
    - apply signal quality and risk gates
    - paper or live trade only if all gates pass

  pre_close:
    - increase caution near settlement/close
    - block trades if orderbook or weather data stale
    - reduce order size or stop new entries if uncertainty remains high

  post_settlement:
    - fetch result
    - settle paper positions
    - reconcile live positions
    - compute forecast error and trading PnL
    - produce LLM-readable daily postmortem
```

# 17. Critical Safety Requirements

## 17.1 Secrets

- Never store API private keys in git.
- Never display secrets in dashboard logs.
- Use `.env` only locally and add it to `.gitignore`.
- Prefer encrypted local secret storage for live keys.
- Use separate demo and production credentials.

## 17.2 Execution controls

- Live trading disabled by default.
- Manual enable required each day.
- Kill switch always visible.
- Maximum loss enforced in code, not just UI.
- No trading if any required data source is stale.
- No trading if market mapping is ambiguous.
- No trading if orderbook reconstruction is invalid.
- No trading after repeated API errors.

## 17.3 LLM controls

- LLM cannot modify risk limits without explicit human approval.
- LLM cannot directly place orders.
- LLM suggestions must be written to review files or pull requests.
- LLM-generated code must pass tests before deployment.
- Production service should run pinned, reviewed code only.

# 18. Improvement Ideas

## 18.1 Forecasting improvements

- Add multiple weather forecast providers.
- Learn provider bias by city, season, and horizon.
- Add live observation nowcasting.
- Add sea-breeze/storm/cloud regime features for Miami.
- Train separate models for high-uncertainty weather regimes.
- Build an upper-tail specialist model for >=88F style bins.
- Calibrate probabilities separately by horizon.
- Track probability drift during the day.

## 18.2 Trading improvements

- Use edge thresholds that vary by signal quality.
- Require stronger edge for wider spreads.
- Avoid trading when the model probability distribution is too flat.
- Trade smaller when near bin boundaries.
- Track market-implied probabilities as a sanity check.
- Compare model vs market over time to identify when the market is consistently better.
- Use alerts for human review before live mode.

## 18.3 System improvements

- Add a local dashboard.
- Add daily Markdown/HTML reports.
- Add replay mode for historical events.
- Add a synthetic exchange simulator for testing.
- Add Docker Compose deployment.
- Add structured logs and health checks.
- Add unit tests for every safety-critical function.

# 19. Definition of Done

The system is ready for paper trading when:

```yaml
paper_ready:
  - Kalshi market discovery works reliably
  - bin mapping is verified or manually overridden
  - weather model emits valid calibrated probabilities
  - dashboard shows probability vs market price
  - paper orders use executable bid/ask assumptions
  - logs and postmortems are generated
  - no-trade engine blocks stale and ambiguous cases
```

The system is ready for limited live testing only when:

```yaml
limited_live_ready:
  - paper trading has run for a meaningful sample
  - backtest and paper results are documented
  - risk limits are enforced by tests
  - kill switch is tested
  - credentials are safely stored
  - live mode requires manual daily activation
  - duplicate orders are prevented
  - order reconciliation works
  - maximum daily loss is tiny and hard-coded
```

# 20. Final Recommendation

Build this as a deterministic quant system with an LLM research and operations layer, not as an unconstrained LLM trader. The most important upgrade is moving from single-bin predictions to calibrated probability distributions with no-trade logic. The second most important upgrade is market-data reliability: robust Kalshi market discovery, verified bin mapping, WebSocket orderbook updates, REST reconciliation, and strict stale-data blocks. The third most important upgrade is safety: paper trading by default, live trading only by deliberate enablement, and risk controls that the LLM cannot bypass.

The system can absolutely be built on a small Linux server using Antigravity and Gemini 3.1 Pro High as the main builder/agent. The right architecture is modular, schema-first, test-heavy, and conservative about live execution.


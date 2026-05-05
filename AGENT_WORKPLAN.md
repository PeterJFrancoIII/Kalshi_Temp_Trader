---
---

## `AGENT_WORKPLAN.md`

```markdown
# Multi-Agent Build Workplan

## Shared Root

/Users/computer/Desktop/App Development/Kalshi

## Required Reading for Every Agent

- MASTER_CONTEXT.md
- CODE_GOVERNANCE.md
- DATA_SOURCES.md
- WEATHER_MODEL_SPEC.md

## Agent Ownership

### Agent 1 — Project Architect
Owns:
- repo structure
- shared types
- README
- environment config
- architecture docs

### Agent 2 — CLIMIA Ingestion
Owns:
- backend/src/ingestion/climia_fetcher.py
- backend/src/ingestion/climia_parser.py
- backend/tests/test_climia_parser.py

### Agent 3 — Live KMIA Observations
Owns:
- backend/src/ingestion/kmia_live_fetcher.py
- backend/src/ingestion/kmia_obhistory_parser.py
- backend/src/features/live_features.py
- backend/tests/test_kmia_live_parser.py

### Agent 4 — Forecast Guidance
Owns:
- backend/src/ingestion/nws_forecast_fetcher.py
- backend/src/features/forecast_features.py
- backend/tests/test_forecast_features.py

### Agent 5 — Forecasting Engine
Owns:
- backend/src/forecasting/rules_model.py
- backend/src/forecasting/bin_converter.py
- backend/tests/test_temperature_bins.py

### Agent 6 — LLM Review
Owns:
- backend/src/llm/prompts/kmia_daily_high_review.md
- backend/src/llm/llm_reviewer.py
- backend/src/llm/consensus.py
- backend/tests/test_llm_output_schema.py

### Agent 7 — Kalshi Read-Only Integration
Owns:
- backend/src/kalshi/client.py
- backend/src/kalshi/market_discovery.py
- backend/src/kalshi/orderbook.py
- backend/src/kalshi/weather_market_mapper.py
- backend/tests/test_kalshi_market_mapping.py

### Agent 8 — Recommendation / EV
Owns:
- backend/src/recommendation/ev.py
- backend/src/recommendation/gates.py
- backend/src/recommendation/recommender.py
- backend/tests/test_ev_logic.py

### Agent 9 — Database and Calibration
Owns:
- backend/src/db/models.py
- backend/src/calibration/metrics.py
- backend/src/calibration/reports.py
- backend/tests/test_calibration_metrics.py
- docs/database_schema.md

### Agent 10 — Dashboard
Owns:
- frontend/ (Streamlit/Python future MVP dashboard, NO React)

### Agent 11 — Scheduler and Ops
Owns:
- backend/src/scheduler/jobs.py
- backend/src/scheduler/run_daily_prediction.py
- backend/src/scheduler/settlement_check.py
- scripts/

### Agent 12 — QA and Integration
Owns:
- integration tests
- end-to-end smoke tests
- test fixtures
- docs/testing_plan.md

---

# MVP Lockdown — KMIA Predictor

## Purpose
The KMIA Predictor MVP is now operationally locked for research, daily dry-run forecasting, and paper evaluation. This lockdown ensures the stability of the core climatology-based models and verification pipelines while preventing the introduction of unapproved trading logic.

## Locked MVP Scope
The system is restricted to read-only data ingestion and simulated evaluation. No changes to the core forecasting models or data-handling constraints are permitted without a formal architecture review.

## What the system does
- **Live Ingestion**: Ingests NWS KMIA sensor data and Kalshi market snapshots (read-only).
- **Forecasting**: Generates daily maximum temperature probability bins using Climatology (Rules V2) and Rule-based (Rules V1) models.
- **Comparison**: Evaluates model performance side-by-side using Brier scores and hit rates.
- **Settlement**: Reconciles forecasts against official CLIMIA reports (dry-run).
- **Calibration**: Aggregates performance metrics over time to track model accuracy.
- **Paper Trading**: Simulates hypothetical trade recommendations and tracks PnL based on market snapshots.
- **Reporting**: Generates daily status dashboards (JSON/MD) and workflow logs.

## What the system explicitly does not do
- **Real Trading**: It does NOT place real-money orders.
- **Authentication**: It does NOT handle Kalshi API keys or private credentials for trading.
- **Automatic Execution**: It does NOT have any automated execution path for financial transactions.
- **Market Impact**: It does NOT interact with market liquidity.

## Safe-to-run commands
- `bash scripts/run_tests.sh`: Executes the full verification suite.
- `bash scripts/run_kmia_daily_workflow.sh`: Orchestrates the daily forecast, comparison, settlement, and calibration sequence.
- `bash scripts/generate_daily_status.sh`: Produces the latest system health and forecast summary.
- `./scripts/run_daily_prediction.sh --dry-run --model rules_v2_climatology`: Runs a specific model dry-run.
- `./scripts/run_daily_prediction.sh --dry-run --compare-models`: Runs a v1/v2 comparison.
- `bash scripts/settle_yesterday.sh`: Checks settlement for the previous day.
- `bash scripts/generate_weekly_calibration.sh`: Updates the aggregate calibration report.

## Generated outputs
- `backend/data/processed/reports/`: Detailed forecast and comparison MD/HTML files.
- `backend/data/processed/logs/`: Daily workflow execution logs.
- `backend/data/processed/status/`: Daily system status JSON and Markdown summaries.
- `backend/data/processed/aggregate_calibration/`: Long-term model performance metrics.
- `backend/data/processed/history/kmia_daily_history.jsonl`: The canonical historical climatology dataset.

## Data sources
- **CLIMIA**: Official NOAA/NWS daily climate reports for KMIA.
- **NWS ObHistory**: Live hourly sensor data for real-time maximum temperature tracking.
- **Kalshi Public API**: Read-only market price and orderbook data.

## Forecast models
- **Rules V1**: Hard-coded heuristics based on NWS forecasts and physical limits.
- **Rules V2 (Climatology)**: Distribution-based model using the 27,879-record KMIA historical dataset.

## Calibration and paper evaluation
The system uses **Brier Score**, **Log Loss**, and **Top-Bin Hit Rate** as primary metrics. Paper trading simulates fills at market ask prices and settles them against observed high temperatures to evaluate potential ROI.

## Safety rules
- **Strict Read-Only**: The Kalshi integration must remain read-only.
- **No Order Logic**: Implementation of `create_order`, `submit_order`, or similar execution functions is strictly forbidden.
- **Simulation-Only**: Paper trading must rely solely on local simulation files (`.jsonl`).
- **Path-Safe Execution**: Scripts must handle paths with spaces and use virtual environments to ensure environment isolation.

## Forbidden changes without architecture review
- Modification of the `KMIA_DAILY_HISTORY` canonical file.
- Changes to the probability binning logic (REQUIRED_BINS).
- Introduction of external trading libraries or authenticated API clients.
- Altering the safety-grep verification checks in the test suite.

## Current readiness statement
- **Ready for automated dry-run forecasting**: YES
- **Ready for paper evaluation**: YES
- **Ready for real trading**: NO

> [!IMPORTANT]
> The current MVP is locked as a research and paper-evaluation system only.

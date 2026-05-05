# KMIA Operational Loop Documentation

This document describes the automated daily prediction and reporting workflow for the KMIA temperature forecasting system.

## Overview

The operational loop is responsible for:
1. Fetching live sensor data and forecasts.
2. Generating probability distributions for daily maximum temperatures.
3. Creating human-readable reports (Markdown and HTML).
4. Storing predictions for future calibration and settlement.

## Core Components

- **`backend/src/scheduler/run_daily_prediction.py`**: The main orchestration script.
- **`backend/src/scheduler/jobs.py`**: Scheduled tasks and loop management.
- **`backend/data/processed/reports/`**: Destination for generated reports.
- **`backend/data/processed/history/kmia_daily_history.jsonl`**: Historical data for climatology-based models.

## Usage

### Running a Manual Prediction

To run a prediction for today (uses default model: `rules_v2_climatology`):
```bash
./scripts/run_daily_prediction.sh
```

To run a dry run (uses mock data, no database required):
```bash
./scripts/run_daily_prediction.sh --dry-run
```

To run for a specific date:
```bash
./scripts/run_daily_prediction.sh --date 2026-05-03
```

### Model Selection

The system supports multiple forecasting models:
- **`rules_v1`**: Original rules-based heuristic model.
- **`rules_v2_climatology`** (Default): Combined model integrating 30-year seasonal climatology with forecast centering and weather suppression.

To select a model:
```bash
./scripts/run_daily_prediction.sh --model rules_v1
```

### Comparison Mode

To run both models side-by-side and generate a comparison report:
```bash
./scripts/run_daily_prediction.sh --compare-models
```
This will generate individual model reports plus a `kmia_comparison_YYYY-MM-DD_HHMMSS.md/html` summary.

## Historical Data Integration (v2)

Model v2 relies on the canonical historical data located at `backend/data/processed/history/kmia_daily_history.jsonl`. 
This file contains the full 27,879-record KMIA climatology.

**Protection Policy**:
- This file is READ-ONLY for all forecasting and testing processes.
- Tests must use synthetic fixtures (e.g., in `backend/data/processed/history/fixtures/`) rather than modifying the canonical file.

If this file is missing, the system will:
1. Log a warning.
2. Use fallback behavior (uniform-like prior) for the climatology component.
3. Continue execution without crashing.

## Automation

The `jobs.py` script can be run as a service to manage the daily loop:
```bash
python3 -m src.scheduler.jobs --loop
```

## Reports

Each run generates files in `backend/data/processed/reports/`:
- `kmia_forecast_YYYY-MM-DD_[MODEL]_HHMMSS.md`: Structured Markdown report.
- `kmia_forecast_YYYY-MM-DD_[MODEL]_HHMMSS.html`: Visual HTML dashboard.
- `kmia_comparison_YYYY-MM-DD_HHMMSS.md/html`: (Optional) Side-by-side comparison.

## Testing

The operational loop is verified by:
```bash
bash scripts/run_tests.sh
```
Or specifically:
```bash
pytest backend/tests/test_daily_prediction_loop.py
```

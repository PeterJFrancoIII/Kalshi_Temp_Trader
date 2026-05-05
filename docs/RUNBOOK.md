# KMIA Predictor Runbook

## Daily operating model
The KMIA Predictor is designed to run once daily after the NWS high temperature observation is finalized and the next day's Kalshi markets are active. The primary orchestration is handled by a single shell script that executes the full data ingestion, forecasting, and calibration loop.

## Manual daily run
To execute the complete daily workflow, run:
```bash
bash scripts/run_kmia_daily_workflow.sh
```
This script will:
1. Generate a Rules V2 forecast dry-run.
2. Generate a model comparison (V1 vs V2).
3. Check settlement for yesterday's high temperature.
4. Update the aggregate calibration reports.
5. Generate the final Daily Status Report.

## Manual status generation
If you need to refresh only the status dashboard without re-running the whole workflow:
```bash
bash scripts/generate_daily_status.sh
```

## Test command
Always run the test suite after any configuration or environment changes:
```bash
bash scripts/run_tests.sh
```

## Expected output paths
- **Status Dashboard**: `backend/data/processed/status/kmia_daily_status_YYYY-MM-DD.md`
- **Detailed Reports**: `backend/data/processed/reports/`
- **Workflow Logs**: `backend/data/processed/logs/kmia_daily_workflow_YYYY-MM-DD.log`
- **Calibration Data**: `backend/data/processed/aggregate_calibration/aggregate_calibration.json`

## How to read the daily status report
The `kmia_daily_status_*.md` report provides a high-level overview:
- **Safety Status**: Should always be `SECURE`.
- **Latest Outputs**: Links to the specific forecast and comparison files generated today.
- **Calibration Summary**: Shows the average accuracy (Brier Score) of both models.
- **Operational Status**: Confirms if the workflow completed successfully and if paper trading data is available.

## How to read aggregate calibration
Open `backend/data/processed/aggregate_calibration/aggregate_calibration.md`. It tracks the "Win Rate" of Model V2 vs V1 based on accuracy metrics. A lower Brier Score indicates a better forecast.

## How to check logs
If the workflow fails, inspect the latest log in `backend/data/processed/logs/`. Logs capture all stdout/stderr from the underlying Python scripts.

## How to verify history file
The canonical history is at `backend/data/processed/history/kmia_daily_history.jsonl`.
- **Expected Record Count**: 27,879
- **Validation**: Use `python3 backend/tests/test_climia_backfill.py` to verify data integrity.

## How to troubleshoot common failures

### missing .venv dependencies
- **Symptom**: `ModuleNotFoundError` or `python3: command not found`.
- **Fix**: Re-run the installation steps:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r backend/requirements.txt
  ```

### run_tests.sh fails
- **Symptom**: `ALL TESTS PASSED` is missing from output.
- **Fix**: Check which specific test failed. If it's a `SafetyViolation`, ensure no forbidden trading terms were added to the code.

### daily workflow fails
- **Symptom**: `Workflow Completed` marker missing from log.
- **Fix**: Check `backend/data/processed/logs/`. Often caused by network timeouts when fetching NWS or Kalshi data. Re-run the script.

### history file missing or too small
- **Symptom**: Climatology model reports "0 records loaded".
- **Fix**: Ensure `kmia_daily_history.jsonl` is present in `backend/data/processed/history/`. Do not use the 15-record sample fixture for production runs.

### status report missing
- **Symptom**: `scripts/generate_daily_status.sh` finishes but no file is created in `status/`.
- **Fix**: Ensure the `reports/` and `logs/` directories contain files for today's date. The generator relies on file discovery.

### CLIMIA not yet available
- **Symptom**: Settlement check logs "Warning: CLIMIA report not found for date".
- **Fix**: CLIMIA reports are often released with a 24-48 hour lag. The settlement script will gracefully skip until data is available.

### aggregate calibration has zero settled days
- **Symptom**: Calibration report shows all zeros.
- **Fix**: This is normal until at least one day has been successfully settled (both a forecast and a CLIMIA observation exist for the same date).

### warning in workflow log
- **Symptom**: Log contains `WARNING`.
- **Fix**: Inspect the warning. Common warnings include "Stale sensor data" or "Incomplete NWS table". Usually safe to ignore if the forecast still completes.

### safety grep finds a suspicious term
- **Symptom**: `run_tests.sh` fails with safety error.
- **Fix**: Remove any implementation of `create_order`, `submit_order`, or other forbidden execution terms from `backend/src/`.

# KMIA Predictor — Daily Operations Checklist

Use this checklist to ensure the system is running correctly and remains within safety bounds.

## 1. Pre-Run
- [ ] Virtual environment is active (`source .venv/bin/activate`).
- [ ] Internet connection is stable (required for NWS and Kalshi data).
- [ ] Canonical history file is present (`backend/data/processed/history/kmia_daily_history.jsonl`).

## 2. Execution
- [ ] Run the full daily workflow:
  ```bash
  bash scripts/run_kmia_daily_workflow.sh
  ```
- [ ] Ensure the workflow completes with Step 5/5.
- [ ] (Optional) Manually refresh status if needed:
  ```bash
  bash scripts/generate_daily_status.sh
  ```

## 3. Inspection
- [ ] **Daily Status**: Open `backend/data/processed/status/kmia_daily_status_YYYY-MM-DD.md`.
  - [ ] Safety Status is `SECURE`.
  - [ ] Daily Workflow is `SUCCESS`.
- [ ] **Forecast Quality**: Check today's forecast report in `backend/data/processed/reports/`.
  - [ ] Are the probability bins reasonable for the current season?
  - [ ] Does the model reflect current live observations?
- [ ] **Workflow Logs**: Scan `backend/data/processed/logs/kmia_daily_workflow_YYYY-MM-DD.log` for errors.

## 4. Calibration & Evaluation
- [ ] **Settlement**: Has yesterday's forecast been settled?
  - [ ] Check if `settle_yesterday.sh` found a valid CLIMIA report.
- [ ] **Weekly Calibration**: Review `backend/data/processed/aggregate_calibration/aggregate_calibration.md`.
  - [ ] Is Model V2 outperforming V1?
- [ ] **Paper Trading**: Review `backend/data/processed/status/` for paper trading availability.
  - [ ] If trades were recorded, are the PnL figures accurate?

## 5. Safety & Compliance
- [ ] Run the test suite:
  ```bash
  bash scripts/run_tests.sh
  ```
- [ ] Verify that **all tests pass**.
- [ ] Ensure no new `create_order` or `place_order` functions were added to the codebase.
- [ ] Run a manual safety scan:
  ```bash
  grep -rnE "create_order|submit_order|cancel_order|place_order|market_order|private key|API key|ENABLE_REAL_TRADING" backend/src/
  ```
  *(Result should be empty)*.

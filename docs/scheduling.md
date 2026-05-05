# Scheduling and Operations

This document outlines the daily operational workflow for the KMIA temperature prediction system and provides examples for automated scheduling using `cron`.

## Daily Workflow Orchestrator

The system includes a central orchestrator script that runs the standard daily sequence:
`scripts/run_kmia_daily_workflow.sh`

### What it does:
1.  **Daily V2 Forecast (Dry-Run)**: Generates the latest probability distribution using the climatology-blended model.
2.  **Model Comparison (Dry-Run)**: Generates side-by-side reports for Rules V1 vs. Rules V2.
3.  **Settlement Check**: Reconciles yesterday's forecast against official NWS CLIMIA reports.
4.  **Aggregate Calibration**: Updates the long-term scoring and calibration reports.

### Safety Note
> [!IMPORTANT]
> **NO REAL TRADING EXECUTION**. This workflow is strictly for research, simulation, and calibration. No orders are placed on Kalshi. All forecasting and settlement checks are performed in dry-run mode.

## Manual Execution

To run the full daily workflow manually from the project root:
```bash
bash scripts/run_kmia_daily_workflow.sh
```

Logs are automatically saved to:
`backend/data/processed/logs/kmia_daily_workflow_YYYY-MM-DD.log`

## Scheduling with Cron

To automate these tasks on a Linux/macOS system, you can use `crontab`. Below are suggested schedules.

### Suggested Schedule

| Task | Suggested Time | Purpose |
| :--- | :--- | :--- |
| **Morning Forecast** | 07:00 AM ET | Initial forecast for the day based on morning guidance. |
| **Midday Refresh** | 12:30 PM ET | Update forecast with mid-day observations and updated NWS guidance. |
| **Post-Settlement** | 07:30 PM ET | Final check once today's high is likely reached and CLIMIA is available. |
| **Weekly Review** | Sun 08:00 PM ET | Comprehensive calibration review of the past week. |

### Crontab Examples

Open your crontab editor:
```bash
crontab -e
```

Add entries (adjust paths to your absolute project location):

```cron
# KMIA Daily Workflow (Morning, Midday, Evening)
0 7 * * * /bin/bash /path/to/Kalshi/scripts/run_kmia_daily_workflow.sh
30 12 * * * /bin/bash /path/to/Kalshi/scripts/run_kmia_daily_workflow.sh
30 19 * * * /bin/bash /path/to/Kalshi/scripts/run_kmia_daily_workflow.sh
```

## Troubleshooting

- **Venv Issues**: Ensure the `.venv` directory exists at the project root. The scripts automatically detect and use it.
- **Path Spaces**: The scripts are designed to be space-safe, but it is recommended to avoid spaces in the project path if possible for maximum compatibility with third-party tools.
- **Settlement Missing**: NWS CLIMIA reports may be delayed. If `settle_yesterday.sh` fails to find a report, it will log the failure and the workflow will continue.
- **Permission Denied**: Ensure the scripts are executable: `chmod +x scripts/*.sh`.

## Output Directories

- **Forecasts**: `backend/data/processed/reports/`
- **Comparisons**: `backend/data/processed/comparisons/`
- **Aggregate Scoring**: `backend/data/processed/aggregate_calibration/`
- **Logs**: `backend/data/processed/logs/`

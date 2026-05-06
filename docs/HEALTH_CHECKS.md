# Health Checks

This document describes how to monitor the health of the KMIA Kalshi bot.

## NO REAL TRADING EXECUTION

This project is for **DRY-RUN / PAPER EVALUATION ONLY**. No real trading execution is performed.

## Health Summary Script

The health summary script provides a quick overview of the system status.

### How to Run

```bash
bash scripts/health_summary.sh
```

### Status Indicators

The script outputs a color-coded status at the end:

- **GREEN**: Everything is running correctly. The web console is active, HTTP 200 is returned, and all required data files (status, forecast, snapshots) exist and are populated.
- **YELLOW**: The system is partially functional. The web console is active, but some non-critical data might be missing (e.g., zero markets found in the latest snapshot, or missing calibration files).
- **RED**: Critical failure. The web console is inactive, HTTP checks failed, or essential files like the daily status or forecast report are missing.

### Read-Only Nature

The health check script is strictly **read-only**. It does not modify any files, restart services, or execute any trading orders.

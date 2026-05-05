# Linux Deployment Guide — KMIA Predictor

## Infrastructure
- **Server**: hal.taild0730.ts.net
- **Deployment Path**: `/opt/kmia-kalshi`
- **Tailscale/SSH**: Ensure you have Tailscale active to reach the `.ts.net` address.

## Prerequisites
- **Python**: 3.11 or higher recommended.
- **Systemd**: Required for automated background jobs.
- **Network**: The server must have outbound internet access for NWS and Kalshi data.

## Initial Setup
Run the following from the repository root on the Linux server:
```bash
bash scripts/linux_setup.sh
```

## Manual Commands
Once setup, you can run these commands from `/opt/kmia-kalshi`:
- **Run Tests**: `bash scripts/run_tests.sh`
- **Daily Workflow**: `bash scripts/run_kmia_daily_workflow.sh`
- **Generate Status**: `bash scripts/generate_daily_status.sh`
- **Health Check**: `bash scripts/health_check.sh`

## Virtual Environment
The system uses a virtual environment at `/opt/kmia-kalshi/.venv`. To activate manually:
```bash
source /opt/kmia-kalshi/.venv/bin/activate
```

## Service Management (Systemd)
The following timers are installed:
- `kmia-daily-workflow.timer`: Runs at 07:00, 12:30, and 19:30.
- `kmia-status.timer`: Runs every 6 hours.
- `kmia-health-check.timer`: Runs every 6 hours.

Manage them with:
```bash
sudo systemctl status kmia-daily-workflow.timer
sudo systemctl list-timers | grep kmia
```

## Logs and Status
- **Workflow Logs**: `backend/data/processed/logs/`
- **Health Logs**: `backend/data/processed/logs/health_check_latest.log`
- **Status Reports**: `backend/data/processed/status/`

## Rollback
1. Stop the timers: `sudo systemctl stop kmia-*.timer`
2. Revert to a previous stable `git` commit or `rsync` backup.
3. Restart the timers.

## Safety Note
> [!IMPORTANT]
> This deployment is strictly **DRY-RUN / PAPER-EVALUATION ONLY**. 
> Real trading execution is NOT implemented. Kalshi integration is read-only.

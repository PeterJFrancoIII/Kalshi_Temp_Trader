#!/usr/bin/env bash
set -euo pipefail

# run_kmia_daily_workflow.sh
# Orchestrates daily forecasting dry-run, settlement check, and aggregate calibration.
# NO REAL TRADING EXECUTION included.

# Path-safe script directory discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
LOG_DIR="$BACKEND_DIR/data/processed/logs"
DATE_STR="$(date +%Y-%m-%d)"
LOG_FILE="$LOG_DIR/kmia_daily_workflow_$DATE_STR.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Redirect stdout and stderr to both log file and console
exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================================================"
echo "KMIA Daily Workflow Started: $(date)"
echo "Project Root: $PROJECT_ROOT"
echo "NO REAL TRADING EXECUTION"
echo "========================================================================"

# 1. Run daily v2 dry-run forecast
echo "[1/4] Running daily v2 dry-run forecast..."
bash "$SCRIPT_DIR/run_daily_prediction.sh" --dry-run --model rules_v2_climatology

# 2. Run compare-models dry-run
echo "[2/4] Running model comparison dry-run..."
bash "$SCRIPT_DIR/run_daily_prediction.sh" --dry-run --compare-models

# 3. Run settlement check
echo "[3/4] Running settlement check..."
bash "$SCRIPT_DIR/settle_yesterday.sh"

# 4. Run paper signal generator
echo "[4/6] Generating paper trading signals..."
bash "$SCRIPT_DIR/generate_paper_signal.sh"

# 5. Run aggregate calibration report
echo "[5/6] Generating weekly/aggregate calibration report..."
bash "$SCRIPT_DIR/generate_weekly_calibration.sh"

# 6. Generate Daily Status Report
echo "[6/6] Generating Daily Status Report..."
# Use venv if available
if [ -x "$PROJECT_ROOT/.venv/bin/python3" ]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
elif [ -x "$BACKEND_DIR/venv/bin/python3" ]; then
  PYTHON_BIN="$BACKEND_DIR/venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

export PYTHONPATH="${PYTHONPATH:-}:$BACKEND_DIR/src"
"$PYTHON_BIN" -m scheduler.generate_daily_status

echo "========================================================================"
echo "KMIA Daily Workflow Completed: $(date)"
echo "Workflow Log: $LOG_FILE"
echo "========================================================================"

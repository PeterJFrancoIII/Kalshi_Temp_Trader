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

# 0. Fetch latest Kalshi markets
echo "Fetching latest Kalshi markets..."
if bash "$SCRIPT_DIR/fetch_kalshi_markets.sh"; then
  echo "Kalshi market fetch completed successfully."
else
  echo "WARNING: Kalshi market fetch failed. Continuing workflow using existing or empty snapshot in restricted no-trade mode."
fi

# 1. Identify target dates from Kalshi snapshot
echo "Identifying target dates from Kalshi snapshot..."
if [ -x "$PROJECT_ROOT/.venv/bin/python3" ]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

SNAPSHOT_PATH="$BACKEND_DIR/data/processed/kalshi_market_snapshots/latest_kalshi_market_snapshot.json"
TARGET_DATES=$("$PYTHON_BIN" -c "
import json
import os
import re
from datetime import datetime

def parse_ticker_date(ticker):
    if not ticker: return None
    match = re.search(r'([0-9]{2})([A-Z]{3})([0-9]{2})', ticker)
    if not match: return None
    yy, mon_str, dd = match.groups()
    months = {'JAN':'01','FEB':'02','MAR':'03','APR':'04','MAY':'05','JUN':'06','JUL':'07','AUG':'08','SEP':'09','OCT':'10','NOV':'11','DEC':'12'}
    mm = months.get(mon_str.upper())
    return f'20{yy}-{mm}-{dd}' if mm else None

snapshot_path = '$SNAPSHOT_PATH'
if not os.path.exists(snapshot_path):
    print(datetime.now().strftime('%Y-%m-%d'))
    exit()

with open(snapshot_path, 'r') as f:
    data = json.load(f)
markets = data.get('markets', []) or data.get('selected_temperature_markets', [])
dates = sorted(list(set(filter(None, [parse_ticker_date(m.get('ticker')) for m in markets]))))
print(' '.join(dates) if dates else datetime.now().strftime('%Y-%m-%d'))
")

echo "Found target dates: $TARGET_DATES"

# 2. Run daily v2 dry-run forecast for each date
echo "[1/4] Running daily v2 dry-run forecast for active dates..."
for TARGET_DATE in $TARGET_DATES; do
    echo "  Generating forecast for $TARGET_DATE..."
    bash "$SCRIPT_DIR/run_daily_prediction.sh" --dry-run --model rules_v2_climatology --date "$TARGET_DATE"
done

# 3. Run compare-models dry-run (Legacy: today only)
echo "[2/4] Running model comparison dry-run for today..."
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

# 6. Run paper signal recorder
echo "[6/7] Recording paper trades from latest signals..."
bash "$SCRIPT_DIR/record_paper_trade.sh"

# 7. Generate Daily Status Report
echo "[7/7] Generating Daily Status Report..."
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

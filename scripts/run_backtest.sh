#!/bin/bash
# NO REAL TRADING EXECUTION
set -e

# Resolve directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run 'python3 -m venv .venv' and install requirements."
    exit 1
fi

export PYTHONPATH="$ROOT_DIR/backend/src"

START_DATE=${1:-$(date -d "7 days ago" +%Y-%m-%d)}
END_DATE=${2:-$(date +%Y-%m-%d)}

echo "Running Kalshi Temp Trader Backtest..."
echo "Start Date: $START_DATE"
echo "End Date: $END_DATE"

# We run the Python module directly if we have a CLI, or we can use python -c.
# Let's execute the coordinator module if we implement it as executable.
.venv/bin/python -c "
from backtesting.coordinator import BacktestCoordinator
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

coord = BacktestCoordinator(start_date='$START_DATE', end_date='$END_DATE')
coord.run_backtest()
"

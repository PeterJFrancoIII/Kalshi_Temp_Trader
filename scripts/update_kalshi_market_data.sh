#!/bin/bash
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

set -euo pipefail

# Safely find project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "--- Updating Kalshi Market Data ---"

# Select virtual environment
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    VENV_PATH="$PROJECT_ROOT/.venv"
elif [ -x "$PROJECT_ROOT/backend/venv/bin/python" ]; then
    VENV_PATH="$PROJECT_ROOT/backend/venv"
else
    echo "ERROR: No virtual environment found."
    exit 1
fi

source "$VENV_PATH/bin/activate"
export PYTHONPATH="${PYTHONPATH:-}:$PROJECT_ROOT/backend/src"

# Run updater
python3 -m market_data.update_kalshi_snapshots

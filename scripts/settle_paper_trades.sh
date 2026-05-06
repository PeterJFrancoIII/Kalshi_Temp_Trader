#!/bin/bash

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

set -e

# Resolution of Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use .venv if present
if [ -d "$ROOT_DIR/.venv" ]; then
    PYTHON="$ROOT_DIR/.venv/bin/python3"
elif [ -d "$ROOT_DIR/backend/venv" ]; then
    PYTHON="$ROOT_DIR/backend/venv/bin/python3"
else
    PYTHON="python3"
fi

export PYTHONPATH="$ROOT_DIR/backend/src:$PYTHONPATH"

echo "===================================================="
echo "         KMIA PAPER TRADE SETTLEMENT"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="

"$PYTHON" "$ROOT_DIR/backend/src/paper_trading/settlement.py"

echo "----------------------------------------------------"
echo "Performance Summary:"
cat "$ROOT_DIR/backend/data/processed/paper_trading/latest_paper_trading_performance.json"
echo "===================================================="

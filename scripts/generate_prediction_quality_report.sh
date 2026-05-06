#!/bin/bash

# NO REAL TRADING EXECUTION
# PAPER EVALUATION ONLY

set -e

# Resolve project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Set PYTHONPATH to include backend/src
export PYTHONPATH="$ROOT_DIR/backend/src:$PYTHONPATH"

# Use virtual environment if it exists
if [ -d "$ROOT_DIR/.venv" ]; then
    VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
elif [ -d "$ROOT_DIR/backend/venv" ]; then
    VENV_PYTHON="$ROOT_DIR/backend/venv/bin/python"
else
    VENV_PYTHON="python3"
fi

echo "--- Generating Daily Prediction Quality Report ---"
echo "Project Root: $ROOT_DIR"
echo "Using Python: $VENV_PYTHON"
echo "Safety: NO REAL TRADING EXECUTION"

"$VENV_PYTHON" "$ROOT_DIR/backend/src/paper_trading/prediction_quality.py"

echo "Report Generation Complete."

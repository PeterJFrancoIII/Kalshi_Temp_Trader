#!/bin/bash
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

set -e

PROJECT_ROOT="/opt/kmia-kalshi"
# If running locally on Mac, adjust root
if [[ "$OSTYPE" == "darwin"* ]]; then
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

cd "$PROJECT_ROOT"

# Activate venv
if [ -d "backend/venv" ]; then
    source backend/venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT/backend/src"

echo "Generating Daily Learning Summary..."
python3 backend/src/paper_trading/learning.py

echo "Done."

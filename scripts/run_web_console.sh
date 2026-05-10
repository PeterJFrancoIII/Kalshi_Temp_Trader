#!/bin/bash
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

set -euo pipefail

# run_web_console.sh - Launch the KMIA Predictor Web Console

# Safely find project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "--- KMIA Weather Market Console ---"
echo "Initializing environment..."

# Select virtual environment
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    VENV_PATH="$PROJECT_ROOT/.venv"
elif [ -x "$PROJECT_ROOT/backend/venv/bin/python" ]; then
    VENV_PATH="$PROJECT_ROOT/backend/venv"
else
    echo "ERROR: No virtual environment found at .venv or backend/venv."
    echo "Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt"
    exit 1
fi

source "$VENV_PATH/bin/activate"

# Configuration with overrides
STREAMLIT_ADDRESS="${STREAMLIT_ADDRESS:-127.0.0.1}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

export PYTHONPATH="${PYTHONPATH:-}:$PROJECT_ROOT/backend/src"

echo "Starting Streamlit console at $STREAMLIT_ADDRESS:$STREAMLIT_PORT..."
echo "Mode: DRY-RUN / PAPER EVALUATION ONLY"
export HOME="$PROJECT_ROOT"

# Launch Streamlit with stability flags
python3 -m streamlit run backend/src/web_console.py \
    --server.port "$STREAMLIT_PORT" \
    --server.address "$STREAMLIT_ADDRESS" \
    --server.fileWatcherType none \
    --browser.gatherUsageStats false

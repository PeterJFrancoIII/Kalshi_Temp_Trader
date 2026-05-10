#!/usr/bin/env bash
# NO REAL TRADING EXECUTION
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

if [ -x "$PROJECT_ROOT/.venv/bin/python3" ]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
elif [ -x "$BACKEND_DIR/venv/bin/python3" ]; then
  PYTHON_BIN="$BACKEND_DIR/venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

cd "$BACKEND_DIR"

export PYTHONPATH="$BACKEND_DIR/src:$BACKEND_DIR/tests"

echo "Running Kalshi Backend Tests from $BACKEND_DIR..."
echo "PYTHONPATH: $PYTHONPATH"
echo "Using Python: $PYTHON_BIN"

"$PYTHON_BIN" tests/run_tests.py

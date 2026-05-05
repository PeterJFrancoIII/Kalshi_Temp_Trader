#!/usr/bin/env bash
# NO REAL TRADING EXECUTION
set -euo pipefail
# settle_yesterday.sh - Runs a dry-run settlement check

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

export PYTHONPATH="${PYTHONPATH:-}:$BACKEND_DIR/src"

echo "Running settlement dry-run..."
echo "Using Python: $PYTHON_BIN"

"$PYTHON_BIN" -m scheduler.settlement_check --dry-run

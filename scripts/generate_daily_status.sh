#!/usr/bin/env bash
set -euo pipefail

# generate_daily_status.sh
# Manually triggers the generation of the daily status JSON and Markdown reports.
# NO REAL TRADING EXECUTION included.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Use venv if available
if [ -x "$PROJECT_ROOT/.venv/bin/python3" ]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
elif [ -x "$BACKEND_DIR/venv/bin/python3" ]; then
  PYTHON_BIN="$BACKEND_DIR/venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

export PYTHONPATH="${PYTHONPATH:-}:$BACKEND_DIR/src"

echo "Generating Daily Status Report..."
"$PYTHON_BIN" -m scheduler.generate_daily_status
echo "Done."

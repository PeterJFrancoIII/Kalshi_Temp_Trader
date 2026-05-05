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

export PYTHONPATH="${PYTHONPATH:-}:$BACKEND_DIR/src"

echo "Using Python: $PYTHON_BIN"
echo "PYTHONPATH: $PYTHONPATH"

# All arguments are passed through to the Python script
# Examples:
#   ./scripts/run_daily_prediction.sh --dry-run --model rules_v2_climatology
#   ./scripts/run_daily_prediction.sh --dry-run --compare-models
"$PYTHON_BIN" -m scheduler.run_daily_prediction "$@"

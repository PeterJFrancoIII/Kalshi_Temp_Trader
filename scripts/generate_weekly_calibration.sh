#!/usr/bin/env bash
# NO REAL TRADING EXECUTION
set -euo pipefail

# Path-safe script directory discovery
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Venv discovery - prioritize project root .venv, then backend/venv
if [ -x "$PROJECT_ROOT/.venv/bin/python3" ]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
elif [ -x "$BACKEND_DIR/venv/bin/python3" ]; then
  PYTHON_BIN="$BACKEND_DIR/venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

# Set PYTHONPATH to include the backend src directory
export PYTHONPATH="${PYTHONPATH:-}:$BACKEND_DIR/src"

echo "Generating Weekly Aggregate Calibration Report..."
echo "Using Python: $PYTHON_BIN"
echo "PYTHONPATH: $PYTHONPATH"

# Defaults for KMIA production paths if no arguments provided
INPUT_DIR="${1:-$BACKEND_DIR/data/processed/comparisons}"
OUTPUT_DIR="${2:-$BACKEND_DIR/data/processed/aggregate_calibration}"

# Execute the aggregator
"$PYTHON_BIN" -m calibration.generate_aggregate_report \
    --input-dir "$INPUT_DIR" \
    --output-dir "$OUTPUT_DIR"

echo "Done. Aggregate reports saved to $OUTPUT_DIR"

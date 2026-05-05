#!/usr/bin/env bash
set -euo pipefail

# linux_setup.sh
# Performs initial environment setup on the Linux server.
# NO REAL TRADING EXECUTION

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
HISTORY_FILE="$BACKEND_DIR/data/processed/history/kmia_daily_history.jsonl"

echo "========================================================================"
echo "KMIA Linux Setup Started"
echo "Project Root: $PROJECT_ROOT"
echo "NO REAL TRADING EXECUTION"
echo "========================================================================"

# 1. Ensure directories exist
echo "Creating data directories..."
mkdir -p "$BACKEND_DIR/data/processed/logs"
mkdir -p "$BACKEND_DIR/data/processed/status"
mkdir -p "$BACKEND_DIR/data/processed/reports"
mkdir -p "$BACKEND_DIR/data/processed/aggregate_calibration"
mkdir -p "$BACKEND_DIR/data/processed/history"

# 2. Setup Virtual Environment
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/.venv"
fi

echo "Installing dependencies..."
"$PROJECT_ROOT/.venv/bin/pip" install --upgrade pip
"$PROJECT_ROOT/.venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

# 3. Verify Canonical History File
echo "Verifying canonical history file..."
if [ ! -f "$HISTORY_FILE" ]; then
    echo "ERROR: Canonical history file missing at $HISTORY_FILE"
    exit 1
fi

RECORD_COUNT=$(wc -l < "$HISTORY_FILE")
echo "History record count: $RECORD_COUNT"
if [ "$RECORD_COUNT" -lt 27000 ]; then
    echo "ERROR: History file is too small ($RECORD_COUNT records). Expected >= 27000."
    exit 1
fi

# 4. Run Tests
echo "Running verification tests..."
bash "$SCRIPT_DIR/run_tests.sh"

echo "========================================================================"
echo "KMIA Linux Setup Completed Successfully"
echo "Next steps:"
echo "1. Run health check: bash scripts/health_check.sh"
echo "2. Run daily workflow: bash scripts/run_kmia_daily_workflow.sh"
echo "========================================================================"

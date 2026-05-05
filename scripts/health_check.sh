#!/usr/bin/env bash
set -euo pipefail

# health_check.sh
# Verifies system integrity and recent operational success.
# NO REAL TRADING EXECUTION

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
PROCESSED_DIR="$BACKEND_DIR/data/processed"
LOG_DIR="$PROCESSED_DIR/logs"
STATUS_DIR="$PROCESSED_DIR/status"
HISTORY_FILE="$PROCESSED_DIR/history/kmia_daily_history.jsonl"
HEALTH_LOG="$LOG_DIR/health_check_latest.log"

# Redirect output to health log
exec > >(tee "$HEALTH_LOG") 2>&1

echo "========================================================================"
echo "KMIA Health Check: $(date)"
echo "NO REAL TRADING EXECUTION"
echo "========================================================================"

HEALTH_STATUS="OK"
WARNINGS=()

# 1. History File Check
if [ ! -f "$HISTORY_FILE" ]; then
    echo "ERROR: History file missing."
    HEALTH_STATUS="ERROR"
else
    COUNT=$(wc -l < "$HISTORY_FILE")
    if [ "$COUNT" -lt 27000 ]; then
        echo "ERROR: History file too small ($COUNT records)."
        HEALTH_STATUS="ERROR"
    fi
fi

# 2. Latest Workflow Log Check
LATEST_WORKFLOW_LOG=$(ls -t "$LOG_DIR"/kmia_daily_workflow_*.log 2>/dev/null | head -n 1 || true)
if [ -n "$LATEST_WORKFLOW_LOG" ]; then
    if grep -q "Traceback" "$LATEST_WORKFLOW_LOG"; then
        echo "ERROR: Traceback found in $LATEST_WORKFLOW_LOG"
        HEALTH_STATUS="ERROR"
    fi
    if grep -q "ERROR" "$LATEST_WORKFLOW_LOG"; then
        echo "ERROR: ERROR found in $LATEST_WORKFLOW_LOG"
        HEALTH_STATUS="ERROR"
    fi
else
    WARNINGS+=("No daily workflow log found yet.")
    HEALTH_STATUS="WARN"
fi

# 3. Status Report Check
LATEST_STATUS_JSON=$(ls -t "$STATUS_DIR"/kmia_daily_status_*.json 2>/dev/null | head -n 1 || true)
LATEST_STATUS_MD=$(ls -t "$STATUS_DIR"/kmia_daily_status_*.md 2>/dev/null | head -n 1 || true)

if [ -z "$LATEST_STATUS_JSON" ] || [ -z "$LATEST_STATUS_MD" ]; then
    WARNINGS+=("Status reports missing.")
    if [ "$HEALTH_STATUS" != "ERROR" ]; then HEALTH_STATUS="WARN"; fi
fi

# Summary
echo "------------------------------------------------------------------------"
echo "HEALTH_STATUS=$HEALTH_STATUS"
echo "Latest Workflow Log: ${LATEST_WORKFLOW_LOG:-None}"
echo "Latest Status JSON: ${LATEST_STATUS_JSON:-None}"
echo "Latest Status MD: ${LATEST_STATUS_MD:-None}"

if [ ${#WARNINGS[@]} -ne 0 ]; then
    echo "Warnings:"
    for w in "${WARNINGS[@]}"; do
        echo "  - $w"
    done
fi
echo "------------------------------------------------------------------------"

if [ "$HEALTH_STATUS" == "ERROR" ]; then
    exit 1
else
    exit 0
fi

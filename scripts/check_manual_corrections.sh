#!/bin/bash
# KMIA Manual Data Corrections Checker
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

PROJECT_ROOT="/opt/kmia-kalshi"
if [ ! -d "$PROJECT_ROOT" ]; then
    PROJECT_ROOT="."
fi

CONFIG_FILE="$PROJECT_ROOT/backend/config/manual_data_corrections.json"

echo "===================================================="
echo "      KMIA MANUAL DATA CORRECTIONS CHECKER"
echo "      NO REAL TRADING EXECUTION"
echo "===================================================="

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file missing at $CONFIG_FILE"
    exit 1
fi

# Validate JSON
if command -v python3 >/dev/null 2>&1; then
    if ! python3 -m json.tool "$CONFIG_FILE" >/dev/null 2>&1; then
        echo "❌ Error: Invalid JSON in $CONFIG_FILE"
        exit 1
    fi
else
    echo "⚠️ Python3 not found, skipping JSON validation."
fi

echo "✅ Config file found and valid JSON."
echo ""

echo "--- Configured Correction Dates ---"
# Extract dates using simple grep/sed for portability
grep -E '"[0-9]{4}-[0-9]{2}-[0-9]{2}":' "$CONFIG_FILE" | sed 's/[^0-9-]*//g'

echo ""
echo "--- Excluded from Learning ---"
grep -B 10 '"exclude_from_learning": true' "$CONFIG_FILE" | grep -E '"[0-9]{4}-[0-9]{2}-[0-9]{2}":' | sed 's/[^0-9-]*//g'

echo ""
echo "--- Market Open-Time Overrides ---"
grep -B 10 '"market_open_time_et":' "$CONFIG_FILE" | grep -E '"[0-9]{4}-[0-9]{2}-[0-9]{2}":' | sed 's/[^0-9-]*//g'

echo ""
echo "===================================================="
echo "      SAFETY CHECK COMPLETE"
echo "      NO REAL TRADING EXECUTION"
echo "===================================================="

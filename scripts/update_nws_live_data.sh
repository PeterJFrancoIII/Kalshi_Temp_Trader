#!/bin/bash
# Update NWS Live Data for KMIA
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

set -e

PROJECT_ROOT="/opt/kmia-kalshi"
if [ ! -d "$PROJECT_ROOT" ]; then
    PROJECT_ROOT="."
fi

# Activate virtual environment
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/backend/venv" ]; then
    source "$PROJECT_ROOT/backend/venv/bin/activate"
fi

export PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT/backend:$PROJECT_ROOT/backend/src"

DATA_DIR="$PROJECT_ROOT/backend/data/processed/weather_nws"
mkdir -p "$DATA_DIR"

LATEST_FILE="$DATA_DIR/latest_nws_kmia_snapshot.json"
TIMESTAMP_FILE="$DATA_DIR/nws_kmia_snapshot_$(date +%Y-%m-%d_%H%M%S).json"
TMP_FILE="$DATA_DIR/latest_nws_kmia_snapshot.tmp.json"

echo "===================================================="
echo "      UPDATING LIVE NWS KMIA DATA"
echo "      NO REAL TRADING EXECUTION"
echo "===================================================="

python3 "$PROJECT_ROOT/backend/src/weather/nws_live_client.py" > "$TMP_FILE"

if [ -s "$TMP_FILE" ]; then
    mv "$TMP_FILE" "$LATEST_FILE"
    cp "$LATEST_FILE" "$TIMESTAMP_FILE"
    echo "✅ Success: Saved snapshot to $LATEST_FILE"
    echo "✅ Success: Archiving as $TIMESTAMP_FILE"
    python3 "$PROJECT_ROOT/scripts/archive_observed_history.py"
else
    echo "❌ Error: Failed to generate NWS snapshot."
    rm -f "$TMP_FILE"
    exit 1
fi

echo "===================================================="
echo "      UPDATE COMPLETE"
echo "      NO REAL TRADING EXECUTION"
echo "===================================================="

#!/bin/bash
# Update The Weather Company Data for KMIA
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

PROJECT_ROOT="/opt/kmia-kalshi"
if [ ! -d "$PROJECT_ROOT" ]; then
    PROJECT_ROOT="."
fi

if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/backend/venv" ]; then
    source "$PROJECT_ROOT/backend/venv/bin/activate"
fi

export PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT/backend:$PROJECT_ROOT/backend/src"

DATA_DIR="$PROJECT_ROOT/backend/data/processed/weather_company"
mkdir -p "$DATA_DIR"

echo "===================================================="
echo "      UPDATING THE WEATHER COMPANY KMIA DATA"
echo "      NO REAL TRADING EXECUTION"
echo "===================================================="

if [ -z "$TWC_API_KEY" ] && [ -z "$WEATHER_COMPANY_API_KEY" ]; then
    echo "WARN: TWC_API_KEY or WEATHER_COMPANY_API_KEY is not set."
    echo "      A snapshot will still be written with MISSING_API_KEY quality flags."
fi

python3 "$PROJECT_ROOT/backend/src/weather/twc_kmia_client.py"

LATEST_FILE="$DATA_DIR/latest_twc_kmia_snapshot.json"

if [ -s "$LATEST_FILE" ]; then
    echo "✅ Success: Saved TWC snapshot to $LATEST_FILE"
    echo "----------------------------------------------------"
    echo "LATEST TWC STATUS REPORT:"
    echo "----------------------------------------------------"
    python3 - <<'PY'
import json
from pathlib import Path
p = Path("backend/data/processed/weather_company/latest_twc_kmia_snapshot.json")
if p.exists():
    data = json.loads(p.read_text())
    print("fetched_at_utc:", data.get("fetched_at_utc"))
    print("provider:", data.get("provider"))
    print("station:", data.get("station"))
    print("forecast_high_f:", data.get("derived_features", {}).get("forecast_high_f"))
    print("hourly_max_temp_f:", data.get("derived_features", {}).get("hourly_max_temp_f"))
    print("sea_breeze_shift_hour_et:", data.get("derived_features", {}).get("sea_breeze_shift_hour_et"))
    print("quality_flags:", data.get("quality_flags", []))
PY
else
    echo "❌ Error: Failed to generate TWC snapshot."
    exit 1
fi

echo "===================================================="
echo "      UPDATE COMPLETE"
echo "      NO REAL TRADING EXECUTION"
echo "===================================================="

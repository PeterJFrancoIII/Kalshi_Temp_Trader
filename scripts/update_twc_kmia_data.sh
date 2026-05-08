#!/bin/bash
# Update The Weather Company Data for KMIA
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

set -e

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
RAW_DIR="$PROJECT_ROOT/backend/data/raw/weather_company"
mkdir -p "$DATA_DIR" "$RAW_DIR"

LATEST_FILE="$DATA_DIR/latest_twc_kmia_snapshot.json"
TMP_FILE="$DATA_DIR/latest_twc_kmia_snapshot.tmp.json"
BACKUP_FILE="$DATA_DIR/latest_twc_kmia_snapshot.backup.json"

cd "$PROJECT_ROOT"

echo "===================================================="
echo "      UPDATING THE WEATHER COMPANY KMIA DATA"
echo "      NO REAL TRADING EXECUTION"
echo "===================================================="

if [ -z "$TWC_API_KEY" ] && [ -z "$WEATHER_COMPANY_API_KEY" ]; then
    echo "❌ Error: TWC_API_KEY or WEATHER_COMPANY_API_KEY is not set."
    echo "   Refusing to overwrite the latest valid TWC snapshot with an empty MISSING_API_KEY snapshot."
    echo "   Load the key first, for example:"
    echo "   export TWC_API_KEY=\"$(cat '/Users/computer/Desktop/App Development/Kalshi/1_Downloads/The_Weather_Company_API_Documents/API Key.md' | tr -d '[:space:]')\""
    exit 2
fi

if [ -s "$LATEST_FILE" ]; then
    cp "$LATEST_FILE" "$BACKUP_FILE"
fi

python3 "$PROJECT_ROOT/backend/src/weather/twc_kmia_client.py" > "$TMP_FILE"

python3 - <<'PY'
import json
import sys
from pathlib import Path

p = Path("backend/data/processed/weather_company/latest_twc_kmia_snapshot.tmp.json")
try:
    data = json.loads(p.read_text())
except Exception as exc:
    print(f"❌ Error: could not parse temporary TWC snapshot: {exc}")
    sys.exit(3)

hourly_status = data.get("endpoint_status", {}).get("hourly_forecast", {}).get("status")
hourly_rows = len(data.get("hourly_forecast", []) or [])
daily_status = data.get("endpoint_status", {}).get("daily_forecast", {}).get("status")
daily_rows = len(data.get("daily_forecast", []) or [])
quality_flags = data.get("quality_flags", []) or []

print("candidate_daily_status:", daily_status)
print("candidate_daily_rows:", daily_rows)
print("candidate_hourly_status:", hourly_status)
print("candidate_hourly_rows:", hourly_rows)
print("candidate_quality_flags:", quality_flags)

if hourly_status != "OK" or hourly_rows <= 0:
    print("❌ Error: candidate TWC snapshot is not comparison-ready. Keeping existing latest snapshot.")
    sys.exit(4)
PY

mv "$TMP_FILE" "$LATEST_FILE"
TIMESTAMP_FILE="$DATA_DIR/twc_kmia_snapshot_$(date -u +%Y-%m-%d_%H%M%S).json"
cp "$LATEST_FILE" "$TIMESTAMP_FILE"

echo "✅ Success: Saved TWC snapshot to $LATEST_FILE"
echo "✅ Success: Archiving as $TIMESTAMP_FILE"
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
    print("twc_hourly_rows:", len(data.get("hourly_forecast", []) or []))
    print("comparison_ready:", data.get("comparison_metadata", {}).get("comparison_ready"))
    print("quality_flags:", data.get("quality_flags", []))
PY

echo "===================================================="
echo "      UPDATE COMPLETE"
echo "      NO REAL TRADING EXECUTION"
echo "===================================================="

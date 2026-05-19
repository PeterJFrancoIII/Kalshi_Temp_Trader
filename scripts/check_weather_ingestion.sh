#!/bin/bash
# KMIA Weather Ingestion Audit
# NO REAL TRADING EXECUTION

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT_DIR/backend/src"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"

echo "===================================================="
echo "         KMIA WEATHER INGESTION AUDIT"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="

# Run the ingestion status writer (canonical module path).
# The class is also re-exported from weather.nws_kmia_client for
# backward compatibility — see that module's docstring.
cd "$ROOT_DIR"
"$PYTHON_BIN" -m ingestion.weather_status_writer

STATUS_FILE="backend/data/processed/weather_ingestion/latest_weather_ingestion_status.json"

if [ -f "$STATUS_FILE" ]; then
    echo "----------------------------------------------------"
    echo "LATEST STATUS REPORT:"
    echo "----------------------------------------------------"
    cat "$STATUS_FILE" | grep -E "fetched_at_utc|current_temp_f|observed_max_so_far_f|forecast_high_f|latest_observation_time|stale_data|history_record_count|climatology_active"
    
    STALE=$(cat "$STATUS_FILE" | grep "stale_data" | grep "true")
    if [ ! -z "$STALE" ]; then
        echo "----------------------------------------------------"
        echo "WARN: DATA IS STALE"
    fi
else
    echo "ERROR: Status file not found at $STATUS_FILE"
fi

echo "===================================================="

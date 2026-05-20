#!/bin/bash
set -e

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

echo "Updating TWC Probabilistic Forecast Data..."

# Ensure we are in the repo root
if [ ! -d ".venv" ]; then
    echo "Error: .venv not found. Please run from repo root."
    exit 1
fi

if [ -z "$TWC_API_KEY" ] && [ -z "$WEATHER_COMPANY_API_KEY" ]; then
    echo "❌ Error: TWC_API_KEY or WEATHER_COMPANY_API_KEY is not set."
    echo "   Refusing to overwrite the latest valid probabilistic snapshot with an empty MISSING_API_KEY snapshot."
    exit 2
fi

PYTHONPATH=backend/src .venv/bin/python3 backend/src/weather/twc_probabilistic_client.py

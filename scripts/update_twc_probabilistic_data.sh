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

PYTHONPATH=backend/src .venv/bin/python3 backend/src/weather/twc_probabilistic_client.py

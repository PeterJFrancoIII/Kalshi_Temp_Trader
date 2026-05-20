#!/bin/bash
set -e

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

echo "Updating Synoptic KMIA Observation Data..."

# Ensure we are in the repo root
if [ ! -d ".venv" ]; then
    echo "Error: .venv not found. Please run from repo root."
    exit 1
fi

if [ -z "$SYNOPTIC_TOKEN" ] && [ -z "$SYNOPTIC_API_TOKEN" ]; then
    echo "❌ Error: SYNOPTIC_TOKEN or SYNOPTIC_API_TOKEN is not set."
    echo "   Running client to emit unavailable snapshot..."
fi

PYTHONPATH=backend/src .venv/bin/python3 backend/src/weather/synoptic_kmia_client.py

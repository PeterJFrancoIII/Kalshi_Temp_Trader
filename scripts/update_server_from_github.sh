#!/bin/bash
# update_server_from_github.sh - Server-side deployment script
# NO REAL TRADING EXECUTION

set -e

EXPECTED_DIR="/opt/kmia-kalshi"
CURRENT_DIR=$(pwd)

echo "------------------------------------------------"
echo "KMIA Server Update Tool"
echo "NO REAL TRADING EXECUTION"
echo "------------------------------------------------"

# Check if running from the correct directory
if [ "$CURRENT_DIR" != "$EXPECTED_DIR" ]; then
    echo "WARNING: This script is intended to run from $EXPECTED_DIR."
    echo "Current directory: $CURRENT_DIR"
    # Do not exit yet, but warn. 
fi

# Fail if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "ERROR: Uncommitted changes detected. Please commit or stash before updating."
    exit 1
fi

echo "Fetching latest changes from origin..."
git fetch origin

echo "Pulling updates from origin/main..."
git pull --ff-only origin main

echo "Updating Python environment..."
source .venv/bin/activate
python -m pip install -r backend/requirements.txt

echo "Running tests..."
bash scripts/run_tests.sh

echo "Generating daily status..."
bash scripts/generate_daily_status.sh

echo "Restarting services..."
sudo systemctl restart kmia-web-console.service

echo "Verifying service health..."
curl -I http://127.0.0.1:8501

echo ""
echo "Update complete."
echo "Final Commit Hash: $(git rev-parse HEAD)"
echo "------------------------------------------------"

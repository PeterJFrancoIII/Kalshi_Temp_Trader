#!/usr/bin/env bash
# ========================================================================
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY
# Read-only Kalshi public market fetch only.
# ========================================================================
set -euo pipefail

# Safely discover project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "========================================================================"
echo "Kalshi Public Market Fetch Started: $(date)"
echo "Mode: READ-ONLY / PAPER EVALUATION"
echo "========================================================================"

# Select virtual environment
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    VENV_PATH="$PROJECT_ROOT/.venv"
elif [ -x "$BACKEND_DIR/venv/bin/python" ]; then
    VENV_PATH="$BACKEND_DIR/venv"
else
    echo "ERROR: No virtual environment found."
    exit 1
fi

source "$VENV_PATH/bin/activate"
export PYTHONPATH="${PYTHONPATH:-}:$BACKEND_DIR/src"

# Safety constraint: Unauthenticated read-only public fetch by default.
export KALSHI_USE_AUTH="false"

SNAPSHOT_DIR="$BACKEND_DIR/data/processed/kalshi_market_snapshots"
LATEST_SNAPSHOT="$SNAPSHOT_DIR/latest_kalshi_market_snapshot.json"
BACKUP_SNAPSHOT="$SNAPSHOT_DIR/latest_kalshi_market_snapshot.json.bak"

# 1. Back up existing snapshot to prevent corrupting/overwriting it on failures
if [ -f "$LATEST_SNAPSHOT" ]; then
    echo "Backing up existing valid snapshot..."
    cp "$LATEST_SNAPSHOT" "$BACKUP_SNAPSHOT"
fi

# 2. Execute canonical python market snapshot updater
echo "Running update_kalshi_snapshots..."
if python3 -m market_data.update_kalshi_snapshots; then
    echo "update_kalshi_snapshots completed successfully."
    
    # 3. Post-validation checks
    if [ -f "$LATEST_SNAPSHOT" ]; then
        STATUS=$(python3 -c "import json; print(json.load(open('$LATEST_SNAPSHOT')).get('status'))" 2>/dev/null || echo "UNKNOWN")
        echo "Snapshot status: $STATUS"
        if [ "$STATUS" = "EMPTY" ] || [ "$STATUS" = "FAILED_EMPTY" ]; then
            echo "WARNING: No active KMIA high-temperature contracts discovered."
        fi
    else
        echo "ERROR: update_kalshi_snapshots returned 0 but no latest snapshot file was found."
        if [ -f "$BACKUP_SNAPSHOT" ]; then
            echo "Restoring backup snapshot..."
            cp "$BACKUP_SNAPSHOT" "$LATEST_SNAPSHOT"
        fi
        exit 1
    fi
else
    EXIT_CODE=$?
    echo "ERROR: update_kalshi_snapshots failed with exit code $EXIT_CODE."
    
    # 4. Restore the backup snapshot if Python fetch failed completely
    if [ -f "$BACKUP_SNAPSHOT" ]; then
        echo "Restoring backup snapshot to prevent using corrupted or partial data."
        cp "$BACKUP_SNAPSHOT" "$LATEST_SNAPSHOT"
    fi
    exit "$EXIT_CODE"
fi

# Clean up backup on success
rm -f "$BACKUP_SNAPSHOT"

echo "========================================================================"
echo "Kalshi Public Market Fetch Completed: $(date)"
echo "========================================================================"

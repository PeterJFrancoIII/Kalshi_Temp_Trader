#!/bin/bash
# check_sync_status.sh - Safe read-only sync status checker
# NO REAL TRADING EXECUTION

set -e

echo "------------------------------------------------"
echo "KMIA Sync Status Checker"
echo "NO REAL TRADING EXECUTION"
echo "------------------------------------------------"

# Current Branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current Branch: $BRANCH"

# Current Commit Hash
HASH=$(git rev-parse HEAD)
echo "Current Commit: $HASH"

# Remote URL
REMOTE=$(git remote get-url origin)
echo "Remote URL:     $REMOTE"

# Git Status (Short)
echo ""
echo "Git Status (Short):"
git status --short

# Check if ahead/behind
echo ""
if git fetch origin > /dev/null 2>&1; then
    LOCAL=$(git rev-parse @)
    REMOTE_HASH=$(git rev-parse origin/main)

    if [ "$LOCAL" = "$REMOTE_HASH" ]; then
        echo "Status: Local branch is up to date with origin/main."
    else
        BEHIND=$(git rev-list --count @..origin/main)
        AHEAD=$(git rev-list --count origin/main..@)
        
        if [ "$BEHIND" -gt 0 ]; then
            echo "Status: Local branch is BEHIND origin/main by $BEHIND commits."
        fi
        
        if [ "$AHEAD" -gt 0 ]; then
            echo "Status: Local branch is AHEAD of origin/main by $AHEAD commits."
        fi
    fi
else
    echo "Status: Could not fetch from origin. Check your internet connection or GitHub credentials."
    echo "Last known state for origin/main: $(git rev-parse origin/main 2>/dev/null || echo 'Unknown')"
fi

echo "------------------------------------------------"

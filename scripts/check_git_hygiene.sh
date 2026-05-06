#!/bin/bash
# scripts/check_git_hygiene.sh
# KMIA Kalshi Git Hygiene Auditor
#
# IMPORTANT: NO REAL TRADING EXECUTION
# This script is READ-ONLY.

set -e

echo "----------------------------------------------------------------"
echo "KMIA KALSHI GIT HYGIENE AUDIT"
echo "Safety Check: NO REAL TRADING EXECUTION"
echo "----------------------------------------------------------------"

echo "Current Git Status (Short):"
git status --short
echo ""

echo "Checking for tracked generated files under backend/data/processed and backend/tests/test_reports..."
# We explicitly exclude the canonical history file from the warning
TRACKED_GENERATED=$(git ls-files backend/data/processed backend/tests/test_reports | grep -v "backend/data/processed/history/kmia_daily_history.jsonl" || true)

if [ -n "$TRACKED_GENERATED" ]; then
    echo "WARNING: The following generated files are being tracked by Git:"
    echo "$TRACKED_GENERATED"
    echo ""
    echo "Recommendation:"
    echo "Run 'git rm --cached <file>' for each file listed above to stop tracking them."
    echo "DO NOT remove 'backend/data/processed/history/kmia_daily_history.jsonl'."
else
    echo "SUCCESS: No unexpected generated files are tracked by Git."
fi

echo "----------------------------------------------------------------"
echo "Audit Complete."
exit 0

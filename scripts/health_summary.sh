#!/bin/bash
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

set -u

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "===================================================="
echo "         KMIA KALSHI BOT HEALTH SUMMARY"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="

# 1. Git Info
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "N/A")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "N/A")
GIT_STATUS_FULL=$(git status --porcelain 2>/dev/null)
if [[ -z "$GIT_STATUS_FULL" ]]; then
    GIT_TREE="Clean"
else
    # Check if dirty ONLY because of runtime outputs (even if ignored, they might show up if tracked)
    # We grep -v for everything we listed in .gitignore as generated
    NON_RUNTIME_DIRTY=$(echo "$GIT_STATUS_FULL" | \
        grep -v "backend/data/processed/" | \
        grep -v "backend/tests/temp/" | \
        grep -v "backend/tests/test_reports/" | \
        grep -v "backend/tests/test_history.jsonl" | \
        grep -v "backend/logs/" | \
        grep -v "backend/src/web_console.log" || true)
        
    if [[ -z "$NON_RUNTIME_DIRTY" ]]; then
        GIT_TREE="Runtime outputs changed"
    else
        GIT_TREE="Dirty source changes"
    fi
fi

echo "Git Commit:   $GIT_COMMIT"
echo "Git Branch:   $GIT_BRANCH"
echo "Git Tree:     $GIT_TREE"

# 2. Service Status
if command -v systemctl >/dev/null 2>&1; then
    SERVICE_ACTIVE=$(systemctl is-active kmia-web-console.service 2>/dev/null || echo "inactive")
else
    # Fallback check for process
    if pgrep -f "streamlit" >/dev/null 2>&1; then
        SERVICE_ACTIVE="active (process found)"
    else
        SERVICE_ACTIVE="inactive"
    fi
fi
echo "Service:      $SERVICE_ACTIVE"

# 3. HTTP Check
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8501 --connect-timeout 2 2>/dev/null || true)
if [[ -z "$HTTP_CODE" || "$HTTP_CODE" == "000" ]]; then HTTP_CODE="000"; fi
echo "HTTP 8501:    $HTTP_CODE"

# 4. File Paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/backend/data/processed"

LATEST_STATUS=$(ls -t "$DATA_DIR/status"/*.json 2>/dev/null | head -n 1)
LATEST_FORECAST=$(ls -t "$DATA_DIR/reports"/kmia_forecast_*.md 2>/dev/null | head -n 1)
LATEST_SNAPSHOT=$(ls -t "$DATA_DIR/kalshi_market_snapshots"/*.json 2>/dev/null | head -n 1)
LATEST_NWS_SNAPSHOT=$(ls -t "$DATA_DIR/weather_nws"/*.json 2>/dev/null | head -n 1)
CALIBRATION_FILE="$DATA_DIR/aggregate_calibration/aggregate_calibration.json"

echo "Latest Status:   ${LATEST_STATUS:-NOT FOUND}"
echo "Latest Forecast: ${LATEST_FORECAST:-NOT FOUND}"
echo "Latest Snapshot: ${LATEST_SNAPSHOT:-NOT FOUND}"
echo "Latest NWS:      ${LATEST_NWS_SNAPSHOT:-NOT FOUND}"

# 5. Snapshot Market Count
MARKETS_FOUND=0
if [[ -n "$LATEST_SNAPSHOT" && -f "$LATEST_SNAPSHOT" ]]; then
    if command -v jq >/dev/null 2>&1; then
        MARKETS_FOUND=$(jq '.markets_found // 0' "$LATEST_SNAPSHOT")
    else
        MARKETS_FOUND=$(grep -o '"markets_found": [0-9]*' "$LATEST_SNAPSHOT" | awk '{print $2}' || echo "0")
    fi
    echo "Markets Found:   $MARKETS_FOUND"
else
    echo -e "${YELLOW}WARN: Latest snapshot missing or empty.${NC}"
fi

# 6. NWS Live Data Status
NWS_LIVE_STATUS="MISSING"
if [[ -n "$LATEST_NWS_SNAPSHOT" && -f "$LATEST_NWS_SNAPSHOT" ]]; then
    if command -v jq >/dev/null 2>&1; then
        IS_STALE=$(jq '.stale_data' "$LATEST_NWS_SNAPSHOT")
        if [[ "$IS_STALE" == "false" ]]; then
            NWS_LIVE_STATUS="CONNECTED"
        else
            NWS_LIVE_STATUS="STALE"
        fi
    else
        if grep -q '"stale_data": false' "$LATEST_NWS_SNAPSHOT"; then
            NWS_LIVE_STATUS="CONNECTED"
        else
            NWS_LIVE_STATUS="STALE"
        fi
    fi
fi
echo "NWS Live Data:   $NWS_LIVE_STATUS"

# 7. Resource Usage
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}')
# Memory usage (portable-ish)
if [[ "$OSTYPE" == "darwin"* ]]; then
    MEM_USAGE=$(vm_stat | perl -ne '/page size of (\d+) bytes/ and $s=$1; /Pages free:\s+(\d+)/ and $f=$1; /Pages active:\s+(\d+)/ and $a=$1; /Pages inactive:\s+(\d+)/ and $i=$1; /Pages speculative:\s+(\d+)/ and $p=$1; /Pages wired down:\s+(\d+)/ and $w=$1; END { printf "%.1f%%", 100*($a+$i+$p+$w)/($a+$i+$p+$w+$f) }' 2>/dev/null || echo "N/A")
else
    MEM_USAGE=$(free -m 2>/dev/null | grep Mem | awk '{printf "%.1f%%", $3/$2*100}' || echo "N/A")
fi

echo "Disk Usage (/):  $DISK_USAGE"
echo "Memory Usage:    $MEM_USAGE"

# Warnings
if [[ -z "$LATEST_STATUS" ]]; then echo -e "${YELLOW}WARN: Missing status file.${NC}"; fi
if [[ -z "$LATEST_FORECAST" ]]; then echo -e "${YELLOW}WARN: Missing forecast file.${NC}"; fi
if [[ "$MARKETS_FOUND" -eq 0 ]]; then echo -e "${YELLOW}WARN: Zero markets found in latest snapshot.${NC}"; fi
if [[ "$GIT_TREE" == "Dirty source changes" ]]; then echo -e "${YELLOW}WARN: Uncommitted source code changes exist.${NC}"; fi
if [[ "$NWS_LIVE_STATUS" != "CONNECTED" ]]; then echo -e "${YELLOW}WARN: NWS Live Data is $NWS_LIVE_STATUS.${NC}"; fi

# Final Status Logic
# GREEN = console active, HTTP 200, status exists, forecast exists
# YELLOW = console active but Kalshi market has zero markets or calibration/snapshot missing
# RED = console inactive, HTTP check fails, status missing, or forecast missing

STATUS_COLOR=$RED
STATUS_TEXT="RED"

CONSOLE_OK=false
if [[ "$SERVICE_ACTIVE" == "active"* || "$SERVICE_ACTIVE" == "active" ]]; then
    CONSOLE_OK=true
fi

HTTP_OK=false
if [[ "$HTTP_CODE" == "200" ]]; then
    HTTP_OK=true
fi

FILES_OK=false
if [[ -n "$LATEST_STATUS" && -n "$LATEST_FORECAST" ]]; then
    FILES_OK=true
fi

if [[ "$CONSOLE_OK" == true && "$HTTP_OK" == true && "$FILES_OK" == true ]]; then
    # Could be GREEN or YELLOW
    if [[ "$MARKETS_FOUND" -gt 0 && -f "$CALIBRATION_FILE" && -n "$LATEST_SNAPSHOT" && "$GIT_TREE" != "Dirty source changes" && "$NWS_LIVE_STATUS" == "CONNECTED" ]]; then
        STATUS_COLOR=$GREEN
        STATUS_TEXT="GREEN"
    else
        STATUS_COLOR=$YELLOW
        STATUS_TEXT="YELLOW"
    fi
else
    STATUS_COLOR=$RED
    STATUS_TEXT="RED"
fi

echo "----------------------------------------------------"
echo -e "FINAL STATUS: ${STATUS_COLOR}${STATUS_TEXT}${NC}"
echo "----------------------------------------------------"

exit 0

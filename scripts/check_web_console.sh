#!/bin/bash
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

set -euo pipefail

echo "--- KMIA Web Console Health Check ---"

# Check if the process is listening on the expected port
if curl -s -I http://127.0.0.1:8501 | grep -q "200 OK"; then
    echo "[PASS] Web console is responding on http://127.0.0.1:8501"
else
    echo "[FAIL] Web console is NOT responding on http://127.0.0.1:8501"
    exit 1
fi

# Check if the systemd service is active (if running on Linux with systemd)
if command -v systemctl >/dev/null 2>&1; then
    if systemctl is-active --quiet kmia-web-console.service; then
        echo "[PASS] kmia-web-console.service is active"
    else
        echo "[FAIL] kmia-web-console.service is NOT active"
        exit 1
    fi
else
    echo "[INFO] systemctl not found, skipping service check"
fi

echo "--- Health Check Complete: OK ---"

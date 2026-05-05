#!/bin/bash
# fetch_kmia_live.sh
# NO REAL TRADING EXECUTION
# Refreshes live observations from NWS.

set -e

# Navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/.."

export PYTHONPATH=$PYTHONPATH:.

echo "Refreshing KMIA live observations..."
python3 -m backend.src.scheduler.jobs live

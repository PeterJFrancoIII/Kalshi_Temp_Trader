#!/bin/bash
# Generate Contract-Aware Forecast Report
# NO REAL TRADING EXECUTION

# Resolve script directory and root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "--------------------------------------------------"
echo "Generating Contract-Aware Forecast Report..."
echo "Safety: DRY-RUN / PAPER EVALUATION ONLY"
echo "--------------------------------------------------"

# Ensure PYTHONPATH includes backend/src
export PYTHONPATH="$ROOT_DIR/backend/src:$PYTHONPATH"

# Run signal generator first to update the signal JSON
python3 "$ROOT_DIR/backend/src/paper_trading/signal_generator.py"

# Run report generator
python3 "$ROOT_DIR/backend/src/paper_trading/contract_forecast_report.py"

echo "--------------------------------------------------"
echo "Done. See backend/data/processed/reports/latest_contract_forecast_report.md"
echo "--------------------------------------------------"

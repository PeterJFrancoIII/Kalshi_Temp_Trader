#!/bin/bash
# KMIA Paper Trading Signal Generator
# NO REAL TRADING EXECUTION

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT_DIR/backend/src"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"

echo "===================================================="
echo "         KMIA PAPER TRADING SIGNAL"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="

cd "$ROOT_DIR"
"$PYTHON_BIN" backend/src/paper_trading/signal_generator.py

STATUS_FILE="backend/data/processed/paper_trading/latest_paper_signal.json"

if [ -f "$STATUS_FILE" ]; then
    echo "----------------------------------------------------"
    echo "BEST SIGNAL:"
    echo "----------------------------------------------------"
    # Use python to extract best signal for clean printing
    "$PYTHON_BIN" -c "
import json
import sys
try:
    with open('$STATUS_FILE', 'r') as f:
        data = json.load(f)
    best = data.get('best_signal')
    if best:
        print(f\"TICKER:      {best.get('market_ticker')}\")
        print(f\"BIN:         {best.get('forecast_bin_label')}\")
        print(f\"MODEL PROB:  {best.get('model_probability'):.2%}\")
        print(f\"MARKET PROB: {best.get('market_probability'):.2%}\" if best.get('market_probability') else \"MARKET PROB: N/A\")
        print(f\"EDGE:        {best.get('edge'):+.2%}\" if best.get('edge') is not None else \"EDGE: N/A\")
        print(f\"CONFIDENCE:  {best.get('confidence').upper()}\")
        print(f\"ACTION:      {best.get('paper_action')}\")
    else:
        print('No signals generated.')
except Exception as e:
    print(f'Error printing signal: {e}')
"
else
    echo "ERROR: Signal file not found at $STATUS_FILE"
fi

echo "===================================================="

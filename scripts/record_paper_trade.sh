#!/bin/bash
# record_paper_trade.sh
# NO REAL TRADING EXECUTION
# Records a simulated trade from the latest paper signal.

set -e

# Resolve project root
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="$ROOT/backend/src"
PYTHON_BIN="$ROOT/.venv/bin/python3"

echo "===================================================="
echo "         KMIA PAPER TRADE RECORDER"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="

cd "$ROOT/backend"
PYTHONPATH="$PYTHONPATH" "$PYTHON_BIN" src/paper_trading/ledger.py

echo "----------------------------------------------------"
if [ -f "data/processed/paper_trading/paper_trade_ledger.jsonl" ]; then
    echo "LATEST RECORDED TRADE:"
    tail -n 1 "data/processed/paper_trading/paper_trade_ledger.jsonl"
else
    echo "No trades recorded."
fi
echo "===================================================="

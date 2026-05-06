#!/bin/bash
# KMIA Automated Paper Trading Loop
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT_DIR/backend/src"

echo "===================================================="
echo "         KMIA PAPER TRADING LOOP"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="

cd "$ROOT_DIR"

echo "[1/4] Updating Kalshi Market Data..."
bash scripts/update_kalshi_market_data.sh

echo "[2/4] Generating Paper Signals..."
bash scripts/generate_paper_signal.sh

echo "[3/4] Recording Paper Trades..."
bash scripts/record_paper_trade.sh

echo "[4/4] Settling Paper Trades..."
bash scripts/settle_paper_trades.sh

echo "===================================================="
echo "         PAPER TRADING LOOP COMPLETE"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="
exit 0

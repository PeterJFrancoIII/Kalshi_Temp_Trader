#!/bin/bash
# KMIA Kalshi Start Entire System Script
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

PROJECT_ROOT="/opt/kmia-kalshi"
export PYTHONPATH="$PROJECT_ROOT/backend/src"

echo "===================================================="
echo "         KMIA KALSHI SYSTEM STARTUP"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="

cd "$PROJECT_ROOT" || { echo "Error: PROJECT_ROOT $PROJECT_ROOT does not exist. Are you in the right directory?"; exit 1; }

# Virtual Environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "backend/venv" ]; then
    source backend/venv/bin/activate
else
    echo "Warning: No virtual environment found at .venv or backend/venv"
fi

echo "[1/10] Installing dependencies..."
pip install -r backend/requirements.txt -q

echo "[2/10] Running Tests..."
bash scripts/run_tests.sh

echo "[3/10] Updating Kalshi Market Data..."
bash scripts/update_kalshi_market_data.sh

echo "[4/10] Generating Paper Signal..."
bash scripts/generate_paper_signal.sh

echo "[5/10] Recording Paper Trade..."
bash scripts/record_paper_trade.sh

echo "[6/10] Settling Paper Trades..."
bash scripts/settle_paper_trades.sh

echo "[7/10] Generating Daily Status..."
bash scripts/run_kmia_daily_workflow.sh > /dev/null 2>&1 || true # Optional step if the script exists
# Just generate status directly if run_kmia_daily_workflow fails or is missing
python -c "from daily_status import build_daily_status; build_daily_status()" 2>/dev/null || true

echo "[8/10] Restarting Web Console..."
if systemctl is-active --quiet kmia-web-console.service; then
    sudo systemctl restart kmia-web-console.service
    echo "kmia-web-console.service restarted."
else
    echo "kmia-web-console.service not active or installed. Skipping restart."
fi

echo "[9/10] Enabling Timers..."
if [ -f "deploy/systemd/kmia-kalshi-market-data.timer" ]; then
    sudo systemctl enable --now kmia-kalshi-market-data.timer 2>/dev/null || echo "Needs sudo to enable kmia-kalshi-market-data.timer"
fi
if [ -f "deploy/systemd/kmia-paper-trading-loop.timer" ]; then
    sudo systemctl enable --now kmia-paper-trading-loop.timer 2>/dev/null || echo "Needs sudo to enable kmia-paper-trading-loop.timer"
fi

echo "[10/10] Health Summary..."
bash scripts/health_summary.sh

echo "===================================================="
echo "         Git Hygiene Check"
echo "===================================================="
echo "Generated files under backend/data/processed are runtime outputs."
echo "Untracked files status:"
git status --short

PAPER_DIR="backend/data/processed/paper_trading"
if ls $PAPER_DIR/paper_signal_*.json 1> /dev/null 2>&1; then
    echo "Cleaning up outdated paper_signal_*.json snapshots..."
    rm -f $PAPER_DIR/paper_signal_*.json
fi

# Explicitly do NOT remove the core ledger/performance files
# Never commit, never push, never reset, never clean.
echo "Git hygiene complete. Remember: Never commit runtime files."

echo "===================================================="
echo "         SYSTEM STARTED SUCCESSFULLY"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="
echo "To view the console, open an SSH tunnel:"
echo "  ssh -N -L 8502:127.0.0.1:8501 kmia"
echo "Then navigate to http://127.0.0.1:8502"

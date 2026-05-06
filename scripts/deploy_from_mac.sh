#!/bin/bash
# KMIA Kalshi Mac to Server Deploy Script
# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

echo "===================================================="
echo "         KMIA KALSHI DEPLOYMENT"
echo "         NO REAL TRADING EXECUTION"
echo "===================================================="

# Detect that it is being run from the repo root
if [ ! -d ".git" ]; then
    echo "Error: Not in the root of a git repository. Run from the repo root."
    exit 1
fi

# Confirm it is not being run on the server
if [ "$(hostname)" = "hal" ]; then
    echo "Error: Run this from the Mac, not the server."
    exit 1
fi

echo "Current Git Status:"
git restore --staged backend/data/processed backend/tests/temp 2>/dev/null || true
git status --short

if [ -n "$(git status --short)" ]; then
    read -p "Commit all current changes? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Generated files are not committed."
        git add .agent backend/src backend/tests docs scripts deploy backend/config backend/requirements.txt README.md .gitignore 2>/dev/null || true
        git restore --staged backend/data/processed backend/tests/temp 2>/dev/null || true
        git commit -m "Update KMIA bot"
    else
        echo "Exiting safely without committing or pushing."
        exit 0
    fi
else
    echo "No uncommitted changes."
fi

echo "Pushing to GitHub..."
git push origin main || { echo "Failed to push to GitHub."; exit 1; }

LOCAL_COMMIT=$(git rev-parse HEAD)
echo "Local commit: $LOCAL_COMMIT"

echo "Deploying to server..."
ssh kmia << 'EOF'
    set -e
    echo "Connected to server."
    cd /opt/kmia-kalshi
    echo "Pulling latest changes..."
    git fetch origin
    git restore backend/tests/temp/ 2>/dev/null || true
    git pull --ff-only origin main
    
    SERVER_COMMIT=$(git rev-parse HEAD)
    echo "Server commit: $SERVER_COMMIT"
    
    echo "Setting up environment..."
    source .venv/bin/activate
    python -m pip install -r backend/requirements.txt -q
    
    echo "Running tests..."
    bash scripts/run_tests.sh
    
    echo "Executing paper trading loop..."
    bash scripts/update_kalshi_market_data.sh
    bash scripts/generate_paper_signal.sh
    bash scripts/record_paper_trade.sh
    bash scripts/settle_paper_trades.sh
    bash scripts/generate_daily_status.sh
    
    echo "Restarting services..."
    sudo systemctl restart kmia-web-console.service || echo "Failed to restart web console"
    sudo systemctl restart kmia-paper-trading-loop.timer || true
    sudo systemctl restart kmia-kalshi-market-data.timer || true
    
    sleep 10
    
    echo "Checking health..."
    bash scripts/health_summary.sh
    
    echo "Checking Web Console HTTP availability..."
    curl -I http://127.0.0.1:8501 || echo "Web console might not be running"
EOF

DEPLOY_EXIT=$?

echo "===================================================="
echo "Deployment Results:"
echo "Local commit: $LOCAL_COMMIT"
if [ $DEPLOY_EXIT -eq 0 ]; then
    echo "Deployment SUCCEEDED."
else
    echo "Deployment FAILED."
fi
echo "===================================================="
echo "To view the console, open an SSH tunnel:"
echo "  ssh -N -L 8502:127.0.0.1:8501 kmia"
echo "Then navigate to http://127.0.0.1:8502"

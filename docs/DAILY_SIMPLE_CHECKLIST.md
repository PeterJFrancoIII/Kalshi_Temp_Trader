# Daily Simple Checklist

## 1. Open the console

Use the browser link from the SSH tunnel.

## 2. Look at SYSTEM STATUS

### GREEN

Everything is working.
Do nothing.

### YELLOW

The bot is working, but something needs attention.
Read ACTION NEEDED.
Most common reason:
Kalshi market discovery found 0 markets.

### RED

Something important is broken.
Go to the Logs tab.
Run:

```bash
bash scripts/health_summary.sh
```

## 3. Safe commands

Run from the server:

```bash
cd /opt/kmia-kalshi
source .venv/bin/activate

bash scripts/health_summary.sh
bash scripts/run_tests.sh
bash scripts/generate_daily_status.sh
bash scripts/update_kalshi_market_data.sh
```

## 4. Git sync check

Mac:

```bash
cd "/Users/computer/Desktop/App Development/Kalshi"
git rev-parse HEAD
```

Server:

```bash
cd /opt/kmia-kalshi
git rev-parse HEAD
```

The hashes should match.

## 5. Safety

**This system is DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

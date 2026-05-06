# Simple Troubleshooting Guide

## If the console does not open

Run:

```bash
sudo systemctl status kmia-web-console.service --no-pager
curl -I http://127.0.0.1:8501
sudo systemctl restart kmia-web-console.service
```

## If the dashboard is YELLOW

**Meaning:**
The bot is mostly working, but something needs attention.
Most common reason:
Kalshi market discovery found 0 markets.

Run:

```bash
bash scripts/health_summary.sh
bash scripts/update_kalshi_market_data.sh
```

## If the dashboard is RED

**Meaning:**
Something important is broken.

Run:

```bash
bash scripts/run_tests.sh
bash scripts/generate_daily_status.sh
bash scripts/health_summary.sh
```

## If Git sync is broken

Run:

```bash
bash scripts/check_sync_status.sh
```

**Warning:**

* Do not force push.
* Do not use rsync unless emergency recovery.

## If the server and Mac do not match

On Mac:

```bash
git rev-parse HEAD
```

On server:

```bash
git rev-parse HEAD
```

They should match.

## If tests fail

* Do not deploy new changes.
* Read the first FAIL line.
* Fix that first.

## Safety

**This project is DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

# Simple Troubleshooting Guide

## If the console does not open

Run these:

```bash
sudo systemctl status kmia-web-console.service --no-pager
curl -I http://127.0.0.1:8501
sudo systemctl restart kmia-web-console.service
```

## If the dashboard is YELLOW or RED

Check the meaning here: [What The Colors Mean](WHAT_THE_COLORS_MEAN.md).

Run these:

```bash
bash scripts/health_summary.sh
bash scripts/update_kalshi_market_data.sh
bash scripts/run_tests.sh
```

## If Git sync is broken

Run: `bash scripts/check_sync_status.sh`

**Warning:**

* Do not force push.
* Do not use rsync.

## If Mac and server do not match

Both should show the same code hash.

Mac: `git rev-parse HEAD`
Server: `git rev-parse HEAD`

## If tests fail

* Do not deploy.
* Read the first FAIL line.
* Fix it.

## Daily Routine

See the [Daily Simple Checklist](DAILY_SIMPLE_CHECKLIST.md).

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real orders.

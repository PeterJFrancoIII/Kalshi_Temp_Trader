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

## If Git sync is broken or Health says Git Tree is Dirty

If health says **Git Tree: Runtime outputs changed**, this is normal. See [Git Hygiene](GIT_HYGIENE.md).

If health says **Git Tree: Dirty source changes**, that needs attention.

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

## If Today's Forecast says Unknown

This means the console could not read the latest forecast summary.

Run on the server:

```bash
cd /opt/kmia-kalshi
bash scripts/run_kmia_daily_workflow.sh
bash scripts/generate_daily_status.sh
sudo systemctl restart kmia-web-console.service
```

Then refresh the browser.

If it still says Unknown, check the Forecast tab and Logs tab.

## Daily Routine

See the [Daily Simple Checklist](DAILY_SIMPLE_CHECKLIST.md).

For fixing incorrect data, see [Manual Data Corrections](MANUAL_DATA_CORRECTIONS.md).
For live weather data issues or missing observation tables, see [Live NWS / KMIA Data](NWS_LIVE_DATA.md).
For setup quality and risk issues, see [Prediction Quality Report](PREDICTION_QUALITY_REPORT.md).

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real orders.

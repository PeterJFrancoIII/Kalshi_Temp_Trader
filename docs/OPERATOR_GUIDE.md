# KMIA Bot Operator Guide

## What to check

For daily tasks, see the [Daily Simple Checklist](DAILY_SIMPLE_CHECKLIST.md).
To update the server from your Mac, see the [Simple Deploy Guide](DEPLOY_SIMPLE.md).

1. Open the console.
2. Check the status color. See [What The Colors Mean](WHAT_THE_COLORS_MEAN.md).
3. If GREEN, do nothing.
4. If YELLOW or RED, read the message.

## Safe commands

- `bash scripts/run_tests.sh`: Run tests.
- `bash scripts/generate_daily_status.sh`: Update status report.
- `bash scripts/update_kalshi_market_data.sh`: Update market prices.

## Troubleshooting

See the [Simple Troubleshooting Guide](TROUBLESHOOTING_SIMPLE.md).
Specifically, check there if Today's Forecast says **Unknown**.
To understand runtime output files and Git status, see [Git Hygiene](GIT_HYGIENE.md).
To correct incorrect market or weather data, see [Manual Data Corrections](MANUAL_DATA_CORRECTIONS.md).
To monitor live weather feeds, see [Live NWS / KMIA Data](NWS_LIVE_DATA.md).

## Paper Trading

For details on simulated trades and performance tracking, see the [Paper Trading Feedback](PAPER_TRADING_FEEDBACK.md) guide.
To monitor the background loop, see [Automated Paper Trading Loop](AUTOMATED_PAPER_LOOP.md).
For strategy lessons, see [Learning Summary](LEARNING_SUMMARY.md).

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**
**NO REAL TRADING EXECUTION.**
Do not add trading or API keys.

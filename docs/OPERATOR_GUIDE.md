# KMIA Bot Operator Guide

## What to check

For daily tasks, see the [Daily Simple Checklist](DAILY_SIMPLE_CHECKLIST.md).

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

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**
**NO REAL TRADING EXECUTION.**
Do not add trading or API keys.

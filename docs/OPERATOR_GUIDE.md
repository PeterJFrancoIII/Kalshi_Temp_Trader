# KMIA Bot Operator Guide

## What to check

For daily routines, see the [Daily Simple Checklist](DAILY_SIMPLE_CHECKLIST.md).

1. Open the console.
2. Look at SYSTEM STATUS.
3. If GREEN, do nothing.
4. If YELLOW, read ACTION NEEDED.
5. If RED, check Logs tab.

## Safe commands

- `bash scripts/run_tests.sh`: Run all system tests.
- `bash scripts/generate_daily_status.sh`: Refresh system status report.
- `bash scripts/run_kmia_daily_workflow.sh`: Run the full daily prediction workflow.
- `bash scripts/update_kalshi_market_data.sh`: Update Kalshi market price data.

## Troubleshooting

For quick fixes, see the [Simple Troubleshooting Guide](TROUBLESHOOTING_SIMPLE.md).

## Daily Routine

For daily routine checks, refer to the [Daily Simple Checklist](DAILY_SIMPLE_CHECKLIST.md).

## Safety

This system is DRY-RUN / PAPER EVALUATION ONLY.
**NO REAL TRADING EXECUTION.**

Do not add trading controls or API keys.

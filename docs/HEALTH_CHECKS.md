# Health Checks

This guide explains how to check the bot's health.

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

## Health Summary Script

Run this script to see if the system is OK:

```bash
bash scripts/health_summary.sh
```

## What the results mean

* **GREEN**: Working perfectly.
* **YELLOW**: Bot is working, but some non-critical data is missing.
* **RED**: Critical failure. Console might be down.

See [What The Colors Mean](WHAT_THE_COLORS_MEAN.md) for more details.

## Read-Only

This script only reads data. It does not change anything or place orders.

## Troubleshooting

See the [Simple Troubleshooting Guide](TROUBLESHOOTING_SIMPLE.md).

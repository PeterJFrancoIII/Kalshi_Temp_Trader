# What The Colors Mean

## GREEN

Everything is working.
No action needed.

## YELLOW

The bot is mostly working, but something needs attention.
Read ACTION NEEDED.

Common reasons:

* Kalshi found 0 matching markets
* Calibration is missing
* A warning appeared in logs

## RED

Something important is broken.
Open the Logs tab.

Run:

```bash
bash scripts/health_summary.sh
```

## Safety

**This system is DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

It must not place real Kalshi orders.

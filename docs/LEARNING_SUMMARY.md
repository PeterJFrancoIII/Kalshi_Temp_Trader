# Learning Summary

The learning summary helps the bot review its paper-trading results.

It does not place real trades.

## What it checks

- Latest paper signal
- Open paper trades
- Pending settlements
- Settled trades
- Win rate
- Simulated PnL
- Model lesson
- Next action

## Model lessons

"Waiting for settlement."
Means there are no settled paper trades yet.

"Current paper strategy is performing well."
Means the settled paper trades are doing well.

"Review calibration and edge thresholds."
Means the strategy may need adjustment.

"Paper strategy needs caution."
Means simulated PnL is negative.

"Collect more data."
Means there is not enough evidence yet.

## How to run

```bash
bash scripts/generate_learning_summary.sh
bash scripts/health_summary.sh
```

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

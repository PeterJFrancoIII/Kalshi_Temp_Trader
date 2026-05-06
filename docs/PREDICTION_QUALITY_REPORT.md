# Prediction Quality Report

The prediction quality report helps the operator understand whether today’s bot setup looks good, risky, or needs review.

It does not place real trades.

## What it checks

- Today’s forecast
- Top probability bin
- Kalshi markets found
- Best paper signal
- Open paper trades
- Pending settlements
- Simulated PnL
- Manual data corrections
- Data quality warnings
- Next action

## Status meanings

### GOOD

The bot has the data it needs.

Usually this means:

- Forecast exists
- Kalshi markets were found
- Paper signal is available
- No critical data-quality issue was found

### WATCH

The bot is working, but something needs attention.

Examples:

- Kalshi markets are missing
- Data is stale
- There are pending settlements
- Some optional files are missing

### REVIEW

Something important needs human review.

Examples:

- Forecast file is missing
- Status file is missing
- Manual correction affects today
- Data quality issue may affect learning

## Main Risk

Main Risk explains the most important thing to watch today.

Examples:

- "Waiting for settlement."
- "Manual correction active."
- "Kalshi markets missing."
- "Forecast file missing."
- "No major risk found."

## Next Action

Next Action tells the operator what to do.

Examples:

- "No action needed."
- "Wait for official KMIA settlement."
- "Check the Forecast tab."
- "Check manual corrections."
- "Run health summary."

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

## How to run

```bash
bash scripts/generate_prediction_quality_report.sh
bash scripts/health_summary.sh
```

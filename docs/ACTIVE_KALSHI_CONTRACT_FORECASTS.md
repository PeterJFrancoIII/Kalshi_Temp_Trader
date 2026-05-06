# Active Kalshi Contract Forecasts

The bot now treats active Kalshi Miami max-temperature contracts as the display layer for forecasts.

This means the console should show the contracts that are actually open or pending on Kalshi, not only the internal static model bins.

The internal model may still use helper bins, but the operator should see the active Kalshi listings.

## Why this matters

Kalshi contracts can change by date.

The forecast report must match the currently active Miami max-temperature contracts for that date.

This helps paper trading compare:

- Model probability
- Kalshi market-implied probability
- Edge
- Expected value
- Paper action

## What the console should show

The Active Kalshi Contract Forecasts table should show:

- Ticker
- Contract title
- Status
- Threshold
- Condition
- Model probability
- Market probability
- Edge
- Time to close
- Speed-to-ROI score
- Paper action

## Paper actions

### NO EDGE

The model does not see a useful simulated edge.

### WATCH

The contract may be interesting, but the signal is not strong enough.

### PAPER BUY CANDIDATE

The contract has a positive paper-only signal.

This is not a real trade.

## Important safety rule

The bot is still:

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

## If contracts look wrong

Run:

```bash
bash scripts/update_kalshi_market_data.sh
bash scripts/generate_paper_signal.sh
bash scripts/health_summary.sh
```

Then refresh the console.

If the active contracts still look wrong, check the Kalshi Market Data tab and the latest market snapshot.

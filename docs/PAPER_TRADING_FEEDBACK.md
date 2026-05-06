# Paper Trading Feedback

This system does not place real trades.

It creates simulated paper signals, records simulated paper trades, and settles those trades against the official KMIA final high temperature.

## What it means

- **PAPER SIGNAL**: The bot found a possible simulated edge.
- **PAPER TRADE**: A simulated trade was recorded.
- **SETTLED TRADE**: The final KMIA temperature is known.
- **WIN**: The simulated trade matched the actual temperature bin.
- **LOSS**: The simulated trade did not match the actual temperature bin.
- **PnL**: Simulated profit or loss only.
- **PERFORMANCE SUMMARY**: JSON file at `backend/data/processed/paper_trading/latest_paper_trading_performance.json`.

## What to check

Run:

```bash
bash scripts/generate_paper_signal.sh
bash scripts/record_paper_trade.sh
bash scripts/settle_paper_trades.sh
bash scripts/health_summary.sh
```

## What good looks like

- Tests pass.
- Signals are generated when market data and forecast bins match.
- Paper trades are recorded only when edge is high enough.
- Settlements update the performance summary.
- The console shows win rate and simulated PnL.

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

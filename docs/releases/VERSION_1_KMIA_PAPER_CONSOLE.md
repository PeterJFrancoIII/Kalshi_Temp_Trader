# Version 1 — KMIA Paper Trading Console Known-Good Baseline

## Tag

v1.0.0-kmia-paper-console

## Purpose

This version is the first known-good local/paper trading console baseline for the KMIA Kalshi temperature bot.

## Status

- DRY-RUN / PAPER ONLY
- No live trading execution
- No order placement
- No order cancellation
- Kalshi read-only auth implemented
- Dynamic Kalshi contract mapping implemented
- Paper signal generation working
- Stale signal suppression implemented
- Command Center implemented
- Kalshi Market Console implemented
- Orderbook artifact ingestion implemented
- Weather Providers datetime merge crash fixed
- Full test suite passing at release time

## Known Limitations

- Live trading disabled
- Human decision recording not yet implemented
- Fee/slippage-aware edge not fully implemented
- Risk gate framework not fully implemented
- Empty snapshot overwrite resilience still needs hardening
- UI still subject to further refinement

## Recovery

To restore this baseline:

git checkout v1.0.0-kmia-paper-console

or:

git checkout fallback/v1-kmia-paper-console

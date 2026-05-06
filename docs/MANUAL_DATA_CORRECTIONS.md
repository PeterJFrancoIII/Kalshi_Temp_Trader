# Manual Data Corrections

Use this when NWS, KMIA, Kalshi, or settlement data is wrong.

Manual corrections help prevent bad data from hurting the bot's learning summaries, calibration, and paper-trading results.

This does not place real trades.

## Current corrections

### May 5, 2026

Operator reported:

- Kalshi data is incorrect.
- NWS/KMIA max temperature is incorrect.

Action:

- Exclude May 5 from learning until corrected.
- Mark settlement as needing manual review.

### May 7, 2026

Operator reported:

- The market/trade opened at 11:00 AM ET.

Action:

- Record 11:00 AM ET as the market open time.

## Config file

Manual corrections live here:

backend/config/manual_data_corrections.json

## Check corrections

Run:

```bash
bash scripts/check_manual_corrections.sh
```

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

## Simple rule

If data is wrong, do not let the bot learn from it until it is reviewed.

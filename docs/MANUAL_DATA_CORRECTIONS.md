# Manual Data Corrections

This document explains how to manually correct NWS/Kalshi data and record market timing overrides for the KMIA Kalshi bot.

## Safety First

**DRY-RUN / PAPER EVALUATION ONLY.**
**NO REAL TRADING EXECUTION.**

This system is for research and paper-trading evaluation only. It must not be used to place real Kalshi orders.

## Configuration File

Corrections are stored in:
`backend/config/manual_data_corrections.json`

## Common Use Cases

### 1. Correcting Bad Official Data
If the official NWS Max Temp is reported incorrectly in the automated history, you can override it:

```json
"2026-05-05": {
  "station": "KMIA",
  "corrected_official_max_temp_f": 88,
  "notes": ["Manual override of incorrect NWS data."]
}
```

### 2. Excluding Dates from Learning
If a day's data is so corrupt that it should not be used to train/calibrate models or calculate win rates:

```json
"2026-05-05": {
  "exclude_from_learning": true,
  "settlement_status": "needs_manual_review"
}
```

### 3. Recording Market Open-Time Overrides
If a Kalshi market opens at an unusual time (e.g., due to holiday or technical issues), you can record it for auditability:

```json
"2026-05-07": {
  "market_open_time_et": "11:00",
  "notes": ["Market opened late at 11:00 AM ET."]
}
```

## How it Impacts the System

- **Settlement**: If `corrected_official_max_temp_f` is present, it is used instead of the value in `kmia_daily_history.jsonl`.
- **Learning**: Dates with `exclude_from_learning: true` are filtered out of win rate and PnL calculations in the performance summary and learning generator.
- **Web Console**: Corrections are displayed on the Operator Home for transparency.
- **Auditability**: All corrections include mandatory notes and are versioned.

## Verification

Run the validation script to check your configuration:
```bash
bash scripts/check_manual_corrections.sh
```

# Live NWS / KMIA Data

The bot can read live public weather data from the National Weather Service API.

This is used for KMIA weather awareness and forecast checking.

It does not place trades.

## Data source

Public NWS API:

<https://api.weather.gov>

KMIA station observations:

<https://api.weather.gov/stations/KMIA/observations/latest>

Recent KMIA observations:

<https://api.weather.gov/stations/KMIA/observations>

KMIA point metadata:

<https://api.weather.gov/points/25.7959,-80.2870>

## What the bot shows

The console should show:

- Current temperature
- Observed max so far
- Forecast high
- Latest observation time
- Whether the data is stale
- Warnings if NWS data is missing or delayed

## How to run manually

```bash
bash scripts/update_nws_live_data.sh
bash scripts/health_summary.sh
```

## What good looks like

- NWS Live Data: CONNECTED
- Current Temp is visible
- Observed Max So Far is visible
- Forecast High is visible
- Stale Data: no

## If data is stale

This is usually YELLOW, not RED.

It means the system is running, but the latest NWS observation may be delayed.

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

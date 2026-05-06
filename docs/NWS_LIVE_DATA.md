# NWS Live Data Ingestion

This system provides live weather observation and forecast data for KMIA (Miami International Airport) using the public National Weather Service (NWS) API.

## Safety First

**DRY-RUN / PAPER EVALUATION ONLY.**
**NO REAL TRADING EXECUTION.**

- **Public NWS API only**: No API keys, no authentication, no secrets.
- **Read-only**: This system only fetches data and does not interact with any trading platforms.

## Architecture

### Components

1.  **NWS Client**: `backend/src/weather/nws_live_client.py`
    - Fetches point metadata for KMIA (25.7959,-80.2870).
    - Retrieves latest and recent observations.
    - Retrieves daily and hourly forecasts.
    - Compiles data into a standardized snapshot.
2.  **Update Script**: `scripts/update_nws_live_data.sh`
    - Runs the client and saves results.
    - Path: `backend/data/processed/weather_nws/latest_nws_kmia_snapshot.json`
    - Archives: `backend/data/processed/weather_nws/nws_kmia_snapshot_YYYY-MM-DD_HHMMSS.json`
3.  **Web Console**:
    - New tab: **Live NWS / KMIA Data**
    - Displays current temp, observed max, forecast high, and staleness status.

## How to Run

To manually update the live weather data:

```bash
bash scripts/update_nws_live_data.sh
```

## Data Fields

- **Current Temp**: Latest reported temperature in Fahrenheit.
- **Observed Max So Far**: The highest temperature recorded today at KMIA.
- **Forecast High**: The predicted daytime high for today.
- **Stale Data**: Marked `true` if the latest observation is older than 90 minutes.

## Troubleshooting

- **MISSING**: The snapshot file does not exist. Run the update script.
- **STALE**: NWS has not updated the observation in over 90 minutes. Check [api.weather.gov](https://api.weather.gov) status.
- **ERROR**: API endpoint failed. Check internet connectivity and NWS API availability.

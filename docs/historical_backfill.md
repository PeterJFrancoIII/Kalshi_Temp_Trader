# Historical CLIMIA Backfill Strategy

## Overview

To provide a baseline climatology for KMIA temperature forecasts, we use a local historical climatological report. This data is used to compute historical priors, rolling averages, and bin distributions.

## Local Source: NOAA Climatological Report

- **File Path**: `/Users/computer/Desktop/App Development/Kalshi/1950-2026_Climatological_Report_USW00012839_MIAMI_INTERNATIONAL_AIRPORT_.txt`
- **Station ID**: `USW00012839`
- **Station Name**: `MIAMI INTERNATIONAL AIRPORT, FL US`
- **Primary Field**: `TMAX` (Daily Maximum Temperature)
- **Format**: CSV with headers including STATION, NAME, DATE, PRCP, TAVG, TMAX, TMIN.

## Data Normalization

The `local_climatology_loader.py` script normalizes the raw CSV data into a standardized JSONL format.

- **Output Path**: `backend/data/processed/history/kmia_daily_history.jsonl`
- **Canonical Record Count**: 27,879 records.
- **Date Range**: 1950-01-01 to 2026-04-30.
- **Normalization Rules**:
    - Station must match `USW00012839`.
    - `TMAX` and `TMIN` are converted to integers (`tmax_f`, `tmin_f`).
    - `PRCP` is converted to float (`prcp_in`).
    - Quality flags are added for missing or malformed data.

## Fixtures and Samples

For testing purposes, small synthetic samples should be stored in:
`backend/data/processed/history/fixtures/`

Current fixtures:
- `kmia_historical_highs_sample_15.jsonl`: A 15-record sample for basic validation.

## Climatology Features

The system uses this historical data to calculate:

1. **Same-Day History**: Max temps for the same month/day in previous years.
2. **Rolling Average**: Average high over a window of days.
3. **Bin Distribution**: Historical frequency of temperatures landing in each Kalshi bin for a specific day of the year (with optional ±window_days).

## Usage

To backfill the processed JSONL history (Note: This overwrites the canonical file):

```bash
python -m ingestion.climia_backfill \
  --input "/Users/computer/Desktop/App Development/Kalshi/1950-2026_Climatological_Report_USW00012839_MIAMI_INTERNATIONAL_AIRPORT_.txt" \
  --output backend/data/processed/history/kmia_daily_history.jsonl
```

## Limitations

- **Local File dependency**: Requires the specific NOAA report file to be present at the expected path.
- **Data Quality**: Relies on the quality of the TMAX field in the NOAA report.
- **Lookahead Bias**: Feature functions are designed to exclude the target date's year to prevent leakage during training/evaluation.

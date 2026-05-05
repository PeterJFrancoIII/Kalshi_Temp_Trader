
# KMIA Kalshi Temperature Prediction App — Master Context

## Objective

Build an app that predicts the official daily maximum temperature at KMIA / Miami International Airport for Kalshi-style weather markets.

The app must output probabilities in these exact bins:

- <=78°F
- 79–80°F
- 81–82°F
- 83–84°F
- 85–86°F
- > =87°F
  >

## Current Scope

Only predict:

- Station: KMIA
- Location: Miami International Airport
- Metric: Daily maximum temperature
- Market style: Kalshi temperature bins

Do not expand to rain, low temperature, sports, politics, or other stations until the KMIA max-temp system is stable.

## Core Data Sources

### Final historical / settlement source

NWS Daily Climatological Report, CLIMIA:

https://forecast.weather.gov/product.php?site=MFL&issuedby=MIA&product=CLI&format=CI&version=1&glossary=0

Use CLIMIA as the final historical and settlement-adjacent truth source.

### Live nowcasting source

NWS WRH Time Series Viewer for KMIA:

https://www.weather.gov/wrh/timeseries?site=kmia

Use for live preliminary station observations and observed max so far.

### Backup observation source

NWS 3-day KMIA observation history:

https://www.weather.gov/data/obhistory/KMIA.html

Use as a backup and cross-check for live observations.

### Kalshi API docs

https://docs.kalshi.com/welcome
https://docs.kalshi.com/getting_started/quick_start_market_data
https://docs.kalshi.com/api-reference/market/get-market-orderbook

Use Kalshi read-only market data in the MVP. Do not implement real-money trading in MVP.

## Critical Rules

1. CLIMIA is final truth.
2. KMIA live time series is preliminary.
3. The app must never treat preliminary live data as final settlement truth.
4. If observed max so far already exceeds a temperature bin, that bin must receive 0% probability.
5. Probability bins must sum to approximately 1.00.
6. LLMs may review and sanity-check predictions, but hard sensor constraints override LLM output.
7. Do not place real-money trades in MVP.
8. All predictions must be logged and later settled against CLIMIA.

## Required Output JSON

{
  "station": "KMIA",
  "date": "YYYY-MM-DD",
  "metric": "daily_max_temperature_f",
  "best_single_number_f": 82,
  "probability_bins": {
    "<=78": 0.00,
    "79-80": 0.00,
    "81-82": 0.45,
    "83-84": 0.44,
    "85-86": 0.10,
    ">=87": 0.01
  },
  "observed_max_so_far_f": 82,
  "current_temp_f": 81,
  "forecast_high_f": 84,
  "confidence": "low|medium|high",
  "main_drivers": [],
  "warnings": []
}

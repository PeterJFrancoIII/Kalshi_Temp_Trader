# Data Sources

## 1. CLIMIA Daily Climatological Report

URL:
<https://forecast.weather.gov/product.php?site=MFL&issuedby=MIA&product=CLI&format=CI&version=1&glossary=0>

Role:
Final historical / settlement-adjacent truth source for KMIA daily climate data.

Use for:

- final daily maximum temperature
- final daily minimum temperature
- daily precipitation
- normal high
- normal low
- record high
- record low
- settlement validation

Important:
CLIMIA is the final validation layer. Use it to settle predictions after the report posts.

## 2. KMIA WRH Time Series Viewer

URL:
<https://www.weather.gov/wrh/timeseries?site=kmia>

Role:
Live preliminary nowcasting source.

Use for:

- current temperature
- observed max so far today
- live trend
- weather condition
- rain/thunderstorm flag
- cloud condition
- wind/dew point context

Important:
This source is preliminary and subject to quality-control changes. Do not use it as final settlement truth.

## 3. NWS KMIA Observation History

URL:
<https://www.weather.gov/data/obhistory/KMIA.html>

Role:
Backup and cross-check for live observations.

Use for:

- recent observation rows
- current temperature
- 6-hour max/min fields where available
- weather conditions
- METAR-like station information

## 4. Kalshi API

Docs:
<https://docs.kalshi.com/welcome>
<https://docs.kalshi.com/getting_started/quick_start_market_data>
<https://docs.kalshi.com/api-reference/market/get-market-orderbook>

Role:
Market comparison, order-book monitoring, and later paper trading.

MVP:
Read-only only.

Use for:

- discovering Miami/KMIA weather markets
- reading order books
- mapping market bins to internal bins
- computing implied probabilities
- paper-trading comparison

Do not use Kalshi market prices as weather truth.

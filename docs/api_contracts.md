# API Contracts

## Output Schema
The core output of the system is the `DailyPrediction`.

```json
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
  "confidence": "high",
  "main_drivers": ["Morning cloud cover observed", "Live temp tracking below normal"],
  "warnings": []
}
```

## Internal Data Flow
- Ingestion pulls raw text/JSON.
- Features module emits `ClimiaReport`, `LiveObservation`, `ForecastSnapshot`, `KalshiMarketSnapshot`.
- Forecasting and Calibration layers mutate and emit `TemperatureBins`.
- The final pipeline outputs a `DailyPrediction` object.

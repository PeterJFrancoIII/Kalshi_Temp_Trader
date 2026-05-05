
# KMIA Daily High Weather Model Spec

## Calibration Warning

The rules-based model probabilities are heuristic until enough CLIMIA-settled outcomes have been collected. Do not treat model probability as calibrated market edge until calibration metrics are available.

## Required Bins {## Calibration Warning  The rules-based model probabilities are heuristic until enough CLIMIA-settled outcomes have been collected. Do not treat model probability as calibrated market edge until calibration metrics are available.}

- <=78
- 79-80
- 81-82
- 83-84
- 85-86
- > =87
  >

## Temperature-to-Bin Function

```python
def temp_to_bin(max_temp_f: int) -> str:
    if max_temp_f <= 78:
        return "<=78"
    if 79 <= max_temp_f <= 80:
        return "79-80"
    if 81 <= max_temp_f <= 82:
        return "81-82"
    if 83 <= max_temp_f <= 84:
        return "83-84"
    if 85 <= max_temp_f <= 86:
        return "85-86"
    return ">=87"
```

## **Hard Constraint**

If observed_max_so_far_f exceeds a bin, that bin must be zero.

Examples:

observed_max_so_far_f = 82:

- <=78 = 0
- 79-80 = 0
- 81-82 can be positive
- 83-84 can be positive
- 85-86 can be positive
- =87 can be positive

observed_max_so_far_f = 85:

- <=78 = 0
- 79-80 = 0
- 81-82 = 0
- 83-84 = 0
- 85-86 can be positive
- =87 can be positive

## **Modeling Layers**

1. Historical prior from CLIMIA.
2. Forecast prior from NWS forecast guidance.
3. Live nowcast adjustment from KMIA observations.
4. LLM review and anomaly detection.

## **Initial Rules-Based Inputs**

- observed_max_so_far_f
- current_temp_f
- current_time_et
- forecast_high_f
- normal_high_f
- recent_rain_flag
- thunderstorm_flag
- overcast_flag
- wind_direction
- wind_speed
- dewpoint_f
- remaining_daylight_hours

## **Output Contract**

{

“station”: “KMIA”,

“date”: “YYYY-MM-DD”,

“metric”: “daily_max_temperature_f”,

“best_single_number_f”: number,

“probability_bins”: {

“<=78”: number,

“79-80”: number,

“81-82”: number,

“83-84”: number,

“85-86”: number,

“>=87”: number

},

“observed_max_so_far_f”: number,

“current_temp_f”: number,

“forecast_high_f”: number,

“confidence”: “low|medium|high”,

“main_drivers”: [],

“warnings”: []

}

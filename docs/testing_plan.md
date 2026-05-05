# Testing Plan

The KMIA Temperature Prediction App uses a multi-layered testing strategy to ensure reliability, data safety, and model calibration.

## 1. Unit Tests
Located in `backend/tests/`.
- `test_calibration_metrics.py`: Validates Brier score, log loss, and temp-to-bin mapping.
- `test_kmia_live_parser.py`: Validates NWS WRH JSON parsing.
- `test_climia_parser.py`: Validates NWS CLI text report parsing.
- `test_forecast_features.py`: Validates forecast data extraction.
- `test_temperature_bins.py`: Validates probability distribution logic.

## 2. Integration Tests
Located in `backend/tests/integration/`.
- `test_pipeline.py`: Exercises the end-to-end flow from data ingestion to settlement using a mock database.
- `test_edge_cases.py`: Validates sensor constraints (e.g., observed max zeroing out lower bins) and probability normalization.

## 3. Data Safety Constraints
The following constraints are enforced at the model and integration level:
- **Zeroing Lower Bins**: If the observed maximum temperature so far exceeds a bin range, that bin must be assigned 0% probability.
- **Probability Sum**: All bins must sum to 1.0 (± 0.005).
- **Stale Data Warning**: If live observations are older than 1 hour, a system warning is generated.

## 4. Running Tests
Run all tests using pytest:
```bash
pytest backend/tests/
```
Or use the provided shell script:
```bash
bash scripts/run_tests.sh
```

## 5. Calibration Monitoring
Calibration metrics (Brier Score, Log Loss) are automatically computed upon settlement and stored in the `calibration_metrics` table. These will be visible on the future Streamlit dashboard for long-term performance tracking.

# Database Schema (Proposed)

The system uses SQLite for local persistence of climatological data, observations, and prediction tracking.

## Tables

### 1. `climia_reports`
Final ground-truth climatological data from NWS CLI reports.
- `id`: Integer (PK)
- `date`: String (YYYY-MM-DD, Index)
- `station`: String
- `max_temp_f`: Integer
- `min_temp_f`: Integer
- `precipitation_inches`: Float
- `fetched_at`: DateTime

### 2. `live_observations`
Time-series observations from KMIA sensors.
- `id`: Integer (PK)
- `timestamp`: DateTime (Index)
- `station`: String
- `temperature_f`: Float
- `observed_max_so_far_f`: Float
- `fetched_at`: DateTime

### 3. `forecast_snapshots`
NWS forecast snapshots for KMIA.
- `id`: Integer (PK)
- `date`: String (Index)
- `station`: String
- `forecast_high_f`: Float
- `fetched_at`: DateTime

### 4. `daily_predictions`
The core prediction output.
- `id`: Integer (PK)
- `run_id`: String (Unique, Index)
- `date`: String (Index)
- `station`: String (default: `"KMIA"`)
- `model_version`: String (NOT NULL, INDEX, default: `"rules_v1"`) — Added P0 Fix 1. Values: `"rules_v1"`, `"rules_v2_climatology"`
- `best_single_number_f`: Float
- `prob_le_78`: Float
- `prob_79_80`: Float
- `prob_81_82`: Float
- `prob_83_84`: Float
- `prob_85_86`: Float
- `prob_ge_87`: Float
- `confidence`: String
- `created_at`: DateTime

> **Migration note (existing databases only)**: If you have an existing `kalshi.db` created before
> `model_version` was added, run this one-time command:
> ```bash
> sqlite3 backend/kalshi.db "ALTER TABLE daily_predictions ADD COLUMN model_version TEXT NOT NULL DEFAULT 'rules_v1';"
> ```
> New installations are unaffected — `Base.metadata.create_all()` includes the column automatically.

### 5. `settlements`
Final mapping of prediction to outcome.
- `id`: Integer (PK)
- `prediction_id`: FK -> daily_predictions.id
- `climia_report_id`: FK -> climia_reports.id
- `actual_high_f`: Integer
- `actual_bin`: String

### 6. `calibration_metrics`
Statistical performance scores.
- `id`: Integer (PK)
- `settlement_id`: FK -> settlements.id
- `brier_score`: Float
- `log_loss`: Float
- `top_predicted_bin`: String
- `winning_bin`: String
- `top_bin_hit`: Boolean

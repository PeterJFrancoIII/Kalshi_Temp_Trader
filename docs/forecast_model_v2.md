# Forecast Model v2: Rules-Based Climatology

## Overview
Forecast Model v2 improves upon the initial rules-based model by integrating **historical climatology** as a baseline prior. This allows the model to leverage 30+ years of local KMIA weather patterns to inform the probability distribution, especially when NWS forecast guidance is uncertain or missing.

## Data Sources
- **Source File**: `1950-2026_Climatological_Report_USW00012839_MIAMI_INTERNATIONAL_AIRPORT_.txt`
- **Processed Data**: `backend/data/processed/history/kmia_daily_history.jsonl`
- **Station**: KMIA (USW00012839)

## Model Architecture

### 1. Blended Prior
The model uses a weighted ensemble approach for its initial distribution:
- **45% Historical Climatology**: A 7-day rolling window centered on the target date over the last 30 years.
- **45% NWS Forecast**: A heuristic distribution centered on the NWS `forecast_high_f`.
- **10% Uniform Floor**: A small baseline probability across all bins to maintain statistical coverage.

### 2. Weather Suppression
Heuristic adjustments are applied to the upper temperature bins (>=87, 85-86, 83-84) based on live or forecasted conditions:
- **Overcast / Recent Rain**: Modest mass shift (5%) from upper bins to lower plausible bins.
- **Thunderstorm**: Stronger mass shift (15%) from upper bins to lower plausible bins.

### 3. Hard Sensor Constraints
The model enforces the **Impossible Bin Rule**:
- Any bin whose upper bound is below the `observed_max_so_far_f` is strictly zeroed.
- The remaining probability mass is re-normalized to sum to 1.0.

## Implementation Details
- **Module**: `backend/src/forecasting/rules_model_v2.py`
- **Prior Loader**: `backend/src/forecasting/climatology_model.py`
- **Model Version**: `rules_v2_climatology`

## Limitations & Warnings
- **Small Windows**: Seasonal windows (e.g., 7 days) may have sparse data in early backfill stages.
- **Climate Shift**: 30-year historical averages may not fully account for recent warming trends without further weighting.
- **Calibration**: This model should be calibrated against the `rules_v1` baseline to ensure the climatology weight (45%) is optimal.

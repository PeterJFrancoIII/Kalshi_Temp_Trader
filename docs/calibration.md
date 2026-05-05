# Calibration Scoring

This document describes the calibration scoring system for the KMIA temperature prediction model. For performance comparison between models, see [Model Comparison Reports](model_comparison.md).

## Methodology

Predictions are scored against final ground-truth maximum temperatures reported by the NWS CLIMIA product.

### 1. Temperature to Bin Mapping

The final maximum temperature is mapped to one of the six standard Kalshi KMIA bins:

- `<=78`
- `79-80`
- `81-82`
- `83-84`
- `85-86`
- `>=87`

### 2. Scoring Functions

#### Top-Bin Hit

A binary metric (True/False) indicating whether the bin assigned the highest probability by the model was the actual winning bin.

#### Brier Score (Multiclass)

Measures the mean squared difference between the predicted probability and the actual outcome across all bins.

- **Formula**: `BS = sum((p_i - y_i)^2)`
- **Range**: `0.0` (Perfect) to `2.0` (Worst possible for multiclass).

#### Log Loss (Multiclass)

Measures the uncertainty of the prediction. It penalizes being "confident and wrong".

- **Formula**: `Loss = -log(p_actual)`
- **Clipping**: An epsilon (`1e-15`) is used to clip probabilities to avoid infinite loss when the model assigns zero probability to the actual outcome.

## Validation Rules

Before scoring, the following validations are performed on the probability bins:

1. All six required bins must be present.
2. All probabilities must be between `0.0` and `1.0`.
3. The sum of all probabilities must be approximately `1.0` (within a `0.01` tolerance).

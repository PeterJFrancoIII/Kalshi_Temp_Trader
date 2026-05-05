# Model Comparison Reports

The Model Comparison module evaluates the performance of two forecasting models against settled ground truth (observed maximum temperature).

## Models Compared

- **v1 (rules_v1)**: The baseline rules-based model.
- **v2 (rules_v2_climatology)**: The challenger model incorporating climatology and enhanced heuristics.

## Core Metrics

| Metric | Description | Goal |
| :--- | :--- | :--- |
| **Brier Score** | Mean squared error of probability forecasts. | Lower is better |
| **Log Loss** | Negative log-likelihood of the actual outcome. | Lower is better |
| **Top-Bin Hit** | Whether the bin with the highest probability was the actual bin. | True is better |
| **Actual-Bin Prob** | Probability assigned by the model to the correct bin. | Higher is better |

## Comparison Fields

### Winner Fields

The report explicitly identifies a winner for each key metric:

- `winner_by_brier`
- `winner_by_log_loss`
- `winner_by_top_bin`

Values can be `rules_v1`, `rules_v2_climatology`, or `tie`. A small tolerance (`1e-12`) is used for floating-point comparisons.

### Delta Fields

Deltas are computed as **v2 minus v1**:

- `brier_delta_v2_minus_v1`
- `log_loss_delta_v2_minus_v1`

**Interpretation**:

- **Negative value**: Model v2 performed better (lower error).
- **Positive value**: Model v1 performed better (lower error).

### Human-Readable Summary

A deterministic summary string provides a concise interpretation of the results, e.g.:

> "rules_v2_climatology won by Brier score and log loss; both models hit the top bin; rules_v2_climatology assigned higher probability to the actual bin."

## Report Generation

Reports are automatically generated as both JSON and Markdown:

- **JSON**: Deterministic structure for automated tracking and aggregation.
- **Markdown**: Human-readable tables and summaries for quick review.

Recommended output path pattern:
`backend/data/processed/comparisons/YYYY-MM-DD_model_comparison.json`
`backend/data/processed/comparisons/YYYY-MM-DD_model_comparison.md`

## Future Aggregate Metrics

To evaluate long-term performance, the following aggregate metrics are recommended:

- **Total Settled Days**: Sample size for comparison.
- **Average Brier/Log Loss**: Overall accuracy per model.
- **Top-Bin Hit Rate**: Percentage of correct top-bin predictions.
- **Win Rate**: Percentage of days model v2 outperformed v1.

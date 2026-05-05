# Model Comparison Report
**Date**: 2026-05-03
**Final Max Temp**: 82°F
**Actual Bin**: `81-82`

## Metrics Comparison

| Metric | rules_v1 | rules_v2_climatology | Winner | Delta (v2-v1) |
| :--- | :--- | :--- | :--- | :--- |
| **Brier Score** | 0.3200 | 0.5724 | rules_v1 | 0.2524 |
| **Log Loss** | 0.6931 | 0.9163 | rules_v1 | 0.2231 |
| **Top Bin Hit** | ✅ | ❌ | rules_v1 | - |
| **Actual Bin Prob** | 0.5000 | 0.4000 | - | - |

## Prediction Details

| Bin | rules_v1 | rules_v2_climatology | Actual |
| :--- | :--- | :--- | :--- |
| <=78 | 0.0000 | 0.0000 |  |
| 79-80 | 0.0000 | 0.0000 |  |
| 81-82 | 0.0000 | 0.0000 | 🎯 |
| 83-84 | 0.0000 | 0.0000 |  |
| 85-86 | 0.0000 | 0.0000 |  |
| >=87 | 0.0000 | 0.0000 |  |

## Summary
Rules_v1 won by Brier score and log loss; only rules_v1 hit the top bin; rules_v2_climatology assigned lower probability to the actual bin.

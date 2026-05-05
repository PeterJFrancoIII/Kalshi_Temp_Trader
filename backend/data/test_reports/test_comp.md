# Model Comparison Report
**Date**: 2026-05-03
**Final Max Temp**: 82°F
**Actual Bin**: `81-82`

## Metrics Comparison

| Metric | rules_v1 | rules_v2_climatology | Winner | Delta (v2-v1) |
| :--- | :--- | :--- | :--- | :--- |
| **Brier Score** | 0.2000 | 0.3200 | rules_v1 | 0.1200 |
| **Log Loss** | 0.5108 | 0.6931 | rules_v1 | 0.1823 |
| **Top Bin Hit** | ✅ | ✅ | tie | - |
| **Actual Bin Prob** | 0.6000 | 0.5000 | - | - |

## Prediction Details

| Bin | rules_v1 | rules_v2_climatology | Actual |
| :--- | :--- | :--- | :--- |
| <=78 | 0.1000 | 0.1000 |  |
| 79-80 | 0.1000 | 0.1000 |  |
| 81-82 | 0.6000 | 0.5000 | 🎯 |
| 83-84 | 0.1000 | 0.2000 |  |
| 85-86 | 0.1000 | 0.1000 |  |
| >=87 | 0.0000 | 0.0000 |  |

## Summary
Rules_v1 won by Brier score and log loss; both models hit the top bin; rules_v2_climatology assigned lower probability to the actual bin.

---
name: kmia-probability-modeling
description: invoke when modifying forecasting logic, bin conversion, distribution blending, or probability outputs
---

# KMIA Probability Modeling

## Purpose
Ensure forecast work produces calibrated KMIA max-temperature probability distributions.

## Instructions
1. **Output Format**: Output a canonical integer Fahrenheit distribution as a dictionary: `Dict[int, float]`.
2. **Sum Constraint**: Probabilities across the distribution must sum to approximately 1.0 (range [0.995, 1.005]).
3. **Context Inclusion**: Include provenance, warnings, calibration version, and reasons for any adjustments in the output.
4. **Distribution Required**: Deterministic highs or single-point forecasts are insufficient. A full distribution is required.
5. **Observation Correction**: Live observation correction may truncate the impossible lower tail (e.g., if current temp is 82, probabilities for <82 become 0), but you must log the reason.
6. **Fixed Bins Legacy**: Fixed bins (e.g., <=78, 79-80) are for display and legacy compatibility only, not for production signal logic.

## Blockers / Fail-Closed Rules
- **No Live Trading**: This project is paper-evaluation only.
- **No Uncalibrated Edge**: Do not present heuristic probabilities as actionable market edge without calibration metrics.
- **Fail Closed**: If probabilities do not sum correctly or data is missing, fail closed and do not produce a signal.

## Required Output Format
Forecast outputs must contain:
- `station`: KMIA
- `date`: YYYY-MM-DD
- `distribution`: `Dict[int, float]`
- `calibration_version`: string
- `provenance`: list of sources
- `warnings`: list of strings

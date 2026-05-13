---
name: point-in-time-backtesting
description: invoke when editing backtesting code, timestamp utils, or selecting historical artifacts
---

# Point-in-Time Backtesting

## Purpose
Ensure replay and calibration work is lookahead-safe.

## Instructions
1. **Embedded Timestamps Only**: Use embedded JSON timestamps only for selecting historical artifacts.
2. **No Filesystem Mtime**: Do not use filesystem `mtime`, `ctime`, or `atime` for point-in-time selection.
3. **No 'Latest' Accidents**: Do not use `latest` artifacts or current files accidentally. Always resolve via the specific timestamp cutoff.
4. **Cutoff Exclusion**: Exclude any artifacts created after the simulated cutoff time for that specific run.
5. **Manifest Recording**: Every run must record a `replay_manifest.json` detailing which files were loaded.
6. **Metric Separation**: Separate the reporting of forecast accuracy, calibration quality, and trading PnL.
7. **No Invalid Scoring**: Do not score unsettled or invalid outcomes as evidence in calibration.

## Blockers / Fail-Closed Rules
- **Lookahead Violation**: Any use of data timestamped after the simulated decision time invalidates the run.
- **Missing Timestamp Blocks**: Files missing embedded timestamps must be ignored.

## Required Output Format
Backtest reports must include a section referencing the `replay_manifest.json` path and a statement confirming that no filesystem timestamps were used for ordering.

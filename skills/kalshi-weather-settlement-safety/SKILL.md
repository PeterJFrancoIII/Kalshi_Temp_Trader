---
name: kalshi-weather-settlement-safety
description: invoke when working on weather data ingestion, settlement logic, or source selection for kmia
---

# Kalshi Weather Settlement Safety

## Purpose
Ensure weather and settlement work targets the official KMIA settlement truth.

## Instructions
1. **Target KMIA Specifically**: Do not treat generic Miami weather forecasts or reports as the settlement target. The target is the official airport high at KMIA.
2. **Settlement Authority Ranking**:
   - **CLI/CLIMIA** is the final settlement authority. Use it for final settlement.
   - **DSM** (Daily Summary Message) is acceptable for early daily max confirmation.
   - **METAR / HF-ASOS / KMIA1M** are fast signals but are NOT final authority. Do not treat them as final settlement truth.
3. **Time Boundaries**: Respect Local Standard Time (LST) and Daylight Saving Time (DST) settlement boundary issues. Ensure comparisons are time-aligned.
4. **Risk Reduction**: Treat near-boundary values and Quality Control (QC) flagged values as risk-reduction or no-trade triggers rather than clean signals.
5. **Metadata Requirements**: Every weather artifact must include source timestamps, explicit station identity (KMIA), and freshness status.

## Blockers / Fail-Closed Rules
- **Paper Only**: This project is paper-evaluation only. No real trading execution.
- **No Inferred Truth**: Do not use preliminary sources (METAR/HF-ASOS) to settle trades.
- **Freshness Gate**: Missing or stale weather timestamps must block downstream execution.

## Required Output Format
When proposing a settlement or analyzing weather data, include:
- Source Name (CLI, DSM, etc.)
- Embedded Timestamp
- Station ID (must be KMIA)
- Value and any QC flags
- Verdict (Final, Preliminary, or Ignored)

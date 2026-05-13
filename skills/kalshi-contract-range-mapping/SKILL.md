---
name: kalshi-contract-range-mapping
description: invoke when editing market discovery, weather_market_mapper, or mapping kalshi tickers to ranges
---

# Kalshi Contract Range Mapping

## Purpose
Ensure market and signal work maps active Kalshi contract text to dynamic ranges correctly.

## Instructions
1. **Dynamic Parsing**: Parse active contract ranges dynamically from contract text/subtitles. Do not rely on fixed global bins for active contracts.
2. **Support All Shapes**: Support lower-tail (e.g., "below 80"), upper-tail (e.g., "85 or above"), between-range ("81 to 82"), and half-degree boundaries if they appear.
3. **Ambiguity Blocks**: Unknown or ambiguous contract text must be marked untradable. Do not guess the mapping.
4. **Signal Metadata**: Paper signal outputs must include:
   - Ticker and Event Ticker
   - Contract Range
   - Model Probability
   - Market Probability
   - Risk Decision
   - Warnings
   - Metadata explicitly stating "NO REAL TRADING".

## Blockers / Fail-Closed Rules
- **No Fixed Bins**: Do not assume Kalshi contracts match our legacy fixed display bins.
- **Uncertain Mapping Blocks**: Any uncertainty in subtitle parsing must block the trade candidate.
- **Read-Only**: No order placement or authenticated API calls.

## Required Output Format
Signal reports must include a `mapping_summary`:
- `ticker`: string
- `subtitle`: string
- `parsed_range`: string or null
- `status`: MAPPED | UNCERTAIN | FAILED

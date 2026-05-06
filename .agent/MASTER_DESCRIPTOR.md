# MASTER_DESCRIPTOR.md - KMIA Kalshi Temperature Prediction App

## Overview

The **KMIA Kalshi Temperature Prediction App** is a specialized forecasting system designed to predict the daily maximum temperature at Miami International Airport (KMIA) and map those predictions to Kalshi-style temperature bins.

The system is currently in a **MVP Research & Paper-Trading phase**. It is strictly a dry-run system used for evaluating model performance and calibration.

## Core Objective

To provide accurate, sensor-constrained probability distributions for KMIA temperature markets, ensuring that live physical observations (e.g., if it's already 82°F, the <=78°F bin must be 0%) are strictly enforced.

## Key Components

- **Ingestion**: Fetches NWS CLIMIA (historical truth) and live KMIA sensor data.
- **Forecasting**: Multi-model approach (V1 Rules, V2 Enhanced Rules) to generate probability bins.
- **Calibration**: Daily and weekly processes to compare forecasts against actual settled outcomes.
- **Safety Layer**: Strictly read-only market data; no execution logic allowed.

## Primary Workflows

- `bash scripts/run_kmia_daily_workflow.sh`: Full daily forecast and calibration loop.
- `bash scripts/generate_daily_status.sh`: Generates a Markdown/JSON status dashboard.
- `bash scripts/run_tests.sh`: Executes the full pytest suite.
- `bash scripts/run_web_console.sh`: Launches the Streamlit web dashboard.

## Deployment Target

- **Server**: Linux (Tailscale/Private)
- **User**: peterjfrancoiii
- **IP**: 100.109.192.54
- **Credentials**: Stored locally in `.env.deploy` (git-ignored).

## Temperature Bins (Current)

- `<=78`
- `79-80`
- `81-82`
- `83-84`
- `85-86`
- `>=87`

## Repository Structure

- `backend/src/`: Core Python logic.
- `backend/data/`: Processed reports and raw logs.
- `docs/`: Technical specifications and safety governance.
- `scripts/`: Operational shell scripts.
- `tests/`: Automated verification suite.

# KMIA Temperature Prediction App Architecture

## System Overview
The app is a modular pipeline for predicting the daily maximum temperature at KMIA. It ingests data from NWS and Kalshi, processes it through multiple layers (rules-based constraints, priors, LLM review), and produces formatted probability bins.
**Note**: The MVP is strictly Python-first. No React or JavaScript frontend will be built during the MVP. If a UI is required, a Streamlit dashboard will be used.

## Core Modules

### Ingestion (`backend/src/ingestion`)
Responsible for fetching raw data from NWS (CLIMIA, Live Observations, Forecasts) and Kalshi markets.

### Features (`backend/src/features`)
Parses and transforms raw data into standardized structured models (`WeatherSnapshot`, `ClimiaReport`, etc.).

### Forecasting (`backend/src/forecasting`)
Applies the baseline modeling rules, generating an initial probability distribution over the Kalshi bins based on historical priors and current observations.

### Calibration (`backend/src/calibration`)
Adjusts raw probabilities using hard constraints (e.g., if the observed maximum is already 85, bins below 85 are forced to 0).

### LLM Review (`backend/src/llm`)
Passes the structured context to an LLM for anomaly detection and final confidence scoring. Hard physical constraints supersede LLM outputs.

### Recommendation (`backend/src/recommendation`)
Analyzes the calibrated probabilities against the Kalshi market snapshot to identify informational recommendations.

### DB & Scheduler (`backend/src/db`, `backend/src/scheduler`)
Manages persistence of predictions and orchestrates the daily execution pipeline.

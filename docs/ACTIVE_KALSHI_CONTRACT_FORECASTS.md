# Active Kalshi Contract Forecasts

This feature allows the bot to map model-generated probability distributions to active Kalshi market contracts for Miami (KMIA) high temperature.

## Overview

The forecasting engine now extracts active contracts from Kalshi market snapshots and calculates:
- **Model Probability**: The probability of the contract condition being met, based on the latest model forecast.
- **Market Probability**: The implied probability from the current 'Yes' ask price (or last price).
- **Edge**: The difference between Model Probability and Market Probability.
- **Speed-to-ROI**: A normalized score representing the expected value per unit of time remaining until market close.

## Web Console Display

The web console provides two main views for this data:

### 1. Operator Home Section
A summary section titled **Active Kalshi Contract Forecasts** appears on the main dashboard. It highlights the **Best Signal** (the contract with the highest positive edge) and provides a summary table of all active contracts.

### 2. Dedicated Tab
A tab titled **Active Kalshi Contract Forecasts** provides a full-page view of the contract signals, including detailed metrics like Time to Close and Speed-to-ROI.

## Safety & Governance

**NO REAL TRADING EXECUTION.**
All signals generated are for **PAPER EVALUATION ONLY**. The system does not have API keys for order execution and will never attempt to place real trades.

## Running the Pipeline

To update the data displayed in the console:

1. **Update Market Snapshots**:
   ```bash
   bash scripts/update_kalshi_market_data.sh
   ```

2. **Generate Signals**:
   ```bash
   bash scripts/generate_paper_signal.sh
   ```

3. **Refresh Web Console**:
   The web console automatically reloads the latest `latest_paper_signal.json` file.

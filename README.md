# KMIA Kalshi Temperature Prediction App
Updated 5/7/26
## Overview

This application predicts the official daily maximum temperature at KMIA (Miami International Airport) for Kalshi-style weather markets.

**Note: This is an MVP that outputs probability bins for market analysis. It does NOT contain real-money trading or execution logic.**

## Features

- Ingests NWS Climatological data (CLIMIA) and live sensor data.
- Enforces hard physical constraints on probability bins based on live observations.
- Outputs temperature probabilities in defined Kalshi bins.

## Setup and Installation

To set up the environment and install dependencies, run the following commands from the project root:

```bash
# Create a virtual environment inside backend/
python3 -m venv backend/venv

# Activate the virtual environment
source backend/venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### Troubleshooting DNS / Pip Failures
If you encounter "Could not find a version that satisfies the requirement" or connection timeouts during `pip install`, it may be due to restricted network access or DNS issues in your environment. 
- Ensure you have an active internet connection.
- If behind a proxy, configure `HTTP_PROXY` and `HTTPS_PROXY` environment variables.
- Try using a local mirror if available: `pip install -r backend/requirements.txt --index-url <local-mirror-url>`

## Running Tests

Tests can be executed using the provided test script from the project root:

```bash
bash scripts/run_tests.sh
```

Alternatively, you can run pytest directly if the virtual environment is activated:

```bash
cd backend
export PYTHONPATH=$PYTHONPATH:$(pwd)/src:$(pwd)/tests
pytest tests
```

## MVP Operations

The system is currently locked for research and paper-trading evaluation.

- **Checklist**: [Daily Operations Checklist](docs/DAILY_OPERATIONS_CHECKLIST.md)
- **Runbook**: [System Runbook](docs/RUNBOOK.md)
- **Lockdown Details**: [MVP Lockdown Scope](docs/MVP_LOCKDOWN.md)
- **Safety Gate**: [Real Trading Gate (Not Approved)](docs/REAL_TRADING_GATE.md)
- **Deployment**: [Linux Deployment Guide](docs/LINUX_DEPLOYMENT.md)

### Primary Commands
```bash
# Run the full daily forecast and calibration loop
bash scripts/run_kmia_daily_workflow.sh

# Generate the latest status dashboard
bash scripts/generate_daily_status.sh
```

## Repository Structure

- `backend/`: Core Python application, including ingestion, models, and shared types.
- `frontend/`: (Future Placeholder) MVP is strictly Python-first. Streamlit will be used for any future dashboard needs.
- `docs/`: Architecture, operations, scheduling, and safety governance.
- `scripts/`: Shell scripts for system operations.

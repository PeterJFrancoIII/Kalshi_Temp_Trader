# Web Console Deployment Guide

**NO REAL TRADING EXECUTION**
**DRY-RUN / PAPER EVALUATION ONLY**

This document explains how to deploy and access the KMIA Weather Market Console on a private Linux server.

## Overview

The web console is built with **Streamlit** and provides a read-only view of the latest forecasts, status reports, and calibration metrics.

## Installation

1. **Create and activate a virtual environment**:

   ```bash
   cd /opt/kmia-kalshi
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r backend/requirements.txt
   ```

## Running the Console

### Manual Start

```bash
cd /opt/kmia-kalshi
bash scripts/run_web_console.sh
```

### Systemd Service Setup

To run the console as a background service:

1. **Copy the service file**:

   ```bash
   sudo cp deploy/systemd/kmia-web-console.service /etc/systemd/system/kmia-web-console.service
   ```

2. **Management commands**:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable kmia-web-console.service
   sudo systemctl restart kmia-web-console.service
   sudo systemctl status kmia-web-console.service --no-pager
   ```

3. **Health check**:

   ```bash
   curl -I http://127.0.0.1:8501
   ```

## Remote Access

### SSH Tunnel from Mac

Since the console binds to `127.0.0.1` by default for safety, use an SSH tunnel:

```bash
# From your Mac terminal:
ssh -N -L 8502:127.0.0.1:8501 peterjfrancoiii@192.168.0.126
```

### Browser URL

Then open your local browser to:
[http://127.0.0.1:8502](http://127.0.0.1:8502)

## Security Note

**WARNING**: 127.0.0.1 is the safe default. The `0.0.0.0` address should only be used if the server is behind a strict firewall, VPN, Tailscale, or an authenticated reverse proxy. Do not expose port 8501 publicly.

The console is **Read-Only**. It does not contain any trading controls, private keys, or API secrets. It is strictly for performance monitoring and paper-trading evaluation.

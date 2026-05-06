# Kalshi Market Data Integration

**NO REAL TRADING EXECUTION**
**DRY-RUN / PAPER EVALUATION ONLY**

This module provides read-only, unauthenticated access to Kalshi public market data. It is used to monitor market conditions for paper-trading evaluation.

## Overview

- **Source**: `https://api.elections.kalshi.com/trade-api/v2`
- **Authentication**: None required (public endpoints only).
- **Storage**: JSON snapshots are stored in `backend/data/processed/kalshi_market_snapshots/`.

## Manual Updates

To fetch the latest market data manually:

```bash
cd /opt/kmia-kalshi
bash scripts/update_kalshi_market_data.sh
```

## Automated Updates (Systemd)

To enable automatic updates every 5 minutes:

1. **Copy the service and timer files**:

   ```bash
   sudo cp deploy/systemd/kmia-kalshi-market-data.service /etc/systemd/system/
   sudo cp deploy/systemd/kmia-kalshi-market-data.timer /etc/systemd/system/
   ```

2. **Enable and start the timer**:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now kmia-kalshi-market-data.timer
   ```

3. **Verify**:

   ```bash
   systemctl list-timers | grep kalshi
   journalctl -u kmia-kalshi-market-data.service -n 80 --no-pager
   ```

## Security & Constraints

- **Read-Only**: This module contains NO logic for authentication, order placement, or account management.
- **No API Keys**: No credentials should ever be added to this module.
- **Restricted Endpoints**: Only `/markets`, `/events`, and `/markets/{ticker}/orderbook` are utilized.

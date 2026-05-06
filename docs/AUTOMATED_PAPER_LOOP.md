# Automated Paper Trading Loop

This loop is paper-only.

It does:

1. Update Kalshi market data
2. Generate a paper signal
3. Record a simulated paper trade if there is a strong signal
4. Try to settle paper trades if official KMIA data is available

It does not place real trades.

## Check status

Run:

```bash
systemctl list-timers | grep paper
sudo systemctl status kmia-paper-trading-loop.timer --no-pager
journalctl -u kmia-paper-trading-loop.service -n 80 --no-pager
```

## Manual run

```bash
cd /opt/kmia-kalshi
bash scripts/run_paper_trading_loop.sh
```

## What good looks like

- Timer is active
- Health is GREEN
- Paper ledger has OPEN or SETTLED simulated trades
- Performance summary updates over time

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

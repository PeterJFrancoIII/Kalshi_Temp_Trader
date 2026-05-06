# KMIA Kalshi Start Entire System

The `start_entire_system.sh` script provides a one-command initialization process to safely start the automated paper trading system.

## How to Run Manually

```bash
bash scripts/start_entire_system.sh
```

## How to Install Startup Service

To make the system start automatically on boot:

```bash
sudo cp deploy/systemd/kmia-full-system-startup.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable kmia-full-system-startup.service
sudo systemctl start kmia-full-system-startup.service
```

## How to Check System Status

```bash
sudo systemctl status kmia-full-system-startup.service --no-pager
sudo systemctl status kmia-web-console.service --no-pager
systemctl list-timers | grep -E "kmia|paper"
bash scripts/health_summary.sh
```

## How to Open the Console

Once started, the Web Console runs locally. To access it securely from another machine, open an SSH tunnel:

```bash
ssh -N -L 8502:127.0.0.1:8501 kmia
```

Then navigate to: [http://127.0.0.1:8502](http://127.0.0.1:8502)

## Safety Guarantee

**DRY-RUN / PAPER EVALUATION ONLY.**
**NO REAL TRADING EXECUTION.**

This script and all associated components strictly operate on simulated, paper-trading data. It does not place real Kalshi orders, execute API trades, or use authenticated credentials.

## Git Hygiene Check

The script includes a Git hygiene module that ensures generated runtime data does not clutter your repository. 
- Generated files under `backend/data/processed` are runtime outputs.
- It will list untracked files (`git status --short`) as a diagnostic warning.
- It safely cleans up old `paper_signal_*.json` files.
- It will **never** automatically commit, push, run `git reset`, or execute `git clean`.

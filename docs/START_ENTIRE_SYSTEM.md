# KMIA Kalshi Start Entire System

The `start_entire_system.sh` script provides a one-command initialization process to safely start the automated paper trading system.

## How to Run

```bash
bash scripts/start_entire_system.sh
```

## What it Starts

When executed, the script performs the following actions sequentially:
1. **Installs Dependencies:** Verifies and updates `requirements.txt`.
2. **Runs Tests:** Validates system integrity and mathematical safety.
3. **Updates Market Data:** Pulls the latest simulated snapshot.
4. **Generates Signals:** Evaluates edge and creates paper trading signals.
5. **Records Paper Trades:** Appends eligible simulated trades to the ledger.
6. **Settles Trades:** Checks official observations against open paper trades.
7. **Generates Status:** Builds the daily summary.
8. **Restarts Console:** Restarts the `kmia-web-console.service` to apply changes.
9. **Enables Timers:** Ensures automation timers are running.
10. **Runs Health Summary:** Prints the current operational status.

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

## How to Open the Console

Once started, the Web Console runs locally. To access it securely from another machine, open an SSH tunnel:

```bash
ssh -N -L 8502:127.0.0.1:8501 kmia
```

Then navigate to: [http://127.0.0.1:8502](http://127.0.0.1:8502)

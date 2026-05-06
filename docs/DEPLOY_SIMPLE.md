# Simple Deploy Guide

Use this when you changed code on the Mac and want the server updated.

## One command

Run from the Mac:

```bash
bash scripts/deploy_from_mac.sh
```

## What it does

1. Checks Git status
2. Pushes Mac code to GitHub
3. SSHs into the server
4. Pulls latest GitHub code on the server
5. Installs requirements
6. Runs tests
7. Updates Kalshi data
8. Generates paper signal
9. Restarts the web console
10. Checks health

## Open the console

```bash
ssh -N -L 8502:127.0.0.1:8501 kmia
```

Then open:

<http://127.0.0.1:8502>

## Safety

**DRY-RUN / PAPER EVALUATION ONLY.**

**NO REAL TRADING EXECUTION.**

The bot must not place real Kalshi orders.

# Mac to Server Deployment

The `deploy_from_mac.sh` script automates the safe, unidirectional deployment of the KMIA Kalshi paper-trading system from your local development machine (Mac) to the remote server (`hal`).

## Architecture and Safety Guarantee

**DRY-RUN / PAPER EVALUATION ONLY.**
**NO REAL TRADING EXECUTION.**

- **Mac is Development:** Code is written and tested locally.
- **GitHub is Source of Truth:** All changes flow through the `main` branch.
- **Server is Read-Only (Git):** The server only pulls from GitHub. It never pushes changes back to the repository. This prevents merge conflicts on the remote server and ensures a clean, auditable Git history.

## How to Run

Execute this script **only** from the root of the repository on your Mac:

```bash
bash scripts/deploy_from_mac.sh
```

## What the Script Does

1. **Environment Validation:** Verifies you are running from the Mac repository root (and refuses to run if the hostname is `hal`).
2. **Local Commits:** Checks for uncommitted changes and optionally commits them with a generic message.
3. **Pushes to GitHub:** Pushes local changes to the `main` branch.
4. **SSH into Server:** Connects securely to the `kmia` SSH host.
5. **Pulls Updates:** Runs `git pull --ff-only` on the server to retrieve the exact code you just pushed.
6. **Executes Validations:** Reinstalls dependencies, runs the test suite, and executes the paper-trading loop.
7. **Restarts Services:** Reboots the web console and automation timers.
8. **Health Check:** Verifies that the console is answering HTTP requests and runs the system health summary.

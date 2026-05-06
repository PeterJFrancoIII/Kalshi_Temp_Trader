# Sync Workflow: Mac <-> GitHub <-> Server

This document outlines the synchronization process for the Kalshi Temp Trader project.

## Important Disclaimer

**NO REAL TRADING EXECUTION**
This project is currently in RESEARCH_MVP status. Real-money trading is strictly forbidden.

## Source of Truth

The **GitHub `main` branch** is the absolute source of truth for all code and configuration.

## Environment Paths

- **Mac Development:** `/Users/computer/Desktop/App Development/Kalshi`
- **Server Deployment:** `/opt/kmia-kalshi`

## Fast Deploy (Recommended)

If you have already verified your changes on the Mac, you can use the [Simple Deploy Guide](DEPLOY_SIMPLE.md) to update the server in one command.

## Normal Workflow

### 1. Mac: Before Editing

Always sync your local Mac environment with GitHub before making changes.

```bash
cd "/Users/computer/Desktop/App Development/Kalshi"
git fetch origin
git status
git pull --ff-only origin main
```

### 2. Mac: After Editing

Push changes to GitHub once they are verified.

```bash
git status
git diff --stat
git add .
git commit -m "Describe the change"
git push origin main
```

### 3. Server: Update

Deploy the latest changes from GitHub to the production server.

```bash
ssh peterjfrancoiii@192.168.0.126
cd /opt/kmia-kalshi
git fetch origin
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
bash scripts/run_tests.sh
bash scripts/generate_daily_status.sh
sudo systemctl restart kmia-web-console.service
curl -I http://127.0.0.1:8501
```

## Verify Sync

To ensure all environments are aligned, verify the commit hashes match.

**Mac:**

```bash
git rev-parse HEAD
```

**Server:**

```bash
git rev-parse HEAD
```

The hashes must match exactly.

## Warnings & Constraints

- **Do Not Force Push:** Never use `git push --force`.
- **Clean State Required:** Do not pull updates if you have uncommitted local changes.
- **No Rsync:** Do not use `rsync` for normal workflows; it is reserved for emergency recovery only.
- **Git Hygiene:** Generated data files and local `.env` files should generally not be committed.
- **Secrets:** Keep all secrets out of Git; use `.env` files that are ignored.

## Troubleshooting

If synchronization fails, refer to the [Simple Troubleshooting Guide](TROUBLESHOOTING_SIMPLE.md).

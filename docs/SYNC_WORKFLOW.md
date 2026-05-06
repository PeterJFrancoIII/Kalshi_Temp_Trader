# Sync Workflow Guide

**NO REAL TRADING EXECUTION**
**DRY-RUN / PAPER EVALUATION ONLY**

This document outlines the approved method for synchronizing code between the local Mac development environment, GitHub, and the production Linux server.

## Overview

GitHub is the **source of truth**. All changes should be committed and pushed to GitHub before being pulled onto other environments. 

**DO NOT use rsync** as the standard sync method. Use Git for auditability and consistency.

## Sync Flow

### 1. Server to GitHub
If you made emergency configuration changes on the server (e.g., to `/opt/kmia-kalshi`):

```bash
cd /opt/kmia-kalshi
git status
git add .
git commit -m "Emergency server config update"
git push origin main
```

### 2. Mac Desktop from GitHub
To pull the latest changes onto your Mac:

```bash
cd "/Users/computer/Desktop/App Development/Kalshi"
git fetch origin
git status
git pull --ff-only origin main
```
*Note: If you have local changes on your Mac, use `git status` and `git diff` to review them before pulling. Do not overwrite local work without review.*

### 3. Server Update from GitHub
To update the production server with the latest code from GitHub:

```bash
cd /opt/kmia-kalshi
git fetch origin
git pull --ff-only origin main
sudo systemctl restart kmia-web-console.service
```

## Emergency Recovery
Only use `rsync` for first-time bootstrapping or emergency recovery when Git is unavailable.

---
**Security Note**: Ensure `.env` files and other secrets are listed in `.gitignore` to prevent them from being pushed to GitHub.

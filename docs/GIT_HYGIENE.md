# Git Hygiene Strategy

This document outlines the Git hygiene rules for the KMIA Kalshi project to ensure that generated reports, logs, snapshots, and test outputs do not clutter the repository or the `git status` output.

## Security & Safety

> [!IMPORTANT]
> **NO REAL TRADING EXECUTION.**
> This project is for **DRY-RUN / PAPER EVALUATION ONLY**.
> - Do not add real trading logic.
> - Do not add order execution.
> - Do not add API keys or private keys to the repository.

## Committed Files (Source of Truth)

The following types of files **MUST** be committed to GitHub:
- **Source Code**: All files in `backend/src/`.
- **Documentation**: All files in `docs/` and root `.md` files.
- **Tests**: All files in `backend/tests/` (except generated test outputs).
- **Scripts**: Maintenance and workflow scripts in `scripts/`.
- **Configuration**: Deployment templates in `deploy/systemd/`, `.agent` files, and `.gitignore`.
- **Canonical History**: `backend/data/processed/history/kmia_daily_history.jsonl` (Used as a baseline for comparisons).

## Ignored Files (Generated Artifacts)

Generated runtime and test outputs are **NOT** committed. These include:
- `backend/data/processed/status/*.json` / `*.md`
- `backend/data/processed/logs/*.log`
- `backend/data/processed/reports/*.md` / `*.html`
- `backend/data/processed/aggregate_calibration/*.json` / `*.md`
- `backend/data/processed/kalshi_market_snapshots/*.json`
- `backend/tests/test_reports/`
- `backend/tests/test_history.jsonl`
- `__pycache__/`, `*.pyc`, `.venv/`

## Syncing & Deployment

- GitHub remains the single source of truth for the codebase.
- Do not use `rsync` for normal synchronization of code; use Git.
- Use `scripts/update_server_from_github.sh` for deployment to production environments.

## Maintenance

Run `bash scripts/check_git_hygiene.sh` regularly to ensure no generated artifacts have been accidentally tracked by Git.

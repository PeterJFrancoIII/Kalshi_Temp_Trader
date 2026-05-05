# KMIA Daily Status Report

The Daily Status Report provides a high-level overview of the KMIA temperature prediction system's health, latest outputs, and calibration metrics.

## Generation

The report can be generated manually using the provided shell script:

```bash
bash scripts/generate_daily_status.sh
```

Or directly via the Python module:

```bash
python -m status.daily_status --date YYYY-MM-DD --output-dir backend/data/processed/status
```

### CLI Arguments

- `--date`: Target date in `YYYY-MM-DD` format. Defaults to the current system date.
- `--output-dir`: Directory where the reports will be saved. Defaults to `backend/data/processed/status`.

## Outputs

Every run generates two files in the output directory:
1. `kmia_daily_status_YYYY-MM-DD.json`: Machine-readable system status.
2. `kmia_daily_status_YYYY-MM-DD.md`: Human-readable summary report.

## Report Content

### 🛡️ Safety Status
Confirms that the system is operating in a read-only mode relative to Kalshi and that no real trading execution is enabled.

### 📈 Forecast Outputs
Lists the latest reports generated for the target date, including Rules V1, Rules V2 (Climatology), and Model Comparison reports.

### 🧪 Calibration Summary
Summarizes aggregate performance metrics like average Brier scores and model win rates.

### ⚙️ Workflow Log Status
Analyzes the latest workflow log for errors, warnings, or tracebacks, and provides a tail of the most recent log entries.

### ⚠️ Warnings
Highlights any missing data, failed workflow steps, or parsing errors detected during status generation.

import pytest
from pathlib import Path
from src.web_console import load_latest_forecast_summary

def test_load_latest_forecast_summary_parsing():
    """
    Verify that the regex in web_console.py correctly extracts forecast data.
    """
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    report_file = temp_dir / "test_forecast.md"
    report_content = """
# KMIA Forecast Report
## Core Estimates
- **Best Single-Number Estimate:** 82.5°F
- **Confidence:** HIGH
- **Forecast High:** 82.5°F

## Probability Bins
| Bin | Probability |
| :--- | :--- |
| <=78 | 5.0% |
| 79-80 | 10.0% |
| 81-82 | 45.0% |
| 83-84 | 30.0% |
| >=85 | 10.0% |
"""
    report_file.write_text(report_content)
    
    summary = load_latest_forecast_summary(report_file)
    
    assert summary["best_single_number"] == "82.5"
    assert "81-82" in summary["top_probability_bin"]
    assert "45.0%" in summary["top_probability_bin"]

def test_load_latest_forecast_summary_missing():
    """Verify safe return for missing file."""
    summary = load_latest_forecast_summary(Path("non_existent.md"))
    assert summary["best_single_number"] == "Unknown"
    assert summary["top_probability_bin"] == "Unknown"
    assert len(summary["warnings"]) > 0

def test_load_latest_forecast_summary_string_path():
    """Verify that it handles string paths as well."""
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    report_file = temp_dir / "test_string_path.md"
    report_file.write_text("- **Forecast High:** 77°F\n## Probability Bins\n| 77-78 | 100% |")
    
    summary = load_latest_forecast_summary(str(report_file))
    assert summary["best_single_number"] == "77"
    assert "77-78" in summary["top_probability_bin"]

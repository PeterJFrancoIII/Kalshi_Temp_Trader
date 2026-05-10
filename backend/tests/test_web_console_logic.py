# import pytest
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
def test_load_latest_forecast_summary_malformed():
    """Verify safe return for malformed content."""
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    report_file = temp_dir / "malformed.md"
    report_file.write_text("# Not a forecast\nJust some random text.")
    
    summary = load_latest_forecast_summary(report_file)
    assert isinstance(summary, dict)
    assert summary["best_single_number"] == "Unknown"
    assert summary["top_probability_bin"] == "Unknown"
    assert "malformed.md" in summary["source_file"]

def test_extract_best_signal():
    from src.web_console import extract_best_signal
    
    # Test with best_signal present
    p_data = {"best_signal": {"market_ticker": "T1"}}
    assert extract_best_signal(p_data)["market_ticker"] == "T1"
    
    # Test with signals fallback
    p_data = {"signals": [{"market_ticker": "T2"}]}
    assert extract_best_signal(p_data)["market_ticker"] == "T2"
    
    # Test with no signals
    p_data = {}
    assert extract_best_signal(p_data) is None
    
    # Test with invalid input
    assert extract_best_signal(None) is None

def test_aggregate_warnings():
    from src.web_console import aggregate_warnings
    
    p_data = {"warnings": ["W1"]}
    mkts = {"warnings": ["W2"]}
    n_data = {"warnings": ["W3"]}
    status_data = {"warnings": ["W4"]}
    
    all_w = aggregate_warnings(p_data, mkts, n_data, status_data)
    assert len(all_w) == 4
    assert "W1" in all_w
    assert "W2" in all_w
    assert "W3" in all_w
    assert "W4" in all_w
    
    # Test with missing warnings
    assert len(aggregate_warnings({}, {}, {}, {})) == 0

import os
import json

import tempfile
import shutil
from calibration.aggregate_reports import (
    aggregate_model_comparisons,
    write_aggregate_calibration_json,
    write_aggregate_calibration_markdown
)

def test_empty_comparison_list():
    """Empty comparison list returns settled_days=0 and warning."""
    result = aggregate_model_comparisons([])
    assert result["settled_days"] == 0
    assert "no comparison records" in result["warnings"]

def test_basic_aggregation():
    """Two deterministic comparison records aggregate metrics correctly."""
    records = [
        {
            "rules_v1": {"brier_score": 0.4, "log_loss": 0.8, "top_bin_hit": True, "actual_bin_probability": 0.5},
            "rules_v2_climatology": {"brier_score": 0.3, "log_loss": 0.7, "top_bin_hit": True, "actual_bin_probability": 0.6},
            "winner_by_brier": "rules_v2_climatology",
            "winner_by_log_loss": "rules_v2_climatology",
            "winner_by_top_bin": "tie",
            "brier_delta_v2_minus_v1": -0.1,
            "log_loss_delta_v2_minus_v1": -0.1
        },
        {
            "rules_v1": {"brier_score": 0.2, "log_loss": 0.4, "top_bin_hit": False, "actual_bin_probability": 0.3},
            "rules_v2_climatology": {"brier_score": 0.5, "log_loss": 0.9, "top_bin_hit": True, "actual_bin_probability": 0.2},
            "winner_by_brier": "rules_v1",
            "winner_by_log_loss": "rules_v1",
            "winner_by_top_bin": "rules_v2_climatology",
            "brier_delta_v2_minus_v1": 0.3,
            "log_loss_delta_v2_minus_v1": 0.5
        }
    ]
    
    result = aggregate_model_comparisons(records)
    
    assert result["settled_days"] == 2
    
    # Averages
    def approx_equal(a, b):
        return abs(a - b) < 1e-6

    assert approx_equal(result["v1_avg_brier"], (0.4 + 0.2) / 2)
    assert approx_equal(result["v2_avg_brier"], (0.3 + 0.5) / 2)
    assert approx_equal(result["v1_avg_log_loss"], (0.8 + 0.4) / 2)
    assert approx_equal(result["v2_avg_log_loss"], (0.7 + 0.9) / 2)
    
    # Hit rates
    assert result["v1_top_bin_hit_rate"] == 0.5
    assert result["v2_top_bin_hit_rate"] == 1.0
    
    # Win rates (v2)
    assert result["v2_win_rate_by_brier"] == 0.5
    assert result["v2_win_rate_by_log_loss"] == 0.5
    assert result["v2_win_rate_by_top_bin"] == 0.5
    
    # Probability averages
    assert approx_equal(result["avg_actual_bin_probability_v1"], (0.5 + 0.3) / 2)
    assert approx_equal(result["avg_actual_bin_probability_v2"], (0.6 + 0.2) / 2)
    
    # Deltas
    assert approx_equal(result["brier_delta_avg_v2_minus_v1"], (-0.1 + 0.3) / 2)
    assert approx_equal(result["log_loss_delta_avg_v2_minus_v1"], (-0.1 + 0.5) / 2)

def test_missing_optional_fields():
    """Missing optional fields do not crash but produce warnings."""
    # Record missing 'rules_v1' and 'rules_v2_climatology' sub-dicts
    records = [
        {"date": "2026-05-01"}
    ]
    
    result = aggregate_model_comparisons(records)
    assert result["settled_days"] == 1
    assert any("missing model details" in w for w in result["warnings"])
    
    # Should have 0.0 for metrics
    assert result["v1_avg_brier"] == 0.0
    assert result["v2_avg_brier"] == 0.0

def test_write_aggregate_json():
    """JSON writer creates a valid pretty JSON file."""
    tmp_dir = tempfile.mkdtemp()
    try:
        report = {
            "settled_days": 1,
            "v1_avg_brier": 0.5,
            "v2_avg_brier": 0.4
        }
        path = os.path.join(tmp_dir, "report.json")
        write_aggregate_calibration_json(report, path)
        
        assert os.path.exists(path)
        with open(path, "r") as f:
            data = json.load(f)
        assert data["settled_days"] == 1
        assert data["v1_avg_brier"] == 0.5
    finally:
        shutil.rmtree(tmp_dir)

def test_write_aggregate_markdown():
    """Markdown writer creates a file with key sections."""
    tmp_dir = tempfile.mkdtemp()
    try:
        report = {
            "settled_days": 5,
            "v1_avg_brier": 0.4567,
            "v2_avg_brier": 0.1234,
            "v1_avg_log_loss": 0.8,
            "v2_avg_log_loss": 0.6,
            "v1_top_bin_hit_rate": 0.6,
            "v2_top_bin_hit_rate": 0.8,
            "v2_win_rate_by_brier": 0.8,
            "v2_win_rate_by_log_loss": 0.6,
            "v2_win_rate_by_top_bin": 0.4,
            "brier_delta_avg_v2_minus_v1": -0.3333,
            "log_loss_delta_avg_v2_minus_v1": -0.2,
            "warnings": ["test warning"]
        }
        path = os.path.join(tmp_dir, "report.md")
        write_aggregate_calibration_markdown(report, path)
        
        assert os.path.exists(path)
        with open(path, "r") as f:
            content = f.read()
        
        assert "# Aggregate Model Calibration Report" in content
        assert "Settled Days" in content
        assert "5" in content
        assert "rules_v1" in content
        assert "rules_v2_climatology" in content
        assert "0.4567" in content
        assert "0.1234" in content
        assert "test warning" in content
        assert "Interpretation Notes" in content
    finally:
        shutil.rmtree(tmp_dir)

def test_writers_handle_empty_report():
    """Writers do not crash on empty/minimal reports."""
    tmp_dir = tempfile.mkdtemp()
    try:
        report = aggregate_model_comparisons([])
        
        json_path = os.path.join(tmp_dir, "empty.json")
        md_path = os.path.join(tmp_dir, "empty.md")
        
        write_aggregate_calibration_json(report, json_path)
        write_aggregate_calibration_markdown(report, md_path)
        
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
    finally:
        shutil.rmtree(tmp_dir)

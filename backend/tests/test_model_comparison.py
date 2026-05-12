import os
import json
import pytest
from src.calibration.comparison import (
    score_model_comparison, 
    write_comparison_json, 
    write_comparison_markdown,
    save_comparison_report
)

import os
import json
import pytest
from src.calibration.comparison import (
    score_model_comparison, 
    write_comparison_json, 
    write_comparison_markdown,
    save_comparison_report
)

def get_sample_predictions():
    v1_probs = {
        "<=78": 0.05, "79-80": 0.15, "81-82": 0.50, 
        "83-84": 0.20, "85-86": 0.05, ">=87": 0.05
    }
    v2_probs = {
        "<=78": 0.01, "79-80": 0.04, "81-82": 0.40, 
        "83-84": 0.45, "85-86": 0.09, ">=87": 0.01
    }
    return v1_probs, v2_probs

def test_score_model_comparison_enhanced_fields():
    v1_probs, v2_probs = get_sample_predictions()
    # Actual temp 82 -> actual bin 81-82
    report = score_model_comparison(v1_probs, v2_probs, 82, date_str="2026-05-03")
    
    # Check per-model fields
    assert report["rules_v1"]["model_name"] == "rules_v1"
    assert report["rules_v1"]["actual_bin"] == "81-82"
    assert report["rules_v1"]["actual_bin_probability"] == 0.50
    assert report["rules_v1"]["top_bin"] == "81-82"
    assert report["rules_v1"]["top_bin_probability"] == 0.50
    assert report["rules_v1"]["top_bin_hit"] is True
    
    assert report["rules_v2_climatology"]["model_name"] == "rules_v2_climatology"
    assert report["rules_v2_climatology"]["actual_bin"] == "81-82"
    assert report["rules_v2_climatology"]["actual_bin_probability"] == 0.40
    assert report["rules_v2_climatology"]["top_bin"] == "83-84"
    assert report["rules_v2_climatology"]["top_bin_probability"] == 0.45
    assert report["rules_v2_climatology"]["top_bin_hit"] is False

def test_winner_and_delta_logic():
    v1_probs, v2_probs = get_sample_predictions()
    report = score_model_comparison(v1_probs, v2_probs, 82)
    
    # v1 has higher prob for actual bin (0.5 vs 0.4) and hits top bin
    assert report["winner_by_brier"] == "rules_v1"
    assert report["winner_by_log_loss"] == "rules_v1"
    assert report["winner_by_top_bin"] == "rules_v1"
    
    # Deltas (v2 - v1). Since v1 is better, v2 should have higher score (Brier/LogLoss)
    assert report["brier_delta_v2_minus_v1"] > 0
    assert report["log_loss_delta_v2_minus_v1"] > 0

def test_tie_behavior():
    v1_probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.5, "83-84": 0.1, "85-86": 0.1, ">=87": 0.1}
    v2_probs = v1_probs.copy()
    
    report = score_model_comparison(v1_probs, v2_probs, 82)
    
    assert report["winner_by_brier"] == "tie"

    assert report["winner_by_log_loss"] == "tie"
    assert report["winner_by_top_bin"] == "tie"
    assert "tie" in report["summary"].lower()


def test_summary_string():
    v1_probs, v2_probs = get_sample_predictions()
    report = score_model_comparison(v1_probs, v2_probs, 82)
    
    summary = report["summary"]
    assert "rules_v1" in summary or "rules_v2_climatology" in summary
    assert "Brier" in summary
    assert "log loss" in summary.lower()

def test_report_writers(tmp_path=None):
    v1_probs, v2_probs = get_sample_predictions()
    report = score_model_comparison(v1_probs, v2_probs, 82, date_str="2026-05-03")
    
    if tmp_path:
        json_path = os.path.join(str(tmp_path), "report.json")
        md_path = os.path.join(str(tmp_path), "report.md")
    else:
        # Fallback for manual run (CWD is backend/ when run via run_tests.sh)
        test_dir = "data/test_reports"
        os.makedirs(test_dir, exist_ok=True)
        json_path = os.path.join(test_dir, "report.json")
        md_path = os.path.join(test_dir, "report.md")
    
    write_comparison_json(report, json_path)
    write_comparison_markdown(report, md_path)
    
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        assert data["actual_bin"] == "81-82"
        
    with open(md_path, 'r') as f:
        content = f.read()
        assert "rules_v1" in content
        assert "rules_v2_climatology" in content
        assert "81-82" in content

def test_legacy_save_comparison_report(tmp_path=None):
    v1_probs, v2_probs = get_sample_predictions()
    report = score_model_comparison(v1_probs, v2_probs, 82)

    if tmp_path:
        test_dir = str(tmp_path / "legacy")
    else:
        # CWD is backend/ when run via run_tests.sh
        test_dir = "data/test_reports/legacy"

    json_p, md_p = save_comparison_report(report, test_dir, "legacy_test")

    assert os.path.exists(json_p)
    assert os.path.exists(md_p)


def test_comparison_markdown_nonzero_probabilities():
    """P1 Fix 4: The per-bin Markdown table must show real non-zero probabilities."""
    v1_probs, v2_probs = get_sample_predictions()
    report = score_model_comparison(v1_probs, v2_probs, 82, date_str="2026-05-03")

    # Verify probability_bins are stored in each model summary
    assert "probability_bins" in report["rules_v1"], (
        "rules_v1 summary missing probability_bins key"
    )
    assert "probability_bins" in report["rules_v2_climatology"], (
        "rules_v2_climatology summary missing probability_bins key"
    )

    # Write the markdown and verify per-bin rows are non-zero
    # CWD is backend/ when run via run_tests.sh
    test_dir = "data/test_reports/prob_test"
    os.makedirs(test_dir, exist_ok=True)
    md_path = os.path.join(test_dir, "prob_test.md")
    write_comparison_markdown(report, md_path)

    with open(md_path, "r") as f:
        content = f.read()

    # The 81-82 row should show 0.5000 for v1 and 0.4000 for v2
    assert "0.5000" in content, (
        "Expected v1 probability 0.5000 in markdown table, got zeros."
    )
    assert "0.4000" in content, (
        "Expected v2 probability 0.4000 in markdown table, got zeros."
    )
    # Sanity: the actual bin marker should appear
    assert "81-82" in content

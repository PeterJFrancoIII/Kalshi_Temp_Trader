import os
from scheduler.settlement_check import settle_prediction_from_climia

def get_sample_content(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "samples", "climia", filename)
    with open(path, "r") as f:
        return f.read()

def test_settle_normal_82():
    # Mock prediction centered on 81-82
    mock_prediction = {
        "<=78": 0.05,
        "79-80": 0.15,
        "81-82": 0.50,
        "83-84": 0.20,
        "85-86": 0.05,
        ">=87": 0.05
    }
    
    # sample_normal.txt has 82F
    raw_text = get_sample_content("sample_normal.txt")
    
    summary = settle_prediction_from_climia(mock_prediction, raw_text)
    
    assert summary["final_max_temp_f"] == 82
    assert summary["actual_bin"] == "81-82"
    assert summary["top_predicted_bin"] == "81-82"
    assert summary["top_bin_hit"] is True
    assert "brier_score" in summary
    assert "log_loss" in summary

def test_settle_incomplete():
    mock_prediction = {b: 1/6 for b in ["<=78", "79-80", "81-82", "83-84", "85-86", ">=87"]}
    
    # sample_incomplete.txt has MM for temps
    raw_text = get_sample_content("sample_incomplete.txt")
    
    summary = settle_prediction_from_climia(mock_prediction, raw_text)
    
    assert "error" in summary
    assert "Could not find final temperature" in summary["error"]

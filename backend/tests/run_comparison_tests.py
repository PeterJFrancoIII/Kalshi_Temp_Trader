import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.calibration.comparison import (
    score_model_comparison, 
    write_comparison_json, 
    write_comparison_markdown
)

def test_score_model_comparison_logic():
    print("Testing enhanced score_model_comparison logic...")
    v1_probs = {
        "<=78": 0.05, "79-80": 0.15, "81-82": 0.50, 
        "83-84": 0.20, "85-86": 0.05, ">=87": 0.05
    }
    v2_probs = {
        "<=78": 0.01, "79-80": 0.04, "81-82": 0.40, 
        "83-84": 0.45, "85-86": 0.09, ">=87": 0.01
    }
    
    report = score_model_comparison(v1_probs, v2_probs, 82, date_str="2026-05-03")
    
    assert report["date"] == "2026-05-03"

    assert report["actual_bin"] == "81-82"
    
    # Check new fields
    assert report["rules_v1"]["actual_bin_probability"] == 0.50
    assert report["rules_v2_climatology"]["actual_bin_probability"] == 0.40
    assert report["winner_by_brier"] == "rules_v1"
    assert report["winner_by_log_loss"] == "rules_v1"
    assert report["winner_by_top_bin"] == "rules_v1"
    assert report["brier_delta_v2_minus_v1"] > 0
    assert "rules_v1 won by brier score and log loss" in report["summary"].lower()


    
    print("✓ score_model_comparison_logic passed")

def test_report_writers():
    print("Testing report writers...")
    v1_probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.6, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    v2_probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.5, "83-84": 0.2, "85-86": 0.1, ">=87": 0.0}
    
    report = score_model_comparison(v1_probs, v2_probs, 82, date_str="2026-05-03")
    
    test_dir = "backend/data/test_reports"
    os.makedirs(test_dir, exist_ok=True)
    json_path = os.path.join(test_dir, "test_comp.json")
    md_path = os.path.join(test_dir, "test_comp.md")
    
    write_comparison_json(report, json_path)
    write_comparison_markdown(report, md_path)
    
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)
    
    with open(md_path, 'r') as f:
        content = f.read()
        assert "rules_v1" in content
        assert "rules_v2_climatology" in content
    
    print(f"✓ report writers passed (files saved to {test_dir})")

if __name__ == "__main__":
    try:
        test_score_model_comparison_logic()
        test_report_writers()
        print("\nAll comparison agent tests passed successfully!")
    except Exception as e:
        print(f"\nTests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


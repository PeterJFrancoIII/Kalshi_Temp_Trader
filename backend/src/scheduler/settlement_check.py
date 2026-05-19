import argparse
import json
import os
from typing import Dict, Any, Optional

# Hard import: pydantic is required. Do not mock it.
# If this fails, install dependencies: pip install -r backend/requirements.txt
import pydantic  # noqa: F401  — validates environment on import

# Standard entrypoint: `python -m scheduler.settlement_check` with
# PYTHONPATH=backend/src (see scripts/settle_yesterday.sh).
from ingestion.climia_parser import get_settlement_max_temp
from calibration.metrics import score_prediction


def settle_prediction_from_climia(prediction_bins: Dict[str, float], raw_climia_text: str) -> Dict[str, Any]:
    """
    Extracts the final temperature from CLIMIA text and scores the prediction.
    """
    final_temp = get_settlement_max_temp(raw_climia_text)
    if final_temp is None:
        return {
            "error": "Could not find final temperature in CLIMIA report.",
            "raw_text_preview": raw_climia_text[:200] + "..."
        }
    
    return score_prediction(prediction_bins, final_temp)

def run_dry_run():
    """
    Executes a dry-run settlement using mock prediction and sample CLIMIA data.
    """
    print("--- CLIMIA Settlement Dry Run ---")
    
    # Mock prediction (centered around 81-82)
    mock_prediction = {
        "<=78": 0.05,
        "79-80": 0.15,
        "81-82": 0.50,
        "83-84": 0.20,
        "85-86": 0.05,
        ">=87": 0.05
    }
    
    # Load sample CLIMIA (sample_normal.txt has 82F)
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "samples", "climia", "sample_normal.txt")
    
    if not os.path.exists(sample_path):
        print(f"Error: Sample file not found at {sample_path}")
        return

    with open(sample_path, "r") as f:
        raw_text = f.read()
    
    print(f"Loading mock prediction: {json.dumps(mock_prediction, indent=2)}")
    print(f"Loading sample CLIMIA from: {os.path.basename(sample_path)}")
    
    summary = settle_prediction_from_climia(mock_prediction, raw_text)
    
    if "error" in summary:
        print(f"SETTLEMENT FAILED: {summary['error']}")
    else:
        print("\n--- Settlement Summary ---")
        print(f"Final Max Temp:  {summary['final_max_temp_f']} F")
        print(f"Actual Bin:      {summary['actual_bin']}")
        print(f"Predicted Bin:   {summary['top_predicted_bin']}")
        print(f"Top Bin Hit:     {summary['top_bin_hit']}")
        print(f"Brier Score:     {summary['brier_score']:.4f}")
        print(f"Log Loss:        {summary['log_loss']:.4f}")
        print("--------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KMIA Settlement Check")
    parser.add_argument("--dry-run", action="store_true", help="Run a dry-run settlement with mock data")
    
    args = parser.parse_args()
    
    if args.dry_run:
        run_dry_run()
    else:
        print("No live settlement implemented yet. Use --dry-run for testing.")

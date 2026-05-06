import json
import os
from pathlib import Path

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "manual_data_corrections.json"

def load_manual_corrections():
    """
    Loads the manual data corrections from the JSON config file.
    Fails safely if file is missing or invalid.
    """
    if not CONFIG_PATH.exists():
        return {}
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
            return data.get("dates", {})
    except Exception as e:
        # Never crash main workflow
        print(f"Warning: Failed to load manual corrections: {e}")
        return {}

def get_correction_for_date(date_str):
    """
    Returns the correction entry for a specific date (YYYY-MM-DD).
    """
    corrections = load_manual_corrections()
    return corrections.get(date_str, {})

def is_excluded_from_learning(date_str):
    """
    Returns True if the date should be excluded from learning/calibration.
    """
    correction = get_correction_for_date(date_str)
    return correction.get("exclude_from_learning", False)

def get_market_open_time_et(date_str):
    """
    Returns the market open time override (ET) if configured.
    """
    correction = get_correction_for_date(date_str)
    return correction.get("market_open_time_et")

if __name__ == "__main__":
    # Simple CLI test
    print(f"Loaded corrections: {load_manual_corrections()}")
    print(f"May 5 excluded: {is_excluded_from_learning('2026-05-05')}")
    print(f"May 7 open time: {get_market_open_time_et('2026-05-07')}")

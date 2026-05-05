import json
import os
from typing import List, Dict, Any, Optional
from features.climatology_features import prior_bin_distribution_for_date

from shared.types import REQUIRED_BINS

def load_history_records(path: str) -> List[Dict[str, Any]]:
    """
    Loads historical records from a JSONL file.
    """
    records = []
    if not os.path.exists(path):
        return []
        
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def climatology_prior_for_date(
    records: List[Dict[str, Any]], 
    target_date: str, 
    window_days: int = 7, 
    years_back: int = 30
) -> Dict[str, Any]:
    """
    Computes historical bin distribution for a target date.
    Returns a dict with 'probability_bins' and 'warnings'.
    """
    warnings = []
    if not records:
        # Fallback: Equal distribution with warning
        warnings.append("No historical records found. Using uniform fallback distribution.")
        return {
            "probability_bins": {b: round(1.0 / len(REQUIRED_BINS), 4) for b in REQUIRED_BINS},
            "warnings": warnings
        }
        
    dist = prior_bin_distribution_for_date(
        records=records,
        target_date=target_date,
        window_days=window_days,
        years_back=years_back
    )
    
    # Ensure all bins are present
    final_dist = {}
    for b in REQUIRED_BINS:
        final_dist[b] = dist.get(b, 0.0)
        
    # Check sum
    total = sum(final_dist.values())
    if total == 0:
        warnings.append(f"No historical records in window for {target_date}. Using uniform fallback.")
        return {
            "probability_bins": {b: round(1.0 / len(REQUIRED_BINS), 4) for b in REQUIRED_BINS},
            "warnings": warnings
        }
        
    # Re-normalize just in case
    final_dist = {b: round(prob / total, 4) for b, prob in final_dist.items()}
    
    return {
        "probability_bins": final_dist,
        "warnings": warnings
    }

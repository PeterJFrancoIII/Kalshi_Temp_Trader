import json
import os
from typing import Dict, Any, List, Optional

def safe_mean(values: List[float]) -> float:
    """Calculates the mean of a list of values, returning 0.0 if empty."""
    if not values:
        return 0.0
    return sum(values) / len(values)

def rate_true(values: List[bool]) -> float:
    """Calculates the rate of True values in a list, returning 0.0 if empty."""
    if not values:
        return 0.0
    return sum(1 for v in values if v) / len(values)

def count_winner(records: List[Dict[str, Any]], metric_key: str, model_name: str) -> float:
    """Calculates the win rate for a specific model name on a specific winner key."""
    if not records:
        return 0.0
    wins = sum(1 for r in records if r.get(metric_key) == model_name)
    return wins / len(records)

def aggregate_model_comparisons(comparison_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates a list of comparison records into a summary report.
    
    Each record is expected to have the structure defined in comparison.py.
    """
    warnings = []
    if not comparison_records:
        return {
            "settled_days": 0,
            "v1_avg_brier": 0.0,
            "v2_avg_brier": 0.0,
            "v1_avg_log_loss": 0.0,
            "v2_avg_log_loss": 0.0,
            "v1_top_bin_hit_rate": 0.0,
            "v2_top_bin_hit_rate": 0.0,
            "v2_win_rate_by_brier": 0.0,
            "v2_win_rate_by_log_loss": 0.0,
            "v2_win_rate_by_top_bin": 0.0,
            "avg_actual_bin_probability_v1": 0.0,
            "avg_actual_bin_probability_v2": 0.0,
            "brier_delta_avg_v2_minus_v1": 0.0,
            "log_loss_delta_avg_v2_minus_v1": 0.0,
            "warnings": ["no comparison records"]
        }

    settled_days = len(comparison_records)
    
    # Collect values for aggregation
    v1_briers = []
    v2_briers = []
    v1_log_losses = []
    v2_log_losses = []
    v1_top_hits = []
    v2_top_hits = []
    v1_actual_probs = []
    v2_actual_probs = []
    brier_deltas = []
    log_loss_deltas = []
    
    for i, record in enumerate(comparison_records):
        v1 = record.get("rules_v1")
        v2 = record.get("rules_v2_climatology")
        
        if not v1 or not v2:
            warnings.append(f"Record at index {i} missing model details")
            continue
            
        v1_briers.append(v1.get("brier_score", 0.0))
        v2_briers.append(v2.get("brier_score", 0.0))
        v1_log_losses.append(v1.get("log_loss", 0.0))
        v2_log_losses.append(v2.get("log_loss", 0.0))
        v1_top_hits.append(v1.get("top_bin_hit", False))
        v2_top_hits.append(v2.get("top_bin_hit", False))
        v1_actual_probs.append(v1.get("actual_bin_probability", 0.0))
        v2_actual_probs.append(v2.get("actual_bin_probability", 0.0))
        
        # Deltas
        if "brier_delta_v2_minus_v1" in record:
            brier_deltas.append(record["brier_delta_v2_minus_v1"])
        else:
            brier_deltas.append(v2.get("brier_score", 0.0) - v1.get("brier_score", 0.0))
            
        if "log_loss_delta_v2_minus_v1" in record:
            log_loss_deltas.append(record["log_loss_delta_v2_minus_v1"])
        else:
            log_loss_deltas.append(v2.get("log_loss", 0.0) - v1.get("log_loss", 0.0))

    return {
        "settled_days": settled_days,
        "v1_avg_brier": safe_mean(v1_briers),
        "v2_avg_brier": safe_mean(v2_briers),
        "v1_avg_log_loss": safe_mean(v1_log_losses),
        "v2_avg_log_loss": safe_mean(v2_log_losses),
        "v1_top_bin_hit_rate": rate_true(v1_top_hits),
        "v2_top_bin_hit_rate": rate_true(v2_top_hits),
        "v2_win_rate_by_brier": count_winner(comparison_records, "winner_by_brier", "rules_v2_climatology"),
        "v2_win_rate_by_log_loss": count_winner(comparison_records, "winner_by_log_loss", "rules_v2_climatology"),
        "v2_win_rate_by_top_bin": count_winner(comparison_records, "winner_by_top_bin", "rules_v2_climatology"),
        "avg_actual_bin_probability_v1": safe_mean(v1_actual_probs),
        "avg_actual_bin_probability_v2": safe_mean(v2_actual_probs),
        "brier_delta_avg_v2_minus_v1": safe_mean(brier_deltas),
        "log_loss_delta_avg_v2_minus_v1": safe_mean(log_loss_deltas),
        "warnings": warnings
    }

def write_aggregate_calibration_json(report: Dict[str, Any], path: str) -> None:
    """Writes the aggregate calibration report to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(report, f, indent=4, sort_keys=True)

def write_aggregate_calibration_markdown(report: Dict[str, Any], path: str) -> None:
    """Writes the aggregate calibration report to a Markdown file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    settled_days = report.get("settled_days", 0)
    
    md = f"""# Aggregate Model Calibration Report
**Settled Days**: {settled_days}

## Model Performance Comparison

| Metric | rules_v1 | rules_v2_climatology | Delta (v2-v1) |
| :--- | :--- | :--- | :--- |
| **Avg Brier Score** | {report.get('v1_avg_brier', 0.0):.4f} | {report.get('v2_avg_brier', 0.0):.4f} | {report.get('brier_delta_avg_v2_minus_v1', 0.0):.4f} |
| **Avg Log Loss** | {report.get('v1_avg_log_loss', 0.0):.4f} | {report.get('v2_avg_log_loss', 0.0):.4f} | {report.get('log_loss_delta_avg_v2_minus_v1', 0.0):.4f} |
| **Top-Bin Hit Rate** | {report.get('v1_top_bin_hit_rate', 0.0):.2%} | {report.get('v2_top_bin_hit_rate', 0.0):.2%} | - |
| **Avg Actual-Bin Prob** | {report.get('avg_actual_bin_probability_v1', 0.0):.4f} | {report.get('avg_actual_bin_probability_v2', 0.0):.4f} | - |

## Rules V2 Win Rates
*   **By Brier Score**: {report.get('v2_win_rate_by_brier', 0.0):.2%}
*   **By Log Loss**: {report.get('v2_win_rate_by_log_loss', 0.0):.2%}
*   **By Top-Bin Hit**: {report.get('v2_win_rate_by_top_bin', 0.0):.2%}

"""
    
    warnings = report.get("warnings", [])
    if warnings:
        md += "## Warnings\n"
        for w in warnings:
            md += f"*   {w}\n"
        md += "\n"
        
    md += "## Interpretation Notes\n"
    md += "A lower Brier Score and Log Loss indicate better predictive accuracy. "
    md += "A higher Top-Bin Hit Rate and Actual-Bin Probability indicate better calibration and confidence.\n"
    
    with open(path, 'w') as f:
        f.write(md)

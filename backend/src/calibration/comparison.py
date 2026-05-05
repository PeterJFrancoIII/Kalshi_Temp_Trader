import json
import os
from typing import Dict, Any, Optional
from calibration.metrics import score_prediction, REQUIRED_BINS

def score_model_comparison(
    v1_prediction: Dict[str, float], 
    v2_prediction: Dict[str, float], 
    final_max_temp_f: int,
    date_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compares two model predictions (v1 vs v2) against the ground truth.
    
    Args:
        v1_prediction: Dict of probabilities for Model v1 (rules_v1).
        v2_prediction: Dict of probabilities for Model v2 (rules_v2_climatology).
        final_max_temp_f: The actual recorded maximum temperature.
        date_str: Optional date string for the event.
        
    Returns:
        A dictionary containing enhanced scores for both models and comparison summary.
    """
    v1_scores = score_prediction(v1_prediction, final_max_temp_f)
    v2_scores = score_prediction(v2_prediction, final_max_temp_f)
    
    actual_bin = v1_scores["actual_bin"]
    
    # Helper to build model summary
    def build_model_summary(name: str, scores: Dict[str, Any], probs: Dict[str, float]) -> Dict[str, Any]:
        return {
            "model_name": name,
            "actual_bin": actual_bin,
            "actual_bin_probability": probs.get(actual_bin, 0.0),
            "top_bin": scores["top_predicted_bin"],
            "top_bin_probability": probs.get(scores["top_predicted_bin"], 0.0),
            "brier_score": scores["brier_score"],
            "log_loss": scores["log_loss"],
            "top_bin_hit": scores["top_bin_hit"],
            "probability_bins": probs,  # store original probs for markdown table
        }

    v1_summary = build_model_summary("rules_v1", v1_scores, v1_prediction)
    v2_summary = build_model_summary("rules_v2_climatology", v2_scores, v2_prediction)
    
    # Comparison logic
    tol = 1e-12
    
    winner_brier = "tie"
    if v1_summary["brier_score"] < v2_summary["brier_score"] - tol:
        winner_brier = "rules_v1"
    elif v2_summary["brier_score"] < v1_summary["brier_score"] - tol:
        winner_brier = "rules_v2_climatology"
        
    winner_log_loss = "tie"
    if v1_summary["log_loss"] < v2_summary["log_loss"] - tol:
        winner_log_loss = "rules_v1"
    elif v2_summary["log_loss"] < v1_summary["log_loss"] - tol:
        winner_log_loss = "rules_v2_climatology"
        
    winner_top_bin = "tie"
    if v1_summary["top_bin_hit"] and not v2_summary["top_bin_hit"]:
        winner_top_bin = "rules_v1"
    elif v2_summary["top_bin_hit"] and not v1_summary["top_bin_hit"]:
        winner_top_bin = "rules_v2_climatology"

    # Human-readable summary
    summary_parts = []
    
    # Brier/Log Loss win
    if winner_brier == "rules_v2_climatology" and winner_log_loss == "rules_v2_climatology":
        summary_parts.append("rules_v2_climatology won by Brier score and log loss")
    elif winner_brier == "rules_v1" and winner_log_loss == "rules_v1":
        summary_parts.append("rules_v1 won by Brier score and log loss")
    elif winner_brier == "tie" and winner_log_loss == "tie":
        summary_parts.append("the models tied on Brier score and log loss")
    else:
        if winner_brier == "tie":
            summary_parts.append("the models tied on Brier score")
        else:
            summary_parts.append(f"{winner_brier} won by Brier score")
            
        if winner_log_loss == "tie":
            summary_parts.append("the models tied on log loss")
        else:
            summary_parts.append(f"{winner_log_loss} won by log loss")
            
    # Top bin
    if winner_top_bin == "tie":
        if v1_summary["top_bin_hit"]:
            summary_parts.append("both models hit the top bin")
        else:
            summary_parts.append("neither model hit the top bin")
    else:
        summary_parts.append(f"only {winner_top_bin} hit the top bin")
        
    # Actual bin probability
    if abs(v2_summary["actual_bin_probability"] - v1_summary["actual_bin_probability"]) < tol:
        summary_parts.append("both assigned equal probability to the actual bin")
    elif v2_summary["actual_bin_probability"] > v1_summary["actual_bin_probability"]:
        summary_parts.append("rules_v2_climatology assigned higher probability to the actual bin")
    else:
        summary_parts.append("rules_v2_climatology assigned lower probability to the actual bin")
        
    summary_text = "; ".join(summary_parts)
    if summary_text:
        summary_text = summary_text[0].upper() + summary_text[1:] + "."
    else:
        # Should not happen with current parts but safe fallback
        summary_text = "The models tied on all metrics."



    comparison = {
        "date": date_str,
        "final_max_temp_f": final_max_temp_f,
        "actual_bin": actual_bin,
        "rules_v1": v1_summary,
        "rules_v2_climatology": v2_summary,
        "winner_by_brier": winner_brier,
        "winner_by_log_loss": winner_log_loss,
        "winner_by_top_bin": winner_top_bin,
        "brier_delta_v2_minus_v1": v2_summary["brier_score"] - v1_summary["brier_score"],
        "log_loss_delta_v2_minus_v1": v2_summary["log_loss"] - v1_summary["log_loss"],
        "summary": summary_text,
        # Maintain legacy structure for backward compatibility
        "v1": v1_scores,
        "v2": v2_scores,
    }
    return comparison

def write_comparison_json(report: Dict[str, Any], path: str) -> None:
    """Writes the comparison report to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(report, f, indent=4)

def write_comparison_markdown(report: Dict[str, Any], path: str) -> None:
    """Writes the comparison report to a Markdown file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    v1 = report["rules_v1"]
    v2 = report["rules_v2_climatology"]
    
    md = f"""# Model Comparison Report
**Date**: {report.get('date') or 'N/A'}
**Final Max Temp**: {report['final_max_temp_f']}°F
**Actual Bin**: `{report['actual_bin']}`

## Metrics Comparison

| Metric | rules_v1 | rules_v2_climatology | Winner | Delta (v2-v1) |
| :--- | :--- | :--- | :--- | :--- |
| **Brier Score** | {v1['brier_score']:.4f} | {v2['brier_score']:.4f} | {report['winner_by_brier']} | {report['brier_delta_v2_minus_v1']:.4f} |
| **Log Loss** | {v1['log_loss']:.4f} | {v2['log_loss']:.4f} | {report['winner_by_log_loss']} | {report['log_loss_delta_v2_minus_v1']:.4f} |
| **Top Bin Hit** | {'✅' if v1['top_bin_hit'] else '❌'} | {'✅' if v2['top_bin_hit'] else '❌'} | {report['winner_by_top_bin']} | - |
| **Actual Bin Prob** | {v1['actual_bin_probability']:.4f} | {v2['actual_bin_probability']:.4f} | - | - |

## Prediction Details

| Bin | rules_v1 | rules_v2_climatology | Actual |
| :--- | :--- | :--- | :--- |
"""
    # Read probability distributions stored in each model's summary dict.
    v1_probs = report["rules_v1"].get("probability_bins", {})
    v2_probs = report["rules_v2_climatology"].get("probability_bins", {})
    
    for b in REQUIRED_BINS:
        v1_p = v1_probs.get(b, 0.0)
        v2_p = v2_probs.get(b, 0.0)
        actual_marker = "🎯" if b == report["actual_bin"] else ""
        md += f"| {b} | {v1_p:.4f} | {v2_p:.4f} | {actual_marker} |\n"
        
    md += f"""
## Summary
{report['summary']}
"""
    with open(path, 'w') as f:
        f.write(md)

def generate_markdown_report(comparison: Dict[str, Any]) -> str:
    """Legacy wrapper for generate_markdown_report."""
    # Create a temporary path to use the new writer and read it back, 
    # or just implement a string version. Let's implement string version to avoid IO.
    v1 = comparison.get("rules_v1", comparison.get("v1"))
    v2 = comparison.get("rules_v2_climatology", comparison.get("v2"))
    
    # Minimal version for compatibility
    report = f"""# Model Comparison Report
**Date/Event**: {comparison.get('date') or 'N/A'}
**Final Max Temp**: {comparison['final_max_temp_f']}°F
**Actual Bin**: `{comparison['actual_bin']}`

| Metric | Model V1 | Model V2 | Winner |
| :--- | :--- | :--- | :--- |
| **Brier Score** | {v1['brier_score']:.4f} | {v2['brier_score']:.4f} | {comparison.get('winner_by_brier', 'N/A')} |
| **Log Loss** | {v1['log_loss']:.4f} | {v2['log_loss']:.4f} | {comparison.get('winner_by_log_loss', 'N/A')} |
"""
    return report

def save_comparison_report(comparison: Dict[str, Any], directory: str, filename_prefix: str):
    """Legacy wrapper for save_comparison_report."""
    json_path = os.path.join(directory, f"{filename_prefix}.json")
    md_path = os.path.join(directory, f"{filename_prefix}.md")
    write_comparison_json(comparison, json_path)
    write_comparison_markdown(comparison, md_path)
    return json_path, md_path


import os
import json
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional

def get_latest_file(pattern: str) -> Optional[str]:
    """Returns the latest file matching the pattern by modification time."""
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def build_daily_status(
    target_date: str | None = None,
    reports_dir: str = "backend/data/processed/reports",
    aggregate_dir: str = "backend/data/processed/aggregate_calibration",
    logs_dir: str = "backend/data/processed/logs",
    paper_trading_dir: str | None = None
) -> dict:
    """
    Builds a daily status report summarizing the latest system activity.
    """
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    warnings = []
    
    # Identify latest reports for target_date
    v1_pattern = os.path.join(reports_dir, f"kmia_forecast_{target_date}_rules_v1_*.md")
    v2_pattern = os.path.join(reports_dir, f"kmia_forecast_{target_date}_rules_v2_climatology_*.md")
    comp_pattern = os.path.join(reports_dir, f"kmia_comparison_{target_date}_*.md")
    
    latest_v1 = get_latest_file(v1_pattern)
    latest_v2 = get_latest_file(v2_pattern)
    latest_comp = get_latest_file(comp_pattern)
    
    if not latest_v1: warnings.append(f"Missing V1 report for {target_date}")
    if not latest_v2: warnings.append(f"Missing V2 report for {target_date}")
    if not latest_comp: warnings.append(f"Missing comparison report for {target_date}")

    # Parse aggregate calibration if present
    agg_json_path = os.path.join(aggregate_dir, "aggregate_calibration.json")
    agg_md_path = os.path.join(aggregate_dir, "aggregate_calibration.md")
    agg_data = {}
    if os.path.exists(agg_json_path):
        try:
            with open(agg_json_path, 'r') as f:
                agg_data = json.load(f)
        except Exception as e:
            warnings.append(f"Failed to parse aggregate calibration JSON: {e}")
    else:
        warnings.append("Missing aggregate calibration JSON")

    # Analyze latest workflow log for target_date
    log_pattern = os.path.join(logs_dir, f"kmia_daily_workflow_{target_date}.log")
    latest_log = get_latest_file(log_pattern)
    log_info = {
        "latest_log_path": latest_log,
        "tail": "",
        "contains_error": False,
        "contains_warning": False,
        "contains_traceback": False
    }
    
    if latest_log:
        try:
            with open(latest_log, 'r') as f:
                lines = f.readlines()
                log_info["tail"] = "".join(lines[-10:])
                full_text = "".join(lines)
                if "ERROR" in full_text: log_info["contains_error"] = True
                if "WARNING" in full_text: log_info["contains_warning"] = True
                if "Traceback" in full_text: log_info["contains_traceback"] = True
        except Exception as e:
            warnings.append(f"Failed to read log file: {e}")
    else:
        warnings.append(f"Missing workflow log for {target_date}")

    # Determine system status
    system_status = "OK"
    if log_info["contains_error"] or log_info["contains_traceback"]:
        system_status = "ERROR"
    elif log_info["contains_warning"] or not latest_v2 or not latest_v1:
        system_status = "WARN"

    # Assemble status dictionary
    status = {
        "date": target_date,
        "station": "KMIA",
        "metric": "daily_max_temperature_f",
        "system_status": system_status,
        "forecast": {
            "latest_v2_report": latest_v2,
            "latest_v1_report": latest_v1,
            "latest_comparison_report": latest_comp,
            "summary": "Reports generated" if latest_v2 else "No reports found"
        },
        "aggregate_calibration": {
            "json_path": agg_json_path if os.path.exists(agg_json_path) else None,
            "markdown_path": agg_md_path if os.path.exists(agg_md_path) else None,
            "settled_days": agg_data.get("settled_days", 0),
            "v1_avg_brier": agg_data.get("v1_avg_brier"),
            "v2_avg_brier": agg_data.get("v2_avg_brier"),
            "v2_win_rate_by_brier": agg_data.get("v2_win_rate_by_brier")
        },
        "workflow_log": log_info,
        "paper_trading": {
            "available": False,
            "summary": "not implemented or no records found"
        },
        "safety": {
            "real_trading_enabled": False,
            "note": "No real trading execution is implemented."
        },
        "warnings": warnings
    }
    
    return status
def format_status_as_markdown(status: dict) -> str:
    """Formats the status dictionary as a human-readable Markdown string."""
    date = status["date"]
    system_status = status["system_status"]
    
    # Status emoji mapping
    status_emoji = {"OK": "✅", "WARN": "⚠️", "ERROR": "❌"}.get(system_status, "❓")
    
    md = [
        f"# KMIA Daily Status Report - {date}",
        f"**System Status:** {status_emoji} {system_status}",
        f"**Station:** {status['station']} | **Metric:** {status['metric']}",
        "",
        "## 🛡️ Safety Status",
        f"- **Real Trading Enabled:** {status['safety']['real_trading_enabled']}",
        f"- **Note:** {status['safety']['note']}",
        "",
        "## 📈 Forecast Outputs",
        f"- **Rules V2 (Climatology):** {status['forecast']['latest_v2_report'] or 'None'}",
        f"- **Rules V1 (Heuristic):** {status['forecast']['latest_v1_report'] or 'None'}",
        f"- **Model Comparison:** {status['forecast']['latest_comparison_report'] or 'None'}",
        f"- **Summary:** {status['forecast']['summary']}",
        "",
        "## 🧪 Calibration Summary",
        f"- **Settled Days:** {status['aggregate_calibration']['settled_days']}",
        f"- **V1 Avg Brier Score:** {status['aggregate_calibration']['v1_avg_brier'] or 'N/A'}",
        f"- **V2 Avg Brier Score:** {status['aggregate_calibration']['v2_avg_brier'] or 'N/A'}",
        f"- **V2 Win Rate:** {status['aggregate_calibration']['v2_win_rate_by_brier'] or '0.0%'}",
        "",
        "## ⚙️ Workflow Log Status",
        f"- **Latest Log:** {status['workflow_log']['latest_log_path'] or 'None'}",
        f"- **Contains Errors:** {status['workflow_log']['contains_error']}",
        f"- **Contains Warnings:** {status['workflow_log']['contains_warning']}",
        f"- **Traceback Found:** {status['workflow_log']['contains_traceback']}",
        "",
        "### Log Tail (Last 10 lines):",
        "```",
        status['workflow_log']['tail'] or "No log content available.",
        "```",
        "",
        "## 🧪 Paper Trading",
        f"- **Available:** {status['paper_trading']['available']}",
        f"- **Summary:** {status['paper_trading']['summary']}",
        ""
    ]
    
    if status["warnings"]:
        md.append("## ⚠️ Warnings")
        for warning in status["warnings"]:
            md.append(f"- {warning}")
        md.append("")
        
    return "\n".join(md)

def write_status_report(status: dict, output_dir: str) -> List[str]:
    """Writes the status report to JSON and Markdown files."""
    os.makedirs(output_dir, exist_ok=True)
    date = status["date"]
    
    json_path = os.path.join(output_dir, f"kmia_daily_status_{date}.json")
    md_path = os.path.join(output_dir, f"kmia_daily_status_{date}.md")
    
    # Write JSON
    with open(json_path, 'w') as f:
        json.dump(status, f, indent=4)
        
    # Write Markdown
    md_content = format_status_as_markdown(status)
    with open(md_path, 'w') as f:
        f.write(md_content)
        
    return [json_path, md_path]

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate KMIA Daily Status Report")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--output-dir", type=str, default="backend/data/processed/status", 
                        help="Directory to save the status reports")
    
    args = parser.parse_args()
    
    # Resolve absolute paths if necessary (optional, but good for CLI)
    # For simplicity, we'll use the relative paths as they work from project root
    
    status_dict = build_daily_status(target_date=args.date)
    paths = write_status_report(status_dict, args.output_dir)
    
    print("Daily status report generated:")
    for p in paths:
        print(f"- {p}")


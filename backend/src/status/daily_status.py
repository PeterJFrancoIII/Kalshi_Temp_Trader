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
    paper_trading_dir: str | None = None,
    nws_snapshot_path: str | None = None
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

    # Load and assess NWS snapshot
    from weather.nws_snapshot_contract import assess_nws_snapshot
    nws_data = None
    if nws_snapshot_path and os.path.exists(nws_snapshot_path):
        try:
            with open(nws_snapshot_path, 'r') as f:
                nws_data = json.load(f)
        except Exception as e:
            warnings.append(f"Failed to load NWS snapshot JSON from {nws_snapshot_path}: {e}")
            
    try:
        weather_gate = assess_nws_snapshot(nws_data)
    except Exception as e:
        warnings.append(f"Failed to assess NWS snapshot: {e}")
        weather_gate = {
            "available": False,
            "allow_paper_recommendations": False,
            "status": "ERROR",
            "no_trade_reason": f"Assessment failed: {e}",
            "warnings": [f"Assessment failed: {e}"],
            "latest_observation_time": None,
            "fetched_at_utc": None,
            "observation_age_minutes": None
        }

    # Append any weather gate warnings
    if weather_gate.get("warnings"):
        warnings.extend(weather_gate["warnings"])

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

    # Degrade system status based on weather gate
    gate_status = weather_gate.get("status", "UNKNOWN")
    if gate_status == "ERROR":
        system_status = "ERROR"
    elif gate_status in ("STALE", "MISSING") and system_status != "ERROR":
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
        "weather_gate": weather_gate,
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
    
    # Weather freshness details
    gate = status.get("weather_gate", {})
    gate_status = gate.get("status", "UNKNOWN")
    gate_emoji = {"OK": "🟢", "STALE": "🟡", "ERROR": "🔴", "MISSING": "⚪"}.get(gate_status, "❓")
    allow_recommendations = gate.get("allow_paper_recommendations", False)
    allow_emoji = "✅ ALLOWED" if allow_recommendations else "❌ BLOCKED"
    
    age = gate.get("observation_age_minutes")
    age_str = f"{age:.1f} minutes" if age is not None else "N/A"
    
    md = [
        f"# KMIA Daily Status Report - {date}",
        f"**System Status:** {status_emoji} {system_status}",
        f"**Station:** {status.get('station', 'KMIA')} | **Metric:** {status.get('metric', 'Max Temperature')}",
        "",
        "## 🛡️ Safety Status",
        f"- **Real Trading Enabled:** {status.get('safety', {}).get('real_trading_enabled', False)}",
        f"- **Note:** {status.get('safety', {}).get('note', 'No real trading execution is implemented.')}",
        "",
        "### 🌤️ Weather Freshness (NWS Gate)",
        f"- **Gate Status:** {gate_emoji} {gate_status}",
        f"- **Allowance Status:** {allow_emoji}",
        f"- **No-Trade Reason:** {gate.get('no_trade_reason') or 'None'}",
        f"- **Observation Age:** {age_str}",
        f"- **Latest Observation Time:** {gate.get('latest_observation_time') or 'N/A'}",
        f"- **Fetched At Time (UTC):** {gate.get('fetched_at_utc') or 'N/A'}"
    ]
    
    if gate.get("warnings"):
        md.append("- **Gate Warnings:**")
        for w in gate["warnings"]:
            md.append(f"  - {w}")
    
    md.extend([
        "",
        "## 📈 Forecast Outputs",
        f"- **Rules V2 (Climatology):** {status.get('forecast', {}).get('latest_v2_report', 'None')}",
        f"- **Rules V1 (Heuristic):** {status.get('forecast', {}).get('latest_v1_report', 'None')}",
        f"- **Model Comparison:** {status.get('forecast', {}).get('latest_comparison_report', 'None')}",
        f"- **Summary:** {status.get('forecast', {}).get('summary', 'N/A')}",
        "",
        "## 🧪 Calibration Summary",
        f"- **Settled Days:** {status.get('aggregate_calibration', {}).get('settled_days', 0)}",
        f"- **V1 Avg Brier Score:** {status.get('aggregate_calibration', {}).get('v1_avg_brier', 'N/A')}",
        f"- **V2 Avg Brier Score:** {status.get('aggregate_calibration', {}).get('v2_avg_brier', 'N/A')}",
        f"- **V2 Win Rate:** {status.get('aggregate_calibration', {}).get('v2_win_rate_by_brier', '0.0%')}",
        "",
        "## ⚙️ Workflow Log Status",
        f"- **Latest Log:** {status.get('workflow_log', {}).get('latest_log_path', 'None')}",
        f"- **Contains Errors:** {status.get('workflow_log', {}).get('contains_error', False)}",
        f"- **Contains Warnings:** {status.get('workflow_log', {}).get('contains_warning', False)}",
        f"- **Traceback Found:** {status.get('workflow_log', {}).get('contains_traceback', False)}",
        "",
        "### Log Tail (Last 10 lines):",
        "```",
        status.get('workflow_log', {}).get('tail') or "No log content available.",
        "```",
        "",
        "## 🧪 Paper Trading",
        f"- **Available:** {status.get('paper_trading', {}).get('available', False)}",
        f"- **Summary:** {status.get('paper_trading', {}).get('summary', 'N/A')}",
        ""
    ])
    
    if status["warnings"]:
        md.append("## ⚠️ Warnings")
        for warning in status["warnings"]:
            md.append(f"- {warning}")
        md.append("")
        
    return "\n".join(md)

def write_daily_status_json(status: dict, path: str) -> None:
    """Writes the status report as a JSON file to the specified path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(status, f, indent=4)

def write_daily_status_markdown(status: dict, path: str) -> None:
    """Writes the status report formatted as Markdown to the specified path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    md_content = format_status_as_markdown(status)
    with open(path, 'w') as f:
        f.write(md_content)

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


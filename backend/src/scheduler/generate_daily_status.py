import os
import json
import glob
from datetime import datetime
from typing import Dict, List, Optional

from shared.artifact_paths import (
    REPORTS_DIR,
    CALIBRATION_DIR,
    LOGS_DIR,
    STATUS_DIR,
    PAPER_TRADING_DIR,
    LATEST_PAPER_SIGNAL,
    PAPER_LEDGER_FILE,
    AGGREGATE_CALIBRATION_JSON,
    LATEST_NWS_KMIA_SNAPSHOT
)

def get_latest_file(pattern: str) -> Optional[str]:
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def get_daily_status():
    today = datetime.now().strftime('%Y-%m-%d')
    os.makedirs(STATUS_DIR, exist_ok=True)
    
    status = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "safety_status": "SECURE", # KMIA system is strictly read-only by design
        "forecasts": {},
        "comparison": None,
        "calibration": None,
        "workflow": {
            "last_log": None,
            "status": "UNKNOWN"
        },
        "paper_trading": {
            "available": os.path.exists(PAPER_LEDGER_FILE),
            "record_count": 0,
            "latest_signal": os.path.basename(LATEST_PAPER_SIGNAL) if os.path.exists(LATEST_PAPER_SIGNAL) else None
        },
        "warnings": []
    }
    
    # 1. Latest Forecasts
    # Expecting: kmia_forecast_YYYY-MM-DD_rules_v1_HHMMSS.md
    v1_pattern = os.path.join(REPORTS_DIR, f"kmia_forecast_{today}_rules_v1_*.md")
    v2_pattern = os.path.join(REPORTS_DIR, f"kmia_forecast_{today}_rules_v2_climatology_*.md")
    
    latest_v1 = get_latest_file(v1_pattern)
    latest_v2 = get_latest_file(v2_pattern)
    
    if latest_v1:
        status["forecasts"]["v1"] = os.path.basename(latest_v1)
    if latest_v2:
        status["forecasts"]["v2"] = os.path.basename(latest_v2)
        
    # 2. Latest Comparison
    comp_pattern = os.path.join(REPORTS_DIR, f"kmia_comparison_{today}_*.md")
    latest_comp = get_latest_file(comp_pattern)
    if latest_comp:
        status["comparison"] = os.path.basename(latest_comp)
        
    # 3. Aggregate Calibration
    if os.path.exists(AGGREGATE_CALIBRATION_JSON):
        with open(AGGREGATE_CALIBRATION_JSON, 'r') as f:
            status["calibration"] = json.load(f)

    # 3b. Load and assess NWS snapshot
    from weather.nws_snapshot_contract import assess_nws_snapshot
    nws_data = None
    if os.path.exists(LATEST_NWS_KMIA_SNAPSHOT):
        try:
            with open(LATEST_NWS_KMIA_SNAPSHOT, 'r') as f:
                nws_data = json.load(f)
        except Exception as e:
            status["warnings"].append(f"Failed to load NWS snapshot JSON from {LATEST_NWS_KMIA_SNAPSHOT}: {e}")
            
    try:
        weather_gate = assess_nws_snapshot(nws_data)
    except Exception as e:
        status["warnings"].append(f"Failed to assess NWS snapshot: {e}")
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

    status["weather_gate"] = weather_gate
    
    if weather_gate.get("warnings"):
        status["warnings"].extend(weather_gate["warnings"])
        
    # 4. Workflow Log
    log_pattern = os.path.join(LOGS_DIR, f"kmia_daily_workflow_{today}.log")
    latest_log = get_latest_file(log_pattern)
    if latest_log:
        status["workflow"]["last_log"] = os.path.basename(latest_log)
        with open(latest_log, 'r') as f:
            log_content = f.read()
            if "Workflow Completed" in log_content:
                status["workflow"]["status"] = "SUCCESS"
            elif "Workflow Started" in log_content:
                status["workflow"]["status"] = "IN_PROGRESS"
            else:
                status["workflow"]["status"] = "FAILED"
                
    # 5. Paper Trading
    if status["paper_trading"]["available"]:
        try:
            with open(PAPER_LEDGER_FILE, 'r') as f:
                ledger_data = json.load(f)
                status["paper_trading"]["record_count"] = len(ledger_data.get("trades", []))
        except Exception:
            status["paper_trading"]["record_count"] = 0

    best_sig_decision = "N/A"
    best_sig_reason = "None"
    best_sig_edge = "N/A"
    if os.path.exists(LATEST_PAPER_SIGNAL):
        try:
            with open(LATEST_PAPER_SIGNAL, 'r') as f:
                sig_data = json.load(f)
                best_sig = sig_data.get("best_signal")
                if best_sig:
                    rd = best_sig.get("risk_decision")
                    if isinstance(rd, dict):
                        best_sig_decision = "PASS" if rd.get("passed", True) else "BLOCK"
                        best_sig_reason = rd.get("no_trade_reason") or rd.get("reason") or "None"
                    else:
                        best_sig_decision = str(rd) if rd else "N/A"
                        best_sig_reason = best_sig.get("no_trade_reason") or "None"
                    
                    edge_val = best_sig.get("edge")
                    if edge_val is None:
                        edge_val = best_sig.get("executable_edge")
                    if edge_val is not None:
                        best_sig_edge = f"{edge_val*100:.1f}%" if isinstance(edge_val, (int, float)) else str(edge_val)
        except Exception:
            pass

    status["paper_trading"]["best_signal_risk_decision"] = best_sig_decision
    status["paper_trading"]["best_signal_no_trade_reason"] = best_sig_reason
    status["paper_trading"]["best_signal_executable_edge"] = best_sig_edge
            
    # 6. Warnings
    if not latest_v1 and not latest_v2:
        status["warnings"].append("No forecasts generated today.")
    if not latest_comp:
        status["warnings"].append("No model comparison generated today.")
    if status["workflow"]["status"] == "FAILED":
        status["warnings"].append("Last daily workflow execution failed.")
        
    return status

def write_json_status(status: Dict):
    today = status["date"]
    output_path = os.path.join(STATUS_DIR, f"kmia_daily_status_{today}.json")
    with open(output_path, 'w') as f:
        json.dump(status, f, indent=4)
    return output_path

def write_markdown_status(status: Dict):
    today = status["date"]
    output_path = os.path.join(STATUS_DIR, f"kmia_daily_status_{today}.md")
    
    cal = status.get("calibration") or {}
    v1_brier = cal.get("v1_avg_brier", "N/A")
    v2_brier = cal.get("v2_avg_brier", "N/A")
    settled = cal.get("settled_days", 0)
    
    # Weather freshness details
    gate = status.get("weather_gate", {})
    gate_status = gate.get("status", "UNKNOWN")
    gate_emoji = {"OK": "🟢", "STALE": "🟡", "ERROR": "🔴", "MISSING": "⚪"}.get(gate_status, "❓")
    allow_recommendations = gate.get("allow_paper_recommendations", False)
    allow_emoji = "✅ ALLOWED" if allow_recommendations else "❌ BLOCKED"
    
    age = gate.get("observation_age_minutes")
    age_str = f"{age:.1f} minutes" if age is not None else "N/A"
    
    md = [
        f"# KMIA Daily Status Report - {today}",
        f"**Generated:** {status['timestamp']}",
        "",
        "## 🛡️ Safety Status",
        f"**Status:** {status['safety_status']}",
        "- Read-only Kalshi integration verified.",
        "- No real trading execution code found.",
        "- No real trading execution is implemented.",
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
        "## 📈 Latest Outputs",
        f"- **Rules V1 Forecast:** {status['forecasts'].get('v1', 'None')}",
        f"- **Rules V2 Forecast:** {status['forecasts'].get('v2', 'None')}",
        f"- **Model Comparison:** {status.get('comparison', 'None')}",
        "",
        "## 🧪 Calibration Summary",
        f"- **Settled Days:** {settled}",
        f"- **V1 Avg Brier Score:** {v1_brier}",
        f"- **V2 Avg Brier Score:** {v2_brier}",
        "",
        "## ⚙️ Operational Status",
        f"- **Daily Workflow:** {status['workflow']['status']}",
        f"- **Latest Log:** {status['workflow']['last_log'] or 'None'}",
        f"- **Paper Trading Available:** {status['paper_trading']['available']}",
        f"- **Paper Trading Records:** {status['paper_trading']['record_count']}",
        f"- **Best Signal Risk Decision:** {status['paper_trading'].get('best_signal_risk_decision', 'N/A')}",
        f"- **Best Signal No-Trade Reason:** {status['paper_trading'].get('best_signal_no_trade_reason', 'None')}",
        f"- **Best Signal Executable Edge:** {status['paper_trading'].get('best_signal_executable_edge', 'N/A')}",
        ""
    ])
    
    if status["warnings"]:
        md.append("## ⚠️ Warnings")
        for warning in status["warnings"]:
            md.append(f"- {warning}")
        md.append("")
        
    with open(output_path, 'w') as f:
        f.write("\n".join(md))
    return output_path

if __name__ == "__main__":
    status = get_daily_status()
    json_path = write_json_status(status)
    md_path = write_markdown_status(status)
    print(f"Daily status report generated:")
    print(f"- {json_path}")
    print(f"- {md_path}")

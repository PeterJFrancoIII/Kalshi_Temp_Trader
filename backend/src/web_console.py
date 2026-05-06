import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

st.set_page_config(
    page_title="KMIA Weather Console",
    page_icon="🌦️",
    layout="wide"
)

# Resolution of Paths
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data" / "processed"
STATUS_DIR = DATA / "status"
REPORTS_DIR = DATA / "reports"
LOGS_DIR = DATA / "logs"
CAL_DIR = DATA / "aggregate_calibration"
HISTORY_FILE = DATA / "history" / "kmia_daily_history.jsonl"

def get_latest_file(directory, pattern):
    files = list(Path(directory).glob(pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def load_text(path):
    if path and path.exists():
        with open(path, 'r') as f:
            return f.read()
    return None

def load_json(path):
    if path and path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return None

# UI Header
st.title("KMIA Kalshi Weather Console")
st.error("🚨 **DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION**")

# Discovery
latest_status_json = get_latest_file(STATUS_DIR, "kmia_daily_status_*.json")
latest_status_md = get_latest_file(STATUS_DIR, "kmia_daily_status_*.md")
latest_forecast_md = get_latest_file(REPORTS_DIR, "kmia_forecast_*.md")
latest_comparison_md = get_latest_file(REPORTS_DIR, "kmia_comparison_*.md")
latest_log = get_latest_file(LOGS_DIR, "kmia_daily_workflow_*.log")
agg_cal_json = CAL_DIR / "aggregate_calibration.json"
agg_cal_md = CAL_DIR / "aggregate_calibration.md"

# Sidebar Metrics
st.sidebar.header("System Overview")
st.sidebar.metric("Station", "KMIA")
st.sidebar.metric("Mode", "Paper Evaluation")

if latest_status_json:
    st.sidebar.success("✅ Status File Found")
else:
    st.sidebar.error("❌ Status File Missing")

if latest_forecast_md:
    st.sidebar.success("✅ Forecast File Found")
else:
    st.sidebar.error("❌ Forecast File Missing")

st.sidebar.divider()
st.sidebar.info(f"**Project Root:** `{ROOT}`")
st.sidebar.info(f"**Last Dashboard Refresh:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Main Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Status", "Forecast", "Model Comparison", "Calibration", "Logs", "Files", "Operator Notes"
])

with tab1:
    st.header("Latest System Status")
    if latest_status_json:
        data = load_json(latest_status_json)
        st.json(data)
    elif latest_status_md:
        content = load_text(latest_status_md)
        st.markdown(content)
    else:
        st.warning("No status reports found. Run `bash scripts/generate_daily_status.sh` to generate one.")

with tab2:
    st.header("Latest Forecast Report")
    content = load_text(latest_forecast_md)
    if content:
        st.markdown(content)
    else:
        st.warning("No forecast reports found. Run `bash scripts/run_kmia_daily_workflow.sh` to generate one.")

with tab3:
    st.header("Latest Model Comparison")
    content = load_text(latest_comparison_md)
    if content:
        st.markdown(content)
    else:
        st.info("No comparison reports available yet.")

with tab4:
    st.header("Aggregate Calibration")
    if agg_cal_json.exists():
        cal_data = load_json(agg_cal_json)
        st.json(cal_data)
    elif agg_cal_md.exists():
        content = load_text(agg_cal_md)
        st.markdown(content)
    else:
        st.info("Aggregate calibration data not found.")

with tab5:
    st.header("Latest Workflow Logs")
    if latest_log:
        st.text(f"File: {latest_log}")
        content = load_text(latest_log)
        if content:
            st.code(content[-10000:], language="text")
    else:
        st.info("No workflow logs found.")

with tab6:
    st.header("Discovered Files")
    file_info = []
    for d in [STATUS_DIR, REPORTS_DIR, LOGS_DIR, CAL_DIR]:
        for f in d.glob("*"):
            if f.is_file():
                file_info.append({
                    "Name": f.name,
                    "Path": str(f.relative_to(ROOT)),
                    "Updated": datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    if file_info:
        df = pd.DataFrame(file_info)
        st.table(df.sort_values(by="Updated", ascending=False))
    else:
        st.info("No files discovered in processed data directories.")

with tab7:
    st.header("Operator Notes & Commands")
    st.markdown("""
    ### Daily Workflow
    To refresh forecasts and calibration:
    ```bash
    bash scripts/run_kmia_daily_workflow.sh
    ```

    ### Status Generation
    To regenerate the dashboard data:
    ```bash
    bash scripts/generate_daily_status.sh
    ```

    ### System Testing
    To verify code safety and logic:
    ```bash
    bash scripts/run_tests.sh
    ```

    ---
    **Security Notice**: This console is read-only. No trading actions can be performed from this interface.
    """)

st.divider()
st.caption("KMIA Kalshi Predictor — Dry-Run Evaluation System")

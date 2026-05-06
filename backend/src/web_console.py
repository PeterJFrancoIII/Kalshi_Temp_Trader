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
KALSHI_DIR = DATA / "kalshi_market_snapshots"
HISTORY_FILE = DATA / "history" / "kmia_daily_history.jsonl"

def get_latest_file(directory, pattern):
    if not directory.exists():
        return None
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

import re

def load_latest_forecast_summary(report_path):
    """
    Extracts today's forecast and top bin from the latest markdown report.
    """
    if not report_path or not report_path.exists():
        return "Unknown", "Unknown"
    
    content = load_text(report_path)
    if not content:
        return "Unknown", "Unknown"
    
    forecast_val = "Unknown"
    top_bin = "Unknown"
    
    # Extract Best Single Number
    # Look for: **Best Single-Number Estimate:** 85°F or **Forecast High:** 85°F
    sn_match = re.search(r"\*\*(?:Best Single-Number Estimate|Forecast High):\*\*\s*([\d.]+)", content)
    if sn_match:
        forecast_val = sn_match.group(1)
        
    # Extract Probability Bins
    bin_section = re.search(r"## Probability Bins(.*?)(?:##|\Z)", content, re.DOTALL)
    if bin_section:
        # Match table rows: | 85-86 | 37.2% |
        rows = re.findall(r"\|\s*([^|]+?)\s*\|\s*([\d.]+)%\s*\|", bin_section.group(1))
        bins = []
        for b_label, b_prob in rows:
            try:
                bins.append((b_label.strip(), float(b_prob)))
            except ValueError:
                continue
        
        if bins:
            # Sort by probability descending
            bins.sort(key=lambda x: x[1], reverse=True)
            top_bin = f"{bins[0][0]} ({bins[0][1]}%)"
            
    return forecast_val, top_bin

# UI Header
st.title("KMIA Kalshi Weather Console")
st.error("🚨 **DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION**")

# Discovery
latest_status_json = get_latest_file(STATUS_DIR, "kmia_daily_status_*.json")
latest_status_md = get_latest_file(STATUS_DIR, "kmia_daily_status_*.md")
# Specific discovery for the primary model reports
latest_forecast_md = get_latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.md")
if not latest_forecast_md:
    latest_forecast_md = get_latest_file(REPORTS_DIR, "kmia_forecast_*.md")

latest_comparison_md = get_latest_file(REPORTS_DIR, "kmia_comparison_*.md")
latest_kalshi_json = KALSHI_DIR / "latest_kalshi_market_snapshot.json"
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

# --- OPERATOR HOME SUMMARY ---
st.header("🏠 Operator Home")

# Initialize state
system_status = "GREEN"
status_color = "success"
action_needed = "None. System is working."
forecast_val = "Unknown"
top_bin = "Unknown"
kalshi_status = "CONNECTED"
kalshi_msg = "Market data is up to date."

# Check for Red Flags
if not latest_status_json or not latest_forecast_md or not DATA.exists():
    system_status = "RED"
    status_color = "error"
    action_needed = "Run: bash scripts/run_kmia_daily_workflow.sh"

# Check logs for Error
log_content = load_text(latest_log) or ""
if "ERROR" in log_content:
    system_status = "RED"
    status_color = "error"
    action_needed = "Check latest workflow log for ERROR details."

# Check for Yellow Flags (if not already Red)
if system_status != "RED":
    if not agg_cal_json.exists():
        system_status = "YELLOW"
        status_color = "warning"
        action_needed = "Calibration data missing. Run the daily workflow."
    
    if "WARNING" in log_content:
        system_status = "YELLOW"
        status_color = "warning"
        action_needed = "Review warnings in the Logs tab."

    if latest_kalshi_json.exists():
        mkts = load_json(latest_kalshi_json)
        if mkts.get("selected_temperature_markets"):
            kalshi_status = "CONNECTED"
        elif mkts.get("total_markets_returned", 0) > 0:
            system_status = "YELLOW"
            status_color = "warning"
            kalshi_status = "CONNECTED (No Miami Markets)"
            action_needed = "Kalshi discovery found general markets, but no matching Miami temperature market. Review ticker/series manually."
        else:
            system_status = "YELLOW"
            status_color = "warning"
            kalshi_status = "CONNECTED (0 Markets)"
            action_needed = "Kalshi discovery returned 0 results. Review search terms in config."
    else:
        system_status = "YELLOW"
        status_color = "warning"
        kalshi_status = "MISSING"
        action_needed = "Run: bash scripts/update_kalshi_market_data.sh"

# Extract Forecast Info
# Try Status JSON first
if latest_status_json:
    status_data = load_json(latest_status_json)
    forecast_info = status_data.get("forecast", {})
    if not forecast_info:
        # Fallback to the 'forecasts' dict if 'forecast' is missing
        f_dict = status_data.get("forecasts", {})
        if f_dict:
            # Pick first available or specific model
            forecast_info = f_dict.get("rules_v2_climatology") or next(iter(f_dict.values()))
            
    if forecast_info:
        forecast_val = str(forecast_info.get("best_single_number", "Unknown"))
        top_bin = forecast_info.get("top_probability_bin", "Unknown")

# Fallback to Markdown parsing if still Unknown
if forecast_val == "Unknown" or top_bin == "Unknown":
    f_val, t_bin = load_latest_forecast_summary(latest_forecast_md)
    if forecast_val == "Unknown":
        forecast_val = f_val
    if top_bin == "Unknown":
        top_bin = t_bin

# Display Summary Cards
col1, col2, col3 = st.columns(3)
with col1:
    if system_status == "GREEN":
        st.success(f"### SYSTEM STATUS: {system_status}")
    elif system_status == "YELLOW":
        st.warning(f"### SYSTEM STATUS: {system_status}")
    else:
        st.error(f"### SYSTEM STATUS: {system_status}")

with col2:
    st.metric("TODAY'S FORECAST", f"{forecast_val}°F")
    st.write(f"**Top Bin:** {top_bin}")
    if latest_forecast_md:
        st.caption(f"Source: {latest_forecast_md.name}")

with col3:
    st.metric("KALSHI MARKET", kalshi_status)
    last_upd = "N/A"
    if latest_kalshi_json.exists():
        last_upd = datetime.fromtimestamp(latest_kalshi_json.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
    st.write(f"**Last Updated:** {last_upd}")

st.info(f"👉 **ACTION NEEDED:** {action_needed}")

# Answers to the 4 Questions
with st.expander("❓ Quick System FAQ", expanded=True):
    q1_icon = "✅" if system_status != "RED" else "❌"
    st.write(f"**1. Is the system working?** {q1_icon} {system_status}")
    st.write(f"**2. What is today's forecast?** {forecast_val}°F (Bin: {top_bin})")
    has_warns = "Yes" if "WARNING" in log_content or system_status == "YELLOW" else "No"
    st.write(f"**3. Are there any warnings?** {has_warns}")
    st.write(f"**4. What should I do?** {action_needed}")

st.divider()

# Main Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Status", "Forecast", "Kalshi Market Data", "Model Comparison", "Calibration", "Logs", "Files", "Operator Notes"
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
    st.header("Kalshi Market Data")
    st.warning("ℹ️ **READ-ONLY PUBLIC MARKET DATA — NO REAL TRADING EXECUTION**")
    
    if latest_kalshi_json.exists():
        market_data = load_json(latest_kalshi_json)
        st.write(f"**Latest Snapshot:** {market_data.get('fetched_at_utc', 'N/A')}")
        
        found_count = market_data.get("markets_found", 0)
        if found_count == 0:
            st.warning("⚠️ **YELLOW: No Miami/KMIA Kalshi temperature market selected yet.**")
            st.info("To fix this, add a known Kalshi market ticker or series ticker to `backend/config/kalshi_market_discovery.json`.")
            st.markdown("[View Setup Guide](file:///Users/computer/Desktop/App%20Development/Kalshi/docs/KALSHI_MANUAL_TICKER_SETUP.md)")
        else:
            st.success(f"✅ {found_count} markets selected.")

        # Manual Tracking Info
        with st.expander("Tracking Metadata", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Known Tickers Used:**", market_data.get("known_market_tickers_used", []))
                st.write("**Known Series Used:**", market_data.get("known_series_tickers_used", []))
            with col_b:
                st.write("**Missing Tickers:**", market_data.get("missing_known_tickers", []))
                st.write("**Missing Series:**", market_data.get("missing_known_series", []))
            
            st.write("**Manual Matches:**", len(market_data.get("manual_matches", [])))
            st.write("**Next Action:**", market_data.get("next_action", "N/A"))

        markets = market_data.get("markets", [])
        if markets:
            display_data = []
            for m in markets:
                display_data.append({
                    "Ticker": m.get("ticker"),
                    "Title": m.get("title"),
                    "Subtitle": m.get("subtitle"),
                    "Last Price": m.get("last_price"),
                    "Yes Bid": m.get("yes_bid"),
                    "Yes Ask": m.get("yes_ask")
                })
            st.dataframe(pd.DataFrame(display_data))
        else:
            st.info("No temperature markets currently tracked.")
    else:
        st.warning("No Kalshi market snapshots found.")
        st.info("Run the following command to update market data:")
        st.code("bash scripts/update_kalshi_market_data.sh")

with tab4:
    st.header("Latest Model Comparison")
    content = load_text(latest_comparison_md)
    if content:
        st.markdown(content)
    else:
        st.info("No comparison reports available yet.")

with tab5:
    st.header("Aggregate Calibration")
    if agg_cal_json.exists():
        cal_data = load_json(agg_cal_json)
        st.json(cal_data)
    elif agg_cal_md.exists():
        content = load_text(agg_cal_md)
        st.markdown(content)
    else:
        st.info("Aggregate calibration data not found.")

with tab6:
    st.header("Latest Workflow Logs")
    if latest_log:
        st.text(f"File: {latest_log}")
        content = load_text(latest_log)
        if content:
            st.code(content[-10000:], language="text")
    else:
        st.info("No workflow logs found.")

with tab7:
    st.header("Discovered Files")
    file_info = []
    for d in [STATUS_DIR, REPORTS_DIR, LOGS_DIR, CAL_DIR, KALSHI_DIR]:
        if d.exists():
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

with tab8:
    st.header("Operator Notes & Commands")
    st.markdown("""
    ### Daily Workflow
    To refresh forecasts and calibration:
    ```bash
    bash scripts/run_kmia_daily_workflow.sh
    ```

    ### Market Data
    To update read-only Kalshi market data:
    ```bash
    bash scripts/update_kalshi_market_data.sh
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
    **Operator Notice**: If market discovery finds 0 matching markets, the system status will show as **YELLOW**. This is an advisory state, not a system failure.
    
    **Security Notice**: This console is read-only. No trading actions can be performed from this interface. **NO REAL TRADING EXECUTION.**
    """)

st.divider()
st.caption("KMIA Kalshi Predictor — Dry-Run Evaluation System")

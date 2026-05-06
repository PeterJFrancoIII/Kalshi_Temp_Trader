import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import re

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

# Resolution of Paths
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data" / "processed"
STATUS_DIR = DATA / "status"
REPORTS_DIR = DATA / "reports"
LOGS_DIR = DATA / "logs"
CAL_DIR = DATA / "aggregate_calibration"
KALSHI_DIR = DATA / "kalshi_market_snapshots"
HISTORY_FILE = DATA / "history" / "kmia_daily_history.jsonl"
PAPER_DIR = DATA / "paper_trading"
LEARNING_DIR = DATA / "learning"
NWS_DIR = DATA / "weather_nws"

try:
    from shared.manual_corrections import load_manual_corrections
except ImportError:
    def load_manual_corrections(): return {}

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

def load_latest_forecast_summary(report_path):
    """
    Extracts today's forecast and top bin from the latest markdown report.
    Returns a dict with status keys.
    """
    res = {
        "best_single_number": "Unknown",
        "top_probability_bin": "Unknown",
        "source_file": str(report_path) if report_path else None,
        "warnings": []
    }

    if not report_path:
        return res

    # Convert to Path if it's a string
    if isinstance(report_path, str):
        # If it's just a filename, assume it's in REPORTS_DIR
        if not os.path.isabs(report_path) and "/" not in report_path:
            report_path = REPORTS_DIR / report_path
        else:
            report_path = Path(report_path)

    if not report_path.exists():
        res["warnings"].append(f"Report file not found: {report_path.name}")
        return res
    
    content = load_text(report_path)
    if not content:
        res["warnings"].append(f"Report file empty: {report_path.name}")
        return res
    
    # Extract Best Single Number
    sn_match = re.search(r"\*\*(?:Best Single-Number Estimate|Forecast High):\*\*\s*([\d.]+)", content)
    if sn_match:
        res["best_single_number"] = sn_match.group(1)
        
    # Extract Probability Bins
    bin_section = re.search(r"## Probability Bins(.*?)(?:##|\Z)", content, re.DOTALL)
    if bin_section:
        rows = re.findall(r"\|\s*([^|]+?)\s*\|\s*([\d.]+)%\s*\|", bin_section.group(1))
        bins = []
        for b_label, b_prob in rows:
            try:
                bins.append((b_label.strip(), float(b_prob)))
            except ValueError:
                continue
        
        if bins:
            bins.sort(key=lambda x: x[1], reverse=True)
            res["top_probability_bin"] = f"{bins[0][0]} ({bins[0][1]}%)"
            
    return res

if __name__ == "__main__":
    st.set_page_config(
        page_title="KMIA Weather Console",
        page_icon="🌦️",
        layout="wide"
    )

    st.title("KMIA Kalshi Weather Console")
    st.error("🚨 **DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION**")

    # Discovery
    latest_status_json = get_latest_file(STATUS_DIR, "kmia_daily_status_*.json")
    latest_status_md = get_latest_file(STATUS_DIR, "kmia_daily_status_*.md")
    latest_forecast_md = get_latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.md")
    if not latest_forecast_md:
        latest_forecast_md = get_latest_file(REPORTS_DIR, "kmia_forecast_*.md")

    latest_comparison_md = get_latest_file(REPORTS_DIR, "kmia_comparison_*.md")
    latest_kalshi_json = KALSHI_DIR / "latest_kalshi_market_snapshot.json"
    latest_log = get_latest_file(LOGS_DIR, "kmia_daily_workflow_*.log")
    agg_cal_json = CAL_DIR / "aggregate_calibration.json"
    agg_cal_md = CAL_DIR / "aggregate_calibration.md"

    # Weather Data Ingestion Status
    WEATHER_INGESTION_DIR = DATA / "weather_ingestion"
    latest_weather_json = WEATHER_INGESTION_DIR / "latest_weather_ingestion_status.json"
    latest_nws_json = NWS_DIR / "latest_nws_kmia_snapshot.json"

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
    forecast_val = "Unknown"
    top_bin = "Unknown"
    weather_live = "Unknown"
    kalshi_status = "Unknown"
    system_status = "GREEN"
    status_color = "success"
    action_needed = "None. System is working."
    w_data = load_json(latest_weather_json) if latest_weather_json and latest_weather_json.exists() else {}

    if w_data:
        weather_live = "✅ CONNECTED" if not w_data.get("is_stale") else "⚠️ STALE"
    else:
        weather_live = "❌ MISSING"

    n_data = load_json(latest_nws_json) if latest_nws_json and latest_nws_json.exists() else {}
    if n_data:
        nws_live = "✅ CONNECTED" if not n_data.get("stale_data") else "⚠️ STALE"
    else:
        nws_live = "❌ MISSING"

    # Evaluate System Health
    if not latest_status_json or not latest_forecast_md or (w_data and w_data.get("is_stale")) or (n_data and n_data.get("stale_data")):
        system_status = "YELLOW"
        status_color = "warning"
        action_needed = "Review missing files or stale weather data."
    
    # Kalshi Status
    if latest_kalshi_json.exists():
        mkts = load_json(latest_kalshi_json)
        if mkts.get("selected_temperature_markets"):
            kalshi_status = "CONNECTED"
        elif mkts.get("total_markets_returned", 0) > 0:
            system_status = "YELLOW"
            status_color = "warning"
            kalshi_status = "CONNECTED (No Miami Markets)"
            action_needed = "Kalshi discovery found general markets, but no matching Miami temperature market."
        else:
            system_status = "YELLOW"
            status_color = "warning"
            kalshi_status = "CONNECTED (0 Markets)"
            action_needed = "Kalshi discovery returned 0 results."
    else:
        system_status = "YELLOW"
        status_color = "warning"
        kalshi_status = "MISSING"
        action_needed = "Run: bash scripts/update_kalshi_market_data.sh"

    # Extract Forecast Info
    status_data = load_json(latest_status_json) if latest_status_json else None
    if isinstance(status_data, dict):
        forecast_info = status_data.get("forecast", {})
        if not forecast_info:
            f_dict = status_data.get("forecasts", {})
            if isinstance(f_dict, dict):
                forecast_info = f_dict.get("rules_v2_climatology") or (next(iter(f_dict.values())) if f_dict else {})
                
        if forecast_info:
            if isinstance(forecast_info, str):
                summary = load_latest_forecast_summary(forecast_info)
                forecast_val = summary.get("best_single_number", "Unknown")
                top_bin = summary.get("top_probability_bin", "Unknown")
            elif isinstance(forecast_info, dict):
                forecast_val = str(forecast_info.get("best_single_number", "Unknown"))
                top_bin = forecast_info.get("top_probability_bin", "Unknown")
    
    # Fallback to direct markdown parsing if status info is incomplete
    if forecast_val == "Unknown" or top_bin == "Unknown":
        summary = load_latest_forecast_summary(latest_forecast_md)
        forecast_val = summary.get("best_single_number", "Unknown")
        top_bin = summary.get("top_probability_bin", "Unknown")

    # Display Summary Cards
    col1, col2, col3, col4 = st.columns(4)
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

    with col3:
        st.metric("WEATHER INGESTION", weather_live)
        if w_data:
            st.write(f"**Temp:** {w_data.get('current_temp_f', 'N/A')}°F")
        st.metric("NWS LIVE DATA", nws_live)
        if n_data:
            st.write(f"**Live Temp:** {n_data.get('current_temp_f', 'N/A')}°F")

    with col4:
        st.metric("KALSHI MARKET", kalshi_status)
        last_upd = "N/A"
        if latest_kalshi_json.exists():
            last_upd = datetime.fromtimestamp(latest_kalshi_json.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        st.write(f"**Last Updated:** {last_upd}")

    # --- PREDICTION QUALITY SUMMARY ---
    pq_json = LEARNING_DIR / "latest_prediction_quality_report.json"
    pq_data = load_json(pq_json) if pq_json.exists() else {}
    
    if pq_data:
        st.divider()
        st.subheader("🎯 Prediction Quality: " + pq_data.get("prediction_quality", "Unknown"))
        pq_col1, pq_col2, pq_col3 = st.columns(3)
        with pq_col1:
            st.write(f"**Main Risk:** {pq_data.get('main_risk', 'None')}")
        with pq_col2:
            st.write(f"**Next Action:** {pq_data.get('next_action', 'N/A')}")
        with pq_col3:
            st.write(f"**Best Paper Signal:** `{pq_data.get('best_paper_signal', 'None')}`")
        
        if pq_data.get("data_quality_warnings"):
            st.warning(" | ".join(pq_data["data_quality_warnings"]))

    # Paper Loop Data
    latest_paper_json = PAPER_DIR / "latest_paper_signal.json"
    p_data = load_json(latest_paper_json) if latest_paper_json.exists() else {}
    
    LEDGER_FILE = PAPER_DIR / "paper_trade_ledger.jsonl"
    open_paper_trades = 0
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE, "r") as f:
            open_paper_trades = sum(1 for line in f if line.strip())

    PERF_FILE = PAPER_DIR / "latest_paper_trading_performance.json"
    perf = load_json(PERF_FILE) if PERF_FILE.exists() else {}
    pending_settlements = perf.get("pending_trades", 0)
    settled_trades = perf.get("total_settled_trades", 0)
    sim_pnl = perf.get("total_simulated_pnl", 0)

    paper_loop_status = "Active" if p_data else "Missing Data"
    
    best_sig = p_data.get("best_signal")
    if isinstance(best_sig, dict):
        latest_signal_action = best_sig.get("paper_action", "Unknown")
    else:
        latest_signal_action = "Unknown"

    if system_status != "GREEN":
        next_action = "Check logs"
    elif pending_settlements > 0:
        next_action = "Wait for official KMIA settlement"
    elif open_paper_trades == 0:
        next_action = "Wait for next signal"
    else:
        next_action = "Wait for official KMIA settlement"

    st.divider()
    st.subheader("🔄 Paper Loop Status")
    
    pl_col1, pl_col2, pl_col3, pl_col4 = st.columns(4)
    with pl_col1:
        st.metric("Paper Loop", paper_loop_status)
        st.write(f"**Latest Signal:** `{latest_signal_action}`")
    with pl_col2:
        st.metric("Open Paper Trades", open_paper_trades)
        st.write(f"**Pending Settlements:** {pending_settlements}")
    with pl_col3:
        st.metric("Settled Trades", settled_trades)
        st.write(f"**Simulated PnL:** ${sim_pnl:.2f}")
    with pl_col4:
        st.metric("Next Action", "Pending" if pending_settlements > 0 else "Ready")
        st.info(next_action)

    # --- LEARNING SUMMARY ---
    latest_learning_json = LEARNING_DIR / "latest_learning_summary.json"
    l_data = load_json(latest_learning_json) if latest_learning_json.exists() else {}
    
    st.divider()
    st.subheader("🎓 Learning Summary")
    
    l_col1, l_col2, l_col3, l_col4 = st.columns(4)
    with l_col1:
        st.metric("Learning Status", "Active" if l_data else "No Data")
        st.write(f"**Trade Date:** {l_data.get('trade_date', 'N/A')}")
    with l_col2:
        st.metric("Win Rate", f"{l_data.get('win_rate', 0):.1%}")
        st.write(f"**Settled Trades:** {l_data.get('settled_trades', 0)}")
    with l_col3:
        st.metric("Simulated PnL", f"${l_data.get('simulated_pnl', 0.0):.2f}")
        st.write(f"**Model Lesson:** {l_data.get('model_lesson', 'Collecting more data...')}")
    with l_col4:
        st.metric("Next Action", "Monitor" if l_data else "Generate")
        st.success(l_data.get('next_action', "Run generate_learning_summary.sh"))

    # --- MANUAL DATA CORRECTIONS ---
    corrections = load_manual_corrections()
    if corrections:
        st.divider()
        st.subheader("🛠️ Manual Data Corrections")
        for date, details in corrections.items():
            status_text = details.get("settlement_status", "Active")
            excluded = " (Excluded from Learning)" if details.get("exclude_from_learning") else ""
            open_time = f" | Market Open: {details['market_open_time_et']} ET" if details.get("market_open_time_et") else ""
            st.write(f"**{date}:** {status_text}{excluded}{open_time}")
            if details.get("notes"):
                for note in details["notes"]:
                    st.write(f"- {note}")
        st.info("🚨 **NO REAL TRADING EXECUTION**")

    st.divider()


    # Main Tabs
    tabs = st.tabs(["Status", "Forecast", "Weather", "Live NWS / KMIA Data", "Kalshi Market Data", "Paper Trading", "Learning", "Prediction Quality", "Logs", "Files", "Operator Notes"])
    
    with tabs[0]:
        st.header("Latest System Status")
        if latest_status_json:
            st.json(load_json(latest_status_json))
        elif latest_status_md:
            st.markdown(load_text(latest_status_md))

    with tabs[1]:
        st.header("Latest Forecast Report")
        if latest_forecast_md:
            st.markdown(load_text(latest_forecast_md))

    with tabs[2]:
        st.header("Weather Ingestion Status (KMIA)")
        if latest_weather_json.exists():
            st.json(load_json(latest_weather_json))

    with tabs[3]:
        st.header("Live NWS Data (KMIA)")
        if n_data:
            nc1, nc2, nc3 = st.columns(3)
            nc1.metric("Current Temp", f"{n_data.get('current_temp_f', 'N/A')}°F")
            nc2.metric("Observed Max", f"{n_data.get('observed_max_so_far_f', 'N/A')}°F")
            nc3.metric("Forecast High", f"{n_data.get('forecast_high_f', 'N/A')}°F")
            
            st.write(f"**Latest Observation Time:** {n_data.get('latest_observation_time', 'N/A')}")
            st.write(f"**Stale Data:** {'Yes' if n_data.get('stale_data') else 'No'}")
            st.write(f"**Endpoint Status:** {n_data.get('endpoint_status', 'N/A')}")
            st.write(f"**Hourly Summary:** {n_data.get('hourly_forecast_summary', 'N/A')}")
            
            if n_data.get("warnings"):
                st.warning(" | ".join(n_data.get("warnings")))
                
            with st.expander("Raw NWS Snapshot JSON"):
                st.json(n_data)
        else:
            st.info("No live NWS snapshot found. Run `bash scripts/update_nws_live_data.sh`.")

    with tabs[4]:
        st.header("Kalshi Market Discovery")
        if latest_kalshi_json.exists():
            st.json(load_json(latest_kalshi_json))

    with tabs[5]:
        st.header("Paper Trading Performance")
        st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
        PERF_FILE = PAPER_DIR / "latest_paper_trading_performance.json"
        if PERF_FILE.exists():
            perf = load_json(PERF_FILE)
            p_col1, p_col2, p_col3, p_col4 = st.columns(4)
            p_col1.metric("Settled Trades", perf.get("total_settled_trades", 0))
            p_col2.metric("Win Rate", f"{perf.get('win_rate', 0):.1%}")
            p_col3.metric("Simulated PnL", f"${perf.get('total_simulated_pnl', 0):.2f}")
            p_col4.metric("Pending Trades", perf.get("pending_trades", 0))
            
            SETTLE_FILE = PAPER_DIR / "paper_trade_settlements.jsonl"
            if SETTLE_FILE.exists():
                st.subheader("Latest Settlement Results")
                settlements = []
                with open(SETTLE_FILE, "r") as f:
                    for line in f:
                        try:
                            settlements.append(json.loads(line))
                        except:
                            continue
                if settlements:
                    df_settle = pd.DataFrame(settlements)
                    # Reorder for display
                    s_cols = ["trade_date", "market_ticker", "actual_max_temp_f", "actual_bin", "result", "simulated_pnl"]
                    st.dataframe(df_settle[s_cols].iloc[::-1])
        else:
            st.info("No performance data available. Run `bash scripts/settle_paper_trades.sh`.")

        st.header("Paper Trading Ledger")
        st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
        LEDGER_FILE = PAPER_DIR / "paper_trade_ledger.jsonl"
        if LEDGER_FILE.exists():
            trades = []
            with open(LEDGER_FILE, "r") as f:
                for line in f:
                    try:
                        trades.append(json.loads(line))
                    except:
                        continue
            st.metric("Open Paper Trades", len(trades))
            if trades:
                df_trades = pd.DataFrame(trades)
                st.dataframe(df_trades.iloc[::-1])
        else:
            st.write("No paper trades recorded yet.")

        st.header("Latest Signals")
        if p_data:
            signals = p_data.get("signals", [])
            if signals:
                df_signals = pd.DataFrame(signals)
                cols = ["market_ticker", "forecast_bin", "model_probability", "market_implied_probability", "edge", "expected_value", "paper_action", "confidence"]
                st.dataframe(df_signals[cols].style.format({
                    "model_probability": "{:.1%}",
                    "market_implied_probability": "{:.1%}",
                    "edge": "{:+.1%}",
                    "expected_value": "{:+.2f}"
                }))

    with tabs[6]:
        st.header("🎓 Paper Trading Learning Summary")
        st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
        if latest_learning_json.exists():
            st.json(l_data)
            st.write("### Model Lesson")
            st.info(l_data.get("model_lesson", "No lesson yet."))
            st.write("### Best Signal Evaluated")
            st.json(l_data.get("best_signal", {}))
        else:
            st.info("No learning summary found. Run `bash scripts/generate_learning_summary.sh`.")

    with tabs[7]:
        st.header("🎯 Prediction Quality Report")
        st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
        
        pq_json = LEARNING_DIR / "latest_prediction_quality_report.json"
        if pq_json.exists():
            pq_data = load_json(pq_json)
            st.json(pq_data)
            
            trade_date = pq_data.get("trade_date")
            if trade_date:
                md_path = LEARNING_DIR / f"prediction_quality_report_{trade_date}.md"
                if md_path.exists():
                    st.divider()
                    st.markdown(load_text(md_path))
        else:
            st.info("No prediction quality report found. Run `bash scripts/generate_prediction_quality_report.sh`.")

    with tabs[8]:
        st.header("Latest Workflow Logs")
        if latest_log:
            st.code(load_text(latest_log)[-5000:], language="text")

    with tabs[9]:
        st.header("Discovered Files")
        file_info = []
        for d in [STATUS_DIR, REPORTS_DIR, LOGS_DIR, CAL_DIR, KALSHI_DIR, PAPER_DIR]:
            if d.exists():
                for f in d.glob("*"):
                    if f.is_file():
                        file_info.append({"Dir": d.name, "File": f.name, "Size": f.stat().st_size})
        if file_info:
            st.table(pd.DataFrame(file_info))

    with tabs[10]:
        st.header("Operator Notes")
        st.write("""
        ### Daily Workflow
        ```bash
        bash scripts/run_kmia_daily_workflow.sh
        bash scripts/generate_paper_signal.sh
        bash scripts/record_paper_trade.sh
        ```
        """)

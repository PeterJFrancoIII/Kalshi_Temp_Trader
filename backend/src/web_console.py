import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import re
from typing import Optional, Tuple

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
WEATHER_INGESTION_DIR = DATA / "weather_ingestion"

try:
    from shared.manual_corrections import load_manual_corrections
except ImportError:
    def load_manual_corrections(): return {}

# --- CORE HELPERS ---
def latest_file(directory: Path, pattern: str) -> Optional[Path]:
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def load_latest_json(directory: Path, pattern: str) -> tuple[Optional[dict], Optional[Path]]:
    path = latest_file(directory, pattern)
    if path:
        return load_json(path), path
    return None, None

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

def normalize_signal_df(df):
    """Normalize aliases for signal dataframes."""
    if "forecast_bin" not in df.columns and "bin" in df.columns:
        df["forecast_bin"] = df["bin"]
    if "contract_ticker" not in df.columns and "market_ticker" in df.columns:
        df["contract_ticker"] = df["market_ticker"]
    if "market_implied_probability" not in df.columns and "market_probability" in df.columns:
        df["market_implied_probability"] = df["market_probability"]
    if "action" not in df.columns and "paper_action" in df.columns:
        df["action"] = df["paper_action"]
    if "time_to_close" not in df.columns and "time_to_close_minutes" in df.columns:
        df["time_to_close"] = df["time_to_close_minutes"]
    if "speed_to_roi" not in df.columns and "speed_to_roi_score" in df.columns:
        df["speed_to_roi"] = df["speed_to_roi_score"]
    return df

def safe_dataframe(df, display_columns, fallback_message="No displayable columns found.", formatters=None):
    """Safely render a DataFrame ignoring missing columns."""
    available_columns = [c for c in display_columns if c in df.columns]
    if available_columns:
        df_display = df[available_columns]
        if formatters:
            valid_formatters = {k: v for k, v in formatters.items() if k in available_columns}
            st.dataframe(df_display.style.format(valid_formatters), use_container_width=True)
        else:
            st.dataframe(df_display, use_container_width=True)
    else:
        st.info(fallback_message)
        st.dataframe(df, use_container_width=True)

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

    if isinstance(report_path, str):
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
    
    sn_match = re.search(r"\*\*(?:Best Single-Number Estimate|Forecast High):\*\*\s*([\d.]+)", content)
    if sn_match:
        res["best_single_number"] = sn_match.group(1)
        
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

# --- RENDERING HELPERS ---

def render_operator_home(app_state):
    st.header("🏠 Operator Home")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if app_state["system_status"] == "GREEN":
            st.success(f"### SYSTEM STATUS: {app_state['system_status']}")
        elif app_state["system_status"] == "YELLOW":
            st.warning(f"### SYSTEM STATUS: {app_state['system_status']}")
        else:
            st.error(f"### SYSTEM STATUS: {app_state['system_status']}")

    with col2:
        st.metric("TODAY'S FORECAST", f"{app_state['forecast_val']}°F")
        st.write(f"**Top Bin:** {app_state['top_bin']}")

    with col3:
        st.metric("WEATHER INGESTION", app_state["weather_live"])
        if app_state["w_path"]:
            st.caption(f"Source: {app_state['w_path'].name}")
        
        st.metric("NWS LIVE DATA", app_state["nws_live"])
        if app_state["latest_nws_path"]:
            st.caption(f"Source: {app_state['latest_nws_path'].name}")
            if app_state["n_data"]:
                st.write(f"**Live Temp:** {app_state['n_data'].get('current_temp_f', 'N/A')}°F")

    with col4:
        st.metric("KALSHI MARKET", app_state["kalshi_status"])
        st.write(f"**Last Updated:** {app_state['kalshi_last_upd']}")

    # Paper Loop Status
    st.divider()
    st.subheader("🔄 Paper Loop Status")
    
    pl_col1, pl_col2, pl_col3, pl_col4 = st.columns(4)
    with pl_col1:
        st.metric("Paper Loop", app_state["paper_loop_status"])
        st.write(f"**Best Signal:** `{app_state.get('latest_signal_ticker', 'N/A')} ({app_state['latest_signal_action']})`")
    with pl_col2:
        st.metric("Open Paper Trades", app_state["open_paper_trades"])
        st.write(f"**Pending Settlements:** {app_state['pending_settlements']}")
    with pl_col3:
        st.metric("Settled Trades", app_state["settled_trades"])
        st.write(f"**Simulated PnL:** ${app_state['sim_pnl']:.2f}")
    with pl_col4:
        st.metric("Next Action", "Pending" if app_state["pending_settlements"] > 0 else "Ready")
        st.info(app_state["next_action"])

    st.info("🚨 **NO REAL TRADING EXECUTION**")


def render_active_forecasts(p_data):
    st.header("📊 Active Kalshi Contract Forecasts")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
    
    if p_data:
        best_sig = p_data.get("best_signal")
        if best_sig:
            st.subheader("🏆 Best Signal")
            st.info(f"**{best_sig.get('market_ticker', 'N/A')}** | Edge: {best_sig.get('edge', 0)*100:+.1f}% | Action: {best_sig.get('paper_action', 'N/A')}")
            bs_c1, bs_c2, bs_c3, bs_c4 = st.columns(4)
            bs_c1.metric("Model Prob", f"{best_sig.get('model_probability', 0)*100:.1f}%")
            bs_c2.metric("Market Prob", f"{best_sig.get('market_probability', 0)*100:.1f}%")
            bs_c3.metric("Edge", f"{best_sig.get('edge', 0)*100:+.1f}%")
            bs_c4.metric("Confidence", best_sig.get("confidence", "N/A").upper())

        st.divider()
        signals = p_data.get("signals", [])
        if signals:
            df_sig = pd.DataFrame(signals)
            df_sig = normalize_signal_df(df_sig)
            col_map_sig = {
                "market_ticker": "Ticker",
                "market_title": "Contract",
                "status": "Status",
                "threshold_f": "Threshold",
                "condition_type": "Condition",
                "model_probability": "Model %",
                "market_probability": "Market %",
                "edge": "Edge",
                "time_to_close_minutes": "Time to Close",
                "speed_to_roi_score": "Speed-to-ROI",
                "paper_action": "Paper Action"
            }
            df_display_sig = df_sig.copy()
            if "model_probability" in df_display_sig.columns:
                df_display_sig["model_probability"] = df_display_sig["model_probability"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "N/A")
            if "market_probability" in df_display_sig.columns:
                df_display_sig["market_probability"] = df_display_sig["market_probability"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "N/A")
            if "edge" in df_display_sig.columns:
                df_display_sig["edge"] = df_display_sig["edge"].apply(lambda x: f"{x*100:+.1f}%" if pd.notnull(x) else "N/A")
            if "time_to_close_minutes" in df_display_sig.columns:
                df_display_sig["time_to_close_minutes"] = df_display_sig["time_to_close_minutes"].apply(lambda x: f"{x:.1f}m" if pd.notnull(x) else "N/A")
            
            existing_cols_sig = [c for c in col_map_sig.keys() if c in df_display_sig.columns]
            df_final = df_display_sig[existing_cols_sig].rename(columns=col_map_sig)
            st.dataframe(df_final, use_container_width=True, hide_index=True)
        else:
            st.info("No active contract forecasts found in latest signal data.")
    else:
        st.warning("No active contract forecasts found. Run:")
        st.code("bash scripts/update_kalshi_market_data.sh\nbash scripts/generate_paper_signal.sh")


def render_paper_trading(perf, settlements, trades):
    st.header("📈 Paper Trading Performance")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
    
    if perf:
        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        p_col1.metric("Settled Trades", perf.get("total_settled_trades", 0))
        p_col2.metric("Win Rate", f"{perf.get('win_rate', 0):.1%}")
        p_col3.metric("Simulated PnL", f"${perf.get('total_simulated_pnl', 0):.2f}")
        p_col4.metric("Pending Trades", perf.get("pending_trades", 0))
    else:
        st.info("No performance data available. Run `bash scripts/settle_paper_trades.sh`.")

    if settlements:
        st.subheader("Latest Settlement Results")
        df_settle = pd.DataFrame(settlements)
        s_cols = ["trade_date", "market_ticker", "actual_max_temp_f", "actual_bin", "result", "simulated_pnl"]
        existing_s_cols = [c for c in s_cols if c in df_settle.columns]
        st.dataframe(df_settle[existing_s_cols].iloc[::-1], use_container_width=True, hide_index=True)

    st.divider()
    st.header("Ledger")
    st.metric("Open Paper Trades", len(trades))
    if trades:
        df_trades = pd.DataFrame(trades)
        st.dataframe(df_trades.iloc[::-1])
    else:
        st.write("No paper trades recorded yet.")


def render_weather_nws(w_data, n_data):
    st.header("🌦️ Weather / NWS Live Data")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
    
    if n_data:
        status_text = "🟢 CONNECTED"
        if n_data.get("stale_data"):
            status_text = "🟡 STALE"
        if n_data.get("endpoint_status") == "ERROR":
            status_text = "🔴 ERROR"
            
        st.subheader(f"NWS Status: {status_text}")
        
        nc1, nc2, nc3, nc4 = st.columns(4)
        nc1.metric("Current Temp", f"{n_data.get('current_temp_f', 'N/A')}°F")
        nc2.metric("Observed Max Today", f"{n_data.get('observed_max_so_far_f', 'N/A')}°F")
        nc3.metric("Wind", f"{n_data.get('wind_direction_compass', 'N/A')} {n_data.get('wind_speed_mph', 'N/A')} mph")
        nc4.metric("Stale Data", "Yes" if n_data.get("stale_data") else "No")
        
        st.write(f"**Latest Observation Time:** {n_data.get('latest_observation_time', 'N/A')} (UTC)")
        if n_data.get("wind_gust_mph"):
            st.write(f"**Recent Gust:** {n_data.get('wind_gust_mph')} mph")
        if n_data.get("clouds_x100ft"):
            st.write(f"**Clouds:** {n_data.get('clouds_x100ft')}")
        
        st.subheader("Recent Observations (KMIA)")
        obs_list = n_data.get("recent_observations_table", [])
        if obs_list:
            df_obs = pd.DataFrame(obs_list)
            col_map = {
                "date_et": "Date",
                "time_et": "Time ET",
                "temperature_f": "Temp °F",
                "dewpoint_f": "Dew Point °F",
                "relative_humidity_pct": "Humidity %",
                "wind_direction_compass": "Wind Dir",
                "wind_direction_degrees": "Wind Deg",
                "wind_speed_mph": "Wind mph",
                "wind_gust_mph": "Gust mph",
                "sea_level_pressure_mb": "Sea Level mb",
                "barometric_pressure_mb": "Pressure mb",
                "precipitation_last_hour_in": "Precip 1h in",
                "clouds_x100ft": "Clouds x100ft",
                "text_description": "Description",
                "raw_message": "Raw METAR"
            }
            existing_cols = [c for c in col_map.keys() if c in df_obs.columns]
            df_display = df_obs[existing_cols].rename(columns=col_map)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.warning("No recent observations found in snapshot.")
        
        if n_data.get("warnings"):
            st.warning(" | ".join(n_data.get("warnings")))
            
        with st.expander("Links & Raw JSON"):
            st.write(f"- [NWS Time Series (KMIA)]({n_data.get('timeseries_source_url')})")
            st.write(f"- [API Observations URL]({n_data.get('api_observations_url')})")
            st.json(n_data)
    else:
        st.info("No live NWS snapshot found. Run `bash scripts/update_nws_live_data.sh`.")

    if w_data:
        st.subheader("Daily Weather Ingestion Status")
        with st.expander("View Daily Weather Status JSON"):
            st.json(w_data)


def render_calibration_learning(pq_data, pq_md, l_data, cal_json, cal_md):
    st.header("🎓 Calibration & Learning")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
    
    st.subheader("Learning Summary")
    if l_data:
        l_col1, l_col2, l_col3, l_col4 = st.columns(4)
        with l_col1:
            st.metric("Learning Status", "Active")
            st.write(f"**Trade Date:** {l_data.get('trade_date', 'N/A')}")
        with l_col2:
            st.metric("Win Rate", f"{l_data.get('win_rate', 0):.1%}")
            st.write(f"**Settled Trades:** {l_data.get('settled_trades', 0)}")
        with l_col3:
            st.metric("Simulated PnL", f"${l_data.get('simulated_pnl', 0.0):.2f}")
            st.write(f"**Model Lesson:** {l_data.get('model_lesson', 'Collecting more data...')}")
        with l_col4:
            st.metric("Next Action", "Monitor")
            st.success(l_data.get('next_action', "Run generate_learning_summary.sh"))
            
        with st.expander("Best Signal Evaluated"):
            st.json(l_data.get("best_signal", {}))
    else:
        st.info("No learning summary found. Run `bash scripts/generate_learning_summary.sh`.")

    st.divider()
    st.subheader("Prediction Quality Report")
    if pq_data:
        st.write(f"**Quality:** {pq_data.get('prediction_quality', 'Unknown')}")
        pq_col1, pq_col2, pq_col3 = st.columns(3)
        with pq_col1:
            st.write(f"**Main Risk:** {pq_data.get('main_risk', 'None')}")
        with pq_col2:
            st.write(f"**Next Action:** {pq_data.get('next_action', 'N/A')}")
        with pq_col3:
            st.write(f"**Best Paper Signal:** `{pq_data.get('best_paper_signal', 'None')}`")
        
        if pq_data.get("data_quality_warnings"):
            st.warning(" | ".join(pq_data["data_quality_warnings"]))
            
        if pq_md:
            with st.expander("View Full Markdown Report"):
                st.markdown(pq_md)
    else:
        st.info("No prediction quality report found. Run `bash scripts/generate_prediction_quality_report.sh`.")

    if cal_md:
        st.divider()
        st.subheader("Aggregate Calibration")
        with st.expander("View Calibration Markdown"):
            st.markdown(cal_md)

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


def render_system_health(app_state):
    st.header("⚙️ System Health & Raw Data")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Latest System Status")
        if app_state["latest_status_json"]:
            with st.expander("View Status JSON"):
                st.json(load_json(app_state["latest_status_json"]))
        if app_state["latest_status_md"]:
            with st.expander("View Status MD"):
                st.markdown(load_text(app_state["latest_status_md"]))
                
        st.subheader("Forecast Report")
        if app_state["latest_forecast_md"]:
            with st.expander("View Forecast MD"):
                st.markdown(load_text(app_state["latest_forecast_md"]))
                
    with col2:
        st.subheader("Kalshi Market Discovery")
        if app_state["latest_kalshi_json"].exists():
            with st.expander("View Kalshi JSON"):
                st.json(load_json(app_state["latest_kalshi_json"]))
                
        st.subheader("Operator Notes & Workflow")
        st.write('''
        ### Daily Commands
        ```bash
        bash scripts/run_kmia_daily_workflow.sh
        bash scripts/generate_paper_signal.sh
        bash scripts/record_paper_trade.sh
        ```
        ''')

    st.divider()
    st.subheader("Latest Workflow Logs")
    if app_state["latest_log"]:
        with st.expander("View Tail of Latest Log"):
            st.code(load_text(app_state["latest_log"])[-5000:], language="text")

    st.divider()
    st.subheader("Discovered Processed Files")
    file_info = []
    for d in [STATUS_DIR, REPORTS_DIR, LOGS_DIR, CAL_DIR, KALSHI_DIR, PAPER_DIR]:
        if d.exists():
            for f in d.glob("*"):
                if f.is_file():
                    file_info.append({"Dir": d.name, "File": f.name, "Size": f.stat().st_size})
    if file_info:
        st.table(pd.DataFrame(file_info))


# --- MAIN ---
if __name__ == "__main__":
    st.set_page_config(
        page_title="KMIA Weather Console",
        page_icon="🌦️",
        layout="wide"
    )

    st.title("KMIA Kalshi Weather Console")
    st.error("🚨 **DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION**")

    # --- DATA LOADING (Centralized) ---
    latest_status_json = latest_file(STATUS_DIR, "kmia_daily_status_*.json")
    latest_status_md = latest_file(STATUS_DIR, "kmia_daily_status_*.md")
    
    latest_forecast_md = latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.md")
    if not latest_forecast_md:
        latest_forecast_md = latest_file(REPORTS_DIR, "kmia_forecast_*.md")

    latest_kalshi_json = KALSHI_DIR / "latest_kalshi_market_snapshot.json"
    latest_log = latest_file(LOGS_DIR, "kmia_daily_workflow_*.log")
    
    agg_cal_json_path = CAL_DIR / "aggregate_calibration.json"
    agg_cal_md_path = CAL_DIR / "aggregate_calibration.md"
    cal_json = load_json(agg_cal_json_path) if agg_cal_json_path.exists() else None
    cal_md = load_text(agg_cal_md_path) if agg_cal_md_path.exists() else None

    # Weather
    latest_weather_json = WEATHER_INGESTION_DIR / "latest_weather_ingestion_status.json"
    w_data_status, w_path = load_latest_json(STATUS_DIR, "kmia_daily_status_*.json")
    w_data_ingest = load_json(latest_weather_json) if latest_weather_json.exists() else None
    w_data = w_data_ingest or w_data_status # Combine or use what's available
    
    # NWS
    latest_nws_path = NWS_DIR / "latest_nws_kmia_snapshot.json"
    if not latest_nws_path.exists():
        latest_nws_path = latest_file(NWS_DIR, "nws_kmia_snapshot_*.json")
    n_data = load_json(latest_nws_path) if latest_nws_path else {}

    # Paper Trading
    latest_paper_json = PAPER_DIR / "latest_paper_signal.json"
    p_data = load_json(latest_paper_json) if latest_paper_json.exists() else {}
    
    PERF_FILE = PAPER_DIR / "latest_paper_trading_performance.json"
    perf = load_json(PERF_FILE) if PERF_FILE.exists() else {}
    
    LEDGER_FILE = PAPER_DIR / "paper_trade_ledger.jsonl"
    trades = []
    open_paper_trades = 0
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        trades.append(json.loads(line))
                        open_paper_trades += 1
                    except:
                        continue

    SETTLE_FILE = PAPER_DIR / "paper_trade_settlements.jsonl"
    settlements = []
    if SETTLE_FILE.exists():
        with open(SETTLE_FILE, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        settlements.append(json.loads(line))
                    except:
                        continue

    # Learning & Prediction Quality
    latest_learning_json = LEARNING_DIR / "latest_learning_summary.json"
    l_data = load_json(latest_learning_json) if latest_learning_json.exists() else {}
    
    pq_json = LEARNING_DIR / "latest_prediction_quality_report.json"
    pq_data = load_json(pq_json) if pq_json.exists() else {}
    pq_md = None
    if pq_data and pq_data.get("trade_date"):
        md_path = LEARNING_DIR / f"prediction_quality_report_{pq_data['trade_date']}.md"
        pq_md = load_text(md_path)

    # --- STATE DERIVATION ---
    app_state = {
        "system_status": "GREEN",
        "action_needed": "None. System is working.",
        "forecast_val": "Unknown",
        "top_bin": "Unknown",
        "weather_live": "✅ CONNECTED" if w_path else "❌ MISSING",
        "w_path": w_path,
        "nws_live": "❌ MISSING",
        "latest_nws_path": latest_nws_path,
        "n_data": n_data,
        "kalshi_status": "MISSING",
        "kalshi_last_upd": "N/A",
        "paper_loop_status": "Active" if p_data else "Missing Data",
        "latest_signal_action": "Unknown",
        "open_paper_trades": open_paper_trades,
        "pending_settlements": perf.get("pending_trades", 0),
        "settled_trades": perf.get("total_settled_trades", 0),
        "sim_pnl": perf.get("total_simulated_pnl", 0),
        "next_action": "Ready",
        "latest_status_json": latest_status_json,
        "latest_status_md": latest_status_md,
        "latest_forecast_md": latest_forecast_md,
        "latest_kalshi_json": latest_kalshi_json,
        "latest_log": latest_log
    }

    # NWS live status
    if n_data:
        is_stale = n_data.get("stale_data", False)
        is_error = n_data.get("endpoint_status") == "ERROR"
        has_temp = n_data.get("current_temp_f") is not None
        if not is_stale or not is_error or has_temp:
            app_state["nws_live"] = "✅ CONNECTED"
        else:
            app_state["nws_live"] = "⚠️ STALE"

    # Kalshi status
    if latest_kalshi_json.exists():
        app_state["kalshi_last_upd"] = datetime.fromtimestamp(latest_kalshi_json.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        mkts = load_json(latest_kalshi_json)
        if mkts.get("selected_temperature_markets"):
            app_state["kalshi_status"] = "CONNECTED"
        elif mkts.get("total_markets_returned", 0) > 0:
            app_state["system_status"] = "YELLOW"
            app_state["kalshi_status"] = "CONNECTED (No Miami Markets)"
            app_state["action_needed"] = "Kalshi discovery found general markets, but no matching Miami temperature market."
        else:
            app_state["system_status"] = "YELLOW"
            app_state["kalshi_status"] = "CONNECTED (0 Markets)"
            app_state["action_needed"] = "Kalshi discovery returned 0 results."
    else:
        app_state["system_status"] = "YELLOW"
        app_state["action_needed"] = "Run: bash scripts/update_kalshi_market_data.sh"

    # Evaluate System Health combined
    if not latest_status_json or not latest_forecast_md or (w_data_status and w_data_status.get("is_stale")) or (n_data and n_data.get("stale_data")):
        app_state["system_status"] = "YELLOW"
        app_state["action_needed"] = "Review missing files or stale weather data."

    # Forecast extraction
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
                app_state["forecast_val"] = summary.get("best_single_number", "Unknown")
                app_state["top_bin"] = summary.get("top_probability_bin", "Unknown")
            elif isinstance(forecast_info, dict):
                app_state["forecast_val"] = str(forecast_info.get("best_single_number", "Unknown"))
                app_state["top_bin"] = forecast_info.get("top_probability_bin", "Unknown")
    
    if app_state["forecast_val"] == "Unknown" or app_state["top_bin"] == "Unknown":
        summary = load_latest_forecast_summary(latest_forecast_md)
        app_state["forecast_val"] = summary.get("best_single_number", "Unknown")
        app_state["top_bin"] = summary.get("top_probability_bin", "Unknown")

    # Paper signal latest action
    best_sig = p_data.get("best_signal")
    if isinstance(best_sig, dict):
        app_state["latest_signal_action"] = best_sig.get("paper_action", "Unknown")
        app_state["latest_signal_ticker"] = best_sig.get("market_ticker", "Unknown")

    # Next action logic
    if app_state["system_status"] != "GREEN":
        app_state["next_action"] = "Check logs"
    elif app_state["pending_settlements"] > 0:
        app_state["next_action"] = "Wait for official KMIA settlement"
    elif app_state["open_paper_trades"] == 0:
        app_state["next_action"] = "Wait for next signal"
    else:
        app_state["next_action"] = "Wait for official KMIA settlement"

    # --- SIDEBAR ---
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

    # --- MAIN TABS ---
    tabs = st.tabs([
        "Operator Home", 
        "Active Kalshi Forecasts", 
        "Paper Trading", 
        "Weather / NWS", 
        "Calibration / Learning", 
        "System Health"
    ])
    
    with tabs[0]:
        render_operator_home(app_state)
        
    with tabs[1]:
        render_active_forecasts(p_data)
        
    with tabs[2]:
        render_paper_trading(perf, settlements, trades)
        
    with tabs[3]:
        render_weather_nws(w_data, n_data)
        
    with tabs[4]:
        render_calibration_learning(pq_data, pq_md, l_data, cal_json, cal_md)
        
    with tabs[5]:
        render_system_health(app_state)

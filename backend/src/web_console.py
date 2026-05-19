"""Streamlit dashboard entry point for the KMIA Kalshi predictor.

The historical 1.7k-line single-file implementation has been split into
focused modules under :mod:`console`:

- :mod:`console.data_helpers` — pure helpers (file IO, formatters,
  domain extractors).
- :mod:`console.pages` — one ``render_<tab>`` function per submodule.

This file now owns three responsibilities only:

1. Streamlit page configuration and the safety banner.
2. Loading the per-render artifact set and deriving ``app_state``.
3. Wiring the sidebar and the eight tab strip to the page renderers.

For backward compatibility with the existing test suite (which imports
``from web_console import format_temp`` etc.), all helper names from
:mod:`console.data_helpers` are re-exported at module scope.

NO REAL TRADING EXECUTION. DRY-RUN / PAPER EVALUATION ONLY.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from console.data_helpers import (
    aggregate_warnings,
    calculate_hypothetical_costs,
    derive_orderbook_prices,
    extract_best_signal,
    extract_bin_from_market,
    extract_market_rows,
    extract_nws_observation_rows,
    format_num,
    format_pnl,
    format_probability,
    format_temp,
    is_signal_stale_or_mismatched,
    latest_file,
    load_forecast_data,
    load_json,
    load_latest_forecast_summary,
    load_latest_json,
    load_text,
    normalize_signal_df,
    pretty_format_bin,
    safe_dataframe,
)
from console.pages import (
    render_active_forecasts,
    render_backtesting,
    render_calibration_learning,
    render_command_center,
    render_kalshi_market_console,
    render_paper_trading,
    render_system_health,
    render_weather_nws,
)
from shared.artifact_paths import (
    BACKTEST_REPORTS_DIR,
    CALIBRATION_DIR,
    KALSHI_MARKET_SNAPSHOT_DIR,
    LATEST_KALSHI_MARKET_SNAPSHOT,
    LATEST_KALSHI_ORDERBOOKS,
    LATEST_NWS_KMIA_SNAPSHOT,
    LATEST_PAPER_SIGNAL,
    LOGS_DIR,
    PAPER_LEDGER_FILE,
    PAPER_TRADING_DIR,
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
    STATUS_DIR,
    WEATHER_NWS_DIR,
)

logger = logging.getLogger(__name__)

# --- Legacy local aliases (kept so existing tests / runtime code that
# imports these names from ``web_console`` continue to work). The
# canonical paths live in :mod:`shared.artifact_paths`. ----------------
ROOT = Path(__file__).resolve().parents[2]
DATA = PROCESSED_DATA_DIR
CAL_DIR = CALIBRATION_DIR
KALSHI_DIR = KALSHI_MARKET_SNAPSHOT_DIR
PAPER_DIR = PAPER_TRADING_DIR
NWS_DIR = WEATHER_NWS_DIR
LEARNING_DIR = DATA / "learning"
WEATHER_INGESTION_DIR = DATA / "weather_ingestion"
HISTORY_FILE = DATA / "history" / "kmia_daily_history.jsonl"


__all__ = [
    # re-exported helpers (keep this list in sync with console.data_helpers)
    "aggregate_warnings",
    "calculate_hypothetical_costs",
    "derive_orderbook_prices",
    "extract_best_signal",
    "extract_bin_from_market",
    "extract_market_rows",
    "extract_nws_observation_rows",
    "format_num",
    "format_pnl",
    "format_probability",
    "format_temp",
    "is_signal_stale_or_mismatched",
    "latest_file",
    "load_forecast_data",
    "load_json",
    "load_latest_forecast_summary",
    "load_latest_json",
    "load_text",
    "normalize_signal_df",
    "pretty_format_bin",
    "safe_dataframe",
    # re-exported page renderers
    "render_active_forecasts",
    "render_backtesting",
    "render_calibration_learning",
    "render_command_center",
    "render_kalshi_market_console",
    "render_paper_trading",
    "render_system_health",
    "render_weather_nws",
]


# --- Streamlit entry point -------------------------------------------

if __name__ == "__main__":
    st.set_page_config(
        page_title="KMIA Weather Console",
        page_icon="🌦️",
        layout="wide",
    )

    st.title("KMIA Kalshi Weather Console")
    st.error("🚨 **DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION**")

    # --- DATA LOADING (centralized so renderers stay pure-ish) -----
    latest_status_json = latest_file(STATUS_DIR, "kmia_daily_status_*.json")
    latest_status_md = latest_file(STATUS_DIR, "kmia_daily_status_*.md")

    latest_forecast_md = latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.md")
    if not latest_forecast_md:
        latest_forecast_md = latest_file(REPORTS_DIR, "kmia_forecast_*.md")

    latest_kalshi_json = LATEST_KALSHI_MARKET_SNAPSHOT
    latest_log = latest_file(LOGS_DIR, "kmia_daily_workflow_*.log")

    agg_cal_json_path = CAL_DIR / "aggregate_calibration.json"
    agg_cal_md_path = CAL_DIR / "aggregate_calibration.md"
    cal_json = load_json(agg_cal_json_path) if agg_cal_json_path.exists() else None
    cal_md = load_text(agg_cal_md_path) if agg_cal_md_path.exists() else None

    latest_weather_json = WEATHER_INGESTION_DIR / "latest_weather_ingestion_status.json"
    w_data_status, w_path = load_latest_json(STATUS_DIR, "kmia_daily_status_*.json")
    w_data_ingest = load_json(latest_weather_json) if latest_weather_json.exists() else None
    w_data = w_data_ingest or w_data_status

    latest_nws_path = LATEST_NWS_KMIA_SNAPSHOT
    if not latest_nws_path.exists():
        latest_nws_path = latest_file(NWS_DIR, "nws_kmia_snapshot_*.json")
    n_data = load_json(latest_nws_path) if latest_nws_path else {}

    latest_paper_json = LATEST_PAPER_SIGNAL
    p_data = load_json(latest_paper_json) if latest_paper_json.exists() else {}

    latest_orderbooks_json = LATEST_KALSHI_ORDERBOOKS
    o_data = load_json(latest_orderbooks_json) if latest_orderbooks_json.exists() else {}

    PERF_FILE = PAPER_DIR / "latest_paper_trading_performance.json"
    perf = load_json(PERF_FILE) if PERF_FILE.exists() else {}

    trades: list[dict] = []
    open_paper_trades = 0
    if PAPER_LEDGER_FILE.exists():
        try:
            ledger_json = load_json(PAPER_LEDGER_FILE)
            if ledger_json and isinstance(ledger_json.get("trades"), list):
                trades = ledger_json["trades"]
                open_paper_trades = len(
                    [t for t in trades if str(t.get("status", "")).lower() == "open"]
                )
        except Exception as e:
            logger.error(f"Error loading Paper Ledger: {e}")

    SETTLE_FILE = PAPER_DIR / "paper_trade_settlements.jsonl"
    settlements: list[dict] = []
    if SETTLE_FILE.exists():
        with open(SETTLE_FILE, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        settlements.append(json.loads(line))
                    except Exception:
                        continue

    latest_learning_json = LEARNING_DIR / "latest_learning_summary.json"
    l_data = load_json(latest_learning_json) if latest_learning_json.exists() else {}

    pq_json = LEARNING_DIR / "latest_prediction_quality_report.json"
    pq_data = load_json(pq_json) if pq_json.exists() else {}
    pq_md = None
    if pq_data and pq_data.get("trade_date"):
        md_path = LEARNING_DIR / f"prediction_quality_report_{pq_data['trade_date']}.md"
        pq_md = load_text(md_path)

    # Weather gate freshness
    from weather.nws_snapshot_contract import assess_nws_snapshot

    weather_gate = None
    if isinstance(w_data_status, dict) and "weather_gate" in w_data_status:
        weather_gate = w_data_status["weather_gate"]
    else:
        try:
            weather_gate = assess_nws_snapshot(n_data)
        except Exception as e:
            weather_gate = {
                "available": False,
                "allow_paper_recommendations": False,
                "status": "ERROR",
                "no_trade_reason": f"Assessment failed: {e}",
                "warnings": [f"Assessment failed: {e}"],
                "latest_observation_time": None,
                "fetched_at_utc": None,
                "observation_age_minutes": None,
            }

    if weather_gate and not weather_gate.get("allow_paper_recommendations", True):
        st.error(
            "🔴 **CRITICAL SAFETY GATING ACTIVE:** Trading recommendations are actively "
            "blocked because the NWS weather snapshot is invalid, stale, or missing.\n\n"
            f"**Reason:** {weather_gate.get('no_trade_reason') or 'No-trade reason unspecified.'}"
        )

    # --- STATE DERIVATION ---
    app_state: dict = {
        "system_status": "GREEN",
        "action_needed": "None. System is working.",
        "forecast_val": "Unknown",
        "top_bin": "Unknown",
        "weather_live": "✅ CONNECTED" if w_path else "❌ MISSING",
        "w_path": w_path,
        "nws_live": "❌ MISSING",
        "latest_nws_path": latest_nws_path,
        "n_data": n_data,
        "weather_gate": weather_gate,
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
        "latest_log": latest_log,
    }

    if n_data:
        is_stale = n_data.get("stale_data", False)
        is_error = n_data.get("endpoint_status") == "ERROR"
        has_temp = n_data.get("current_temp_f") is not None
        if not is_stale or not is_error or has_temp:
            app_state["nws_live"] = "✅ CONNECTED"
        else:
            app_state["nws_live"] = "⚠️ STALE"

    mkts: dict = {}
    if latest_kalshi_json.exists():
        app_state["kalshi_last_upd"] = datetime.fromtimestamp(
            latest_kalshi_json.stat().st_mtime
        ).strftime('%Y-%m-%d %H:%M')
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

    if (
        not latest_status_json
        or not latest_forecast_md
        or (w_data_status and w_data_status.get("is_stale"))
        or (n_data and n_data.get("stale_data"))
        or (weather_gate and not weather_gate.get("allow_paper_recommendations", True))
    ):
        app_state["system_status"] = "YELLOW"
        reason = "Review missing files or stale weather data."
        if weather_gate and not weather_gate.get("allow_paper_recommendations", True):
            reason = f"NWS Weather Gate blocked recommendations: {weather_gate.get('no_trade_reason')}"
        app_state["action_needed"] = reason

    status_data = load_json(latest_status_json) if latest_status_json else None
    if isinstance(status_data, dict):
        forecast_info = status_data.get("forecast", {})
        if not forecast_info:
            f_dict = status_data.get("forecasts", {})
            if isinstance(f_dict, dict):
                forecast_info = f_dict.get("rules_v2_climatology") or (
                    next(iter(f_dict.values())) if f_dict else {}
                )

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

    best_sig = p_data.get("best_signal")
    if isinstance(best_sig, dict):
        app_state["latest_signal_action"] = best_sig.get("paper_action", "Unknown")
        app_state["latest_signal_ticker"] = best_sig.get("market_ticker", "Unknown")

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

    st.sidebar.subheader("🔌 Data Ingestion & Gates")
    if weather_gate:
        g_status = weather_gate.get("status", "UNKNOWN")
        g_emoji = {"OK": "🟢", "STALE": "🟡", "ERROR": "🔴", "MISSING": "⚪"}.get(g_status, "❓")
        st.sidebar.markdown(f"**NWS Gate Status:** {g_emoji} `{g_status}`")

        allow_recommendations = weather_gate.get("allow_paper_recommendations", False)
        allow_str = "✅ ALLOWED" if allow_recommendations else "❌ BLOCKED"
        st.sidebar.markdown(f"**Trading:** `{allow_str}`")

        age = weather_gate.get("observation_age_minutes")
        age_str = f"{age:.1f}m" if age is not None else "N/A"
        st.sidebar.markdown(f"**Obs Age:** `{age_str}`")

        if weather_gate.get("warnings"):
            st.sidebar.warning(f"⚠️ {len(weather_gate['warnings'])} warnings active.")
    else:
        st.sidebar.markdown("**NWS Gate Status:** ⚪ `UNKNOWN`")

    st.sidebar.divider()

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
        "Command Center",
        "Kalshi Market Console",
        "Active Kalshi Forecasts",
        "Paper Trading",
        "Weather / NWS",
        "Calibration / Learning",
        "Backtesting",
        "System Health",
    ])

    with tabs[0]:
        render_command_center(app_state, p_data, mkts)
    with tabs[1]:
        render_kalshi_market_console(mkts, o_data, p_data)
    with tabs[2]:
        render_active_forecasts(p_data)
    with tabs[3]:
        render_paper_trading(perf, settlements, trades, app_state=app_state)
    with tabs[4]:
        render_weather_nws(w_data, n_data)
    with tabs[5]:
        render_calibration_learning(pq_data, pq_md, l_data, cal_json, cal_md)
    with tabs[6]:
        render_backtesting()
    with tabs[7]:
        render_system_health(app_state)

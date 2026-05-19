"""System Health tab — gate telemetry, log tails, discovered file table."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from console.data_helpers import load_json, load_text
from shared.artifact_paths import (
    CALIBRATION_DIR,
    KALSHI_MARKET_SNAPSHOT_DIR,
    LATEST_PAPER_SIGNAL,
    LOGS_DIR,
    PAPER_TRADING_DIR,
    REPORTS_DIR,
    STATUS_DIR,
)


def render_system_health(app_state):
    st.header("⚙️ System Health & Raw Data")

    gate = app_state.get("weather_gate", {})
    if gate:
        status_val = gate.get("status", "UNKNOWN")
        allow_paper = gate.get("allow_paper_recommendations", False)
        status_emoji = {"OK": "🟢 OK", "STALE": "🟡 STALE", "ERROR": "🔴 ERROR", "MISSING": "⚪ MISSING"}.get(status_val, "❓ UNKNOWN")

        st.subheader("🌤️ NWS Weather Gate Telemetry")
        sgcol1, sgcol2, sgcol3 = st.columns(3)
        with sgcol1:
            st.metric("Freshness Gate Status", status_emoji)
        with sgcol2:
            st.metric("Trading Allowance", "✅ ALLOWED" if allow_paper else "❌ BLOCKED")
        with sgcol3:
            age = gate.get("observation_age_minutes")
            st.metric("Observation Age", f"{age:.1f} minutes" if age is not None else "N/A")

        if not allow_paper:
            st.error(f"⚠️ **Fail-Closed Gate Active:** Trading is blocked because: {gate.get('no_trade_reason') or 'No-trade reason unspecified.'}")
            if gate.get("warnings"):
                for w in gate["warnings"]:
                    st.warning(f"Warning detail: {w}")
        st.divider()

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

        st.subheader("Latest Paper Trading Signal")
        if LATEST_PAPER_SIGNAL.exists():
            with st.expander("View Paper Signal JSON"):
                st.json(load_json(LATEST_PAPER_SIGNAL))

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
    for d in [STATUS_DIR, REPORTS_DIR, LOGS_DIR, CALIBRATION_DIR, KALSHI_MARKET_SNAPSHOT_DIR, PAPER_TRADING_DIR]:
        if d.exists():
            for f in d.glob("*"):
                if f.is_file():
                    file_info.append({"Dir": d.name, "File": f.name, "Size": f.stat().st_size})
    if file_info:
        st.table(pd.DataFrame(file_info))


__all__ = ["render_system_health"]

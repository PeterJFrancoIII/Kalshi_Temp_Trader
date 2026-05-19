"""Command Center tab — top-level status overview."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from console.data_helpers import (
    aggregate_warnings,
    extract_best_signal,
    format_probability,
    format_temp,
    is_signal_stale_or_mismatched,
    load_json,
)


def render_command_center(app_state, p_data, mkts):
    st.header("🏠 Command Center")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Bot Mode", "DRY-RUN / PAPER")
    with col2:
        st.metric("Live Trading", "DISABLED")
    with col3:
        st.metric("Station", "KMIA")
    with col4:
        target_date = "N/A"
        if p_data and "trade_date" in p_data:
            target_date = p_data["trade_date"]
        st.metric("Target Date", target_date)

    st.divider()

    st.subheader("🌦️ Weather Freshness (NWS Gate)")
    n_data = app_state.get("n_data", {})
    gate = app_state.get("weather_gate", {})
    gate_status = gate.get("status", "UNKNOWN") if isinstance(gate, dict) else "UNKNOWN"
    gate_emoji = {"OK": "🟢", "STALE": "🟡", "ERROR": "🔴", "MISSING": "⚪"}.get(gate_status, "❓")
    allow_recommendations = gate.get("allow_paper_recommendations", False) if isinstance(gate, dict) else False
    allow_emoji = "✅ ALLOWED" if allow_recommendations else "❌ BLOCKED"

    col_g1, col_g2, col_g3, col_g4 = st.columns(4)
    with col_g1:
        st.metric("NWS Gate Status", f"{gate_emoji} {gate_status}")
    with col_g2:
        st.metric("Trading Allowance", allow_emoji)
    with col_g3:
        age = gate.get("observation_age_minutes") if isinstance(gate, dict) else None
        age_str = f"{age:.1f}m" if age is not None else "—"
        st.metric("Observation Age", age_str)
    with col_g4:
        st.metric("Current Temp", format_temp(n_data.get('current_temp_f') if n_data else None))

    if isinstance(gate, dict):
        if not allow_recommendations:
            st.error(f"⚠️ **Paper Recommendations Blocked:** {gate.get('no_trade_reason') or 'No-trade reason unspecified.'}")
        elif gate.get("warnings"):
            for warning in gate["warnings"]:
                st.warning(f"⚠️ {warning}")
    else:
        st.warning("No weather gate status found.")

    st.divider()

    st.subheader("⚖️ Kalshi Market Status")
    if mkts:
        kc1, kc2, kc3 = st.columns(3)
        mtime = "N/A"
        if app_state.get("latest_kalshi_json") and app_state["latest_kalshi_json"].exists():
            mtime = datetime.fromtimestamp(app_state["latest_kalshi_json"].stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        kc1.metric("Snapshot Time", mtime)
        kc2.metric("Total Markets", mkts.get("total_markets_returned", 0))
        kc3.metric("Active KXHIGHMIA", len(mkts.get("selected_temperature_markets", [])))

        if not mkts.get("selected_temperature_markets"):
            st.warning("⚠️ No active Miami temperature markets found.")
    else:
        st.warning("No Kalshi market snapshot found.")

    st.divider()

    st.subheader("🏆 Best Signal")
    best_sig = extract_best_signal(p_data)

    if is_signal_stale_or_mismatched(p_data, mkts):
        st.error("### NO SIGNAL — stale or mismatched paper signal ignored.")
    elif best_sig:
        st.info(f"**{best_sig.get('market_ticker', 'N/A')}** | Action: {best_sig.get('paper_action', 'N/A')}")
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Model Prob", format_probability(best_sig.get('model_probability')))
        sc2.metric("Market Prob", format_probability(best_sig.get('market_probability')))
        sc3.metric("Edge", format_probability(best_sig.get('edge'), show_plus=True))
        sc4.metric("Confidence", best_sig.get("confidence", "N/A").upper())

        with st.expander("Signal Details", expanded=True):
            st.write(f"**Contract:** {best_sig.get('market_title', 'N/A')}")
            st.write(f"**Status:** {best_sig.get('status', 'N/A')}")
            st.write(f"**Expected Value:** {best_sig.get('expected_value', 'N/A')}")
            st.write(f"**Yes Bid:** {best_sig.get('yes_bid', 'N/A')} | **Yes Ask:** {best_sig.get('yes_ask', 'N/A')}")
            st.write(f"**Last Price:** {best_sig.get('last_price', 'N/A')}")
            risk = best_sig.get("risk_decision")
            if isinstance(risk, dict):
                risk_passed = risk.get("passed", risk.get("all_passed"))
                risk_color = "✅" if risk_passed else "🚫"
                st.write(f"**Risk Gate:** {risk_color} {'PASS' if risk_passed else 'BLOCKED'}")

                gate_id = risk.get("failed_gate_id")
                gate_name = risk.get("failed_gate_name")
                if gate_id:
                    st.write(f"**Failed Gate ID:** `{gate_id}`")
                if gate_name:
                    st.write(f"**Failed Gate Name:** {gate_name}")

                no_trade = risk.get("no_trade_reason") or risk.get("blocking_reason")
                if no_trade:
                    st.warning(f"No-Trade Reason: {no_trade}")
            if best_sig.get("no_trade_reason"):
                st.warning(f"No-Trade Reason: {best_sig['no_trade_reason']}")
            if best_sig.get("warnings"):
                st.warning(" | ".join(best_sig["warnings"]))
    else:
        st.error(f"### STATUS: {p_data.get('status', 'NO_SIGNAL')}")
        st.write(f"**Forecast Source:** `{p_data.get('forecast_source', 'N/A')}`")
        st.write(f"**Market Snapshot:** `{p_data.get('market_snapshot_source', 'N/A')}`")
        if p_data.get("warnings"):
            for w in p_data["warnings"]:
                st.warning(w)

    st.divider()

    st.subheader("⚠️ Operator Attention")
    status_data = load_json(app_state.get("latest_status_json"))
    all_warnings = aggregate_warnings(p_data, mkts, n_data, status_data)

    if all_warnings:
        for w in all_warnings:
            st.warning(w)
    else:
        st.success("No critical warnings detected.")

    st.divider()

    st.subheader("⌨️ Action Commands")
    st.write("Run these commands in the terminal to update data or generate signals:")
    st.code("bash scripts/update_nws_live_data.sh", language="bash")
    st.code("bash scripts/update_kalshi_market_data.sh", language="bash")
    st.code("bash scripts/generate_paper_signal.sh", language="bash")
    st.code("bash scripts/run_kmia_daily_workflow.sh", language="bash")

    st.divider()
    st.subheader("🤖 Decisions")
    st.button("Record Decision", disabled=True, help="Coming Soon")

    st.divider()

    st.subheader("🔍 Raw / Debug Views")
    with st.expander("Raw Paper Signal JSON"):
        st.json(p_data)
    with st.expander("Raw Kalshi Snapshot JSON"):
        st.json(mkts)
    with st.expander("Raw Weather Snapshot JSON"):
        st.json(n_data)
    with st.expander("Latest Status JSON"):
        if app_state.get("latest_status_json"):
            st.json(load_json(app_state["latest_status_json"]))


__all__ = ["render_command_center"]

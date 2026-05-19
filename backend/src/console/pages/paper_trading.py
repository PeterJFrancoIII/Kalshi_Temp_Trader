"""Paper Trading tab — balances, open positions, settled history."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from console.data_helpers import format_pnl, load_json
from shared.artifact_paths import PAPER_LEDGER_FILE


def _format_rd(rd):
    if not rd:
        return "—"
    if isinstance(rd, dict):
        passed = rd.get("passed", rd.get("all_passed", True))
        return "PASS" if passed else "BLOCK"
    return str(rd)


def render_paper_trading(perf, settlements, trades, app_state=None):
    st.header("📈 Paper Trading Performance")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")

    gate = app_state.get("weather_gate", {}) if app_state else {}
    if gate:
        gate_status = gate.get("status", "UNKNOWN")
        gate_emoji = {"OK": "🟢", "STALE": "🟡", "ERROR": "🔴", "MISSING": "⚪"}.get(gate_status, "❓")
        allow_recommendations = gate.get("allow_paper_recommendations", False)
        allow_emoji = "✅ ALLOWED" if allow_recommendations else "❌ BLOCKED"
        age = gate.get("observation_age_minutes")
        age_str = f"{age:.1f} minutes" if age is not None else "N/A"

        st.subheader("🌤️ Weather Freshness (NWS Gate)")
        gcol1, gcol2, gcol3 = st.columns(3)
        with gcol1:
            st.metric("Gate Status", f"{gate_emoji} {gate_status}")
        with gcol2:
            st.metric("Trading Recommendations", allow_emoji)
        with gcol3:
            st.metric("Observation Age", age_str)

        if not allow_recommendations:
            st.error(f"⚠️ **Gate Blocking Reason:** {gate.get('no_trade_reason') or 'No-trade reason unspecified.'}")
        elif gate.get("warnings"):
            for warning in gate["warnings"]:
                st.warning(f"⚠️ {warning}")
        st.divider()

    if PAPER_LEDGER_FILE.exists():
        try:
            ledger_json = load_json(PAPER_LEDGER_FILE)
            if ledger_json:
                bal = ledger_json.get("account_balance")
                if bal is not None:
                    st.metric("Paper Account Balance", f"${bal:.2f}")
        except Exception:
            pass

    if perf:
        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        p_col1.metric("Settled Trades", perf.get("total_settled_trades", 0))
        p_col2.metric("Win Rate", f"{perf.get('win_rate', 0):.1%}")
        p_col3.metric("Simulated PnL", f"${perf.get('total_simulated_pnl', 0):.2f}")
        p_col4.metric("Pending Trades", perf.get("pending_trades", 0))
    else:
        st.info("No performance data available. Run `bash scripts/settle_paper_trades.sh`.")

    st.divider()

    st.subheader("🏁 Open Positions")
    open_trades = [t for t in trades if str(t.get("status", "")).lower() == "open"]
    if open_trades:
        df_open = pd.DataFrame(open_trades)

        if "risk_decision" in df_open.columns:
            df_open["risk_decision"] = df_open["risk_decision"].apply(_format_rd)

        display_cols = [
            "timestamp_utc", "market_ticker", "target_date", "forecast_bin",
            "contract_range_label", "execution_price", "risk_decision",
            "no_trade_reason",
        ]
        available = [c for c in display_cols if c in df_open.columns]
        st.dataframe(df_open[available].iloc[::-1], width="stretch", hide_index=True)
    else:
        st.info("No active open paper trades.")

    st.divider()

    st.subheader("📜 Trade History")
    settled_trades = [t for t in trades if str(t.get("status", "")).lower() == "settled"]
    if settled_trades:
        df_history = pd.DataFrame(settled_trades)
        display_cols = [
            "target_date", "market_ticker", "contract_range_label", "status",
            "pnl", "settled_at_utc", "risk_decision", "no_trade_reason",
        ]
        available = [c for c in display_cols if c in df_history.columns]

        df_display = df_history[available].copy()
        if "pnl" in df_display.columns:
            df_display["pnl"] = df_display["pnl"].apply(format_pnl)
        if "status" in df_display.columns:
            df_display["status"] = df_display["status"].apply(lambda x: str(x).upper() if x else "—")
        if "risk_decision" in df_display.columns:
            df_display["risk_decision"] = df_display["risk_decision"].apply(_format_rd)

        st.dataframe(df_display.iloc[::-1], width="stretch", hide_index=True)
    else:
        st.write("No settled trades in history.")

    st.divider()
    with st.expander("Raw Ledger / Settlement Debug"):
        st.subheader("Full Ledger (JSON)")
        st.json(trades)
        if settlements:
            st.subheader("Legacy Settlement Log (JSONL)")
            st.json(settlements)


__all__ = ["render_paper_trading"]

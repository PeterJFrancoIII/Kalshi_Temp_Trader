"""Active Forecasts tab — model insights and per-contract signal table."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from console.data_helpers import (
    format_probability,
    format_temp,
    load_forecast_data,
    normalize_signal_df,
)


def render_active_forecasts(p_data):
    st.header("📊 Active Kalshi Contract Forecasts")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")

    if not p_data:
        st.warning("No active contract forecasts found. Run:")
        st.code("bash scripts/update_kalshi_market_data.sh\nbash scripts/generate_paper_signal.sh")
        return

    allow_rec = p_data.get("allow_paper_recommendations", True)
    if not allow_rec:
        st.error(f"🔴 **CRITICAL SAFETY GATING ACTIVE:** Trading recommendations are actively blocked.\n\n**Reason:** {p_data.get('no_trade_reason') or 'No-trade reason unspecified.'}")

    best_sig = p_data.get("best_signal")
    if best_sig:
        if not allow_rec:
            st.subheader("🚫 Best Signal (BLOCKED)")
            st.info(f"**{best_sig.get('market_ticker', 'N/A')}** | Edge: {format_probability(best_sig.get('edge'), show_plus=True)} | Action: BLOCKED")
        else:
            st.subheader("🏆 Best Signal")
            st.info(f"**{best_sig.get('market_ticker', 'N/A')}** | Edge: {format_probability(best_sig.get('edge'), show_plus=True)} | Action: {best_sig.get('paper_action', 'N/A')}")

        bs_c1, bs_c2, bs_c3, bs_c4 = st.columns(4)
        bs_c1.metric("Model Prob", format_probability(best_sig.get('model_probability')))
        bs_c2.metric("Market Prob", format_probability(best_sig.get('market_probability')))
        bs_c3.metric("Edge", format_probability(best_sig.get('edge'), show_plus=True))
        bs_c4.metric("Confidence", "BLOCKED" if not allow_rec else best_sig.get("confidence", "N/A").upper())

    f_data = load_forecast_data(p_data.get("forecast_source"))
    if f_data:
        st.divider()
        st.subheader("🤖 Model Insights")
        mi_c1, mi_c2, mi_c3, mi_c4 = st.columns(4)
        mi_c1.metric("Deterministic Anchor", format_temp(f_data.get('deterministic_anchor_f')))
        mi_c2.metric("Distribution Mean", format_temp(f_data.get('final_distribution_mean_f')))
        mi_c3.metric("Distribution Mode", format_temp(f_data.get('final_distribution_mode_f')))
        mi_c4.metric("Suppression Shift", format_temp(f_data.get('weather_suppression_shift_f')))

        wi_c1, wi_c2, wi_c3, wi_c4 = st.columns(4)
        wi_c1.metric("Observed Max", format_temp(f_data.get('observed_max_so_far_f')))
        wi_c2.metric("Current Temp", format_temp(f_data.get('current_temp_f')))
        wi_c3.metric("Forecast Weight", f"{f_data.get('forecast_weight', 'N/A')}")
        wi_c4.metric("Climatology Weight", f"{f_data.get('climatology_weight', 'N/A')}")

        st.subheader("📈 Distribution Support")
        dist = f_data.get("integer_distribution", {})
        dist_cdf = f_data.get("integer_distribution_cdf", {})
        if dist:
            support = [int(k) for k, v in dist.items() if float(v) > 0]
            support_min = min(support) if support else "N/A"
            support_max = max(support) if support else "N/A"
            dist_sum = sum(float(v) for v in dist.values())

            p_gt_105 = 0.0
            if "105" in dist_cdf:
                p_gt_105 = 1.0 - float(dist_cdf["105"])

            ds_c1, ds_c2, ds_c3, ds_c4 = st.columns(4)
            ds_c1.metric("Support Min", format_temp(support_min))
            ds_c2.metric("Support Max", format_temp(support_max))
            ds_c3.metric("P(>105°F)", f"{p_gt_105*100:.1f}%")
            ds_c4.metric("Dist Sum", f"{dist_sum:.4f}")

    st.divider()
    signals = p_data.get("signals", [])

    all_no_trade = True
    if signals:
        for s in signals:
            act = str(s.get("paper_action", "")).upper()
            if "BUY" in act:
                all_no_trade = False
                break
    else:
        all_no_trade = True

    if all_no_trade:
        st.info("ℹ️ **No active paper trading candidates found.**")
        reason = p_data.get("no_trade_reason") or "No active edge or risk parameters not met."
        st.warning(f"**Reason:** {reason}")

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
            "raw_edge": "Raw Edge",
            "executable_edge": "Executable Edge",
            "breakeven_probability": "Breakeven %",
            "executable_price": "Exec Price",
            "risk_decision": "Risk Decision",
            "no_trade_reason": "No-Trade Reason",
            "time_to_close_minutes": "Time to Close",
            "speed_to_roi_score": "Speed-to-ROI",
            "paper_action": "Paper Action",
        }

        df_display_sig = df_sig.copy()

        expected_cols = [
            "model_probability", "market_probability", "edge", "raw_edge",
            "executable_edge", "breakeven_probability", "executable_price",
            "risk_decision", "no_trade_reason", "paper_action",
            "threshold_f", "time_to_close_minutes",
        ]
        for c in expected_cols:
            if c not in df_display_sig.columns:
                df_display_sig[c] = None

        def format_rd(rd):
            if not rd:
                return "PASS"
            if isinstance(rd, dict):
                passed = rd.get("passed")
                if passed is None:
                    passed = rd.get("all_passed", True)
                return "PASS" if passed else "BLOCK"
            return str(rd)

        def format_ntr(row):
            reason = row.get("no_trade_reason")
            if reason:
                return str(reason)
            rd = row.get("risk_decision")
            if isinstance(rd, dict):
                return rd.get("no_trade_reason") or rd.get("reason") or "None"
            return "None"

        df_display_sig["risk_decision"] = df_display_sig["risk_decision"].apply(format_rd)
        df_display_sig["no_trade_reason"] = df_display_sig.apply(format_ntr, axis=1)

        if not allow_rec:
            df_display_sig["paper_action"] = "BLOCKED"

        if "model_probability" in df_display_sig.columns:
            df_display_sig["model_probability"] = df_display_sig["model_probability"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "N/A")
        if "market_probability" in df_display_sig.columns:
            df_display_sig["market_probability"] = df_display_sig["market_probability"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "N/A")
        if "edge" in df_display_sig.columns:
            df_display_sig["edge"] = df_display_sig["edge"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "—")
        if "raw_edge" in df_display_sig.columns:
            df_display_sig["raw_edge"] = df_display_sig["raw_edge"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "—")
        if "executable_edge" in df_display_sig.columns:
            df_display_sig["executable_edge"] = df_display_sig["executable_edge"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "—")
        if "breakeven_probability" in df_display_sig.columns:
            df_display_sig["breakeven_probability"] = df_display_sig["breakeven_probability"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "—")
        if "executable_price" in df_display_sig.columns:
            df_display_sig["executable_price"] = df_display_sig["executable_price"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "—")
        if "threshold_f" in df_display_sig.columns:
            df_display_sig["threshold_f"] = df_display_sig["threshold_f"].apply(lambda x: f"{x:.1f}°F" if pd.notnull(x) else "—")
        if "time_to_close_minutes" in df_display_sig.columns:
            df_display_sig["time_to_close_minutes"] = df_display_sig["time_to_close_minutes"].apply(lambda x: f"{x:.1f}m" if pd.notnull(x) else "—")

        existing_cols_sig = [c for c in col_map_sig.keys() if c in df_display_sig.columns]
        df_final = df_display_sig[existing_cols_sig].rename(columns=col_map_sig)
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        blocked = [s for s in signals if isinstance(s.get("risk_decision"), dict) and not s["risk_decision"].get("passed", s["risk_decision"].get("all_passed", True))]
        if blocked:
            st.subheader("🚫 Risk Gate Blocks")
            for s in blocked:
                rd = s["risk_decision"]
                reason = rd.get("no_trade_reason") or rd.get("blocking_reason") or rd.get("reason") or "Risk gate blocked"
                st.error(f"**{s.get('market_ticker', 'N/A')}**: {reason}")
    else:
        st.error(f"### STATUS: {p_data.get('status', 'NO_SIGNAL')}")
        st.write(f"**Forecast Source:** `{p_data.get('forecast_source', 'N/A')}`")
        st.write(f"**Market Snapshot:** `{p_data.get('market_snapshot_source', 'N/A')}`")
        if p_data.get("warnings"):
            for w in p_data["warnings"]:
                st.warning(w)
        st.info("No active contract forecasts found in latest signal data.")


__all__ = ["render_active_forecasts"]

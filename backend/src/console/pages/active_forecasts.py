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
from console.market_visibility import (
    MARKET_STATUS_CLOSED,
    MARKET_STATUS_MISSING_FORECAST,
    MARKET_STATUS_STALE_MARKET_DATA,
    build_kalshi_bins_rows,
    format_snapshot_age_line,
    is_tradable_status,
    partition_market_dates,
    status_banner_message,
    status_badge,
)


def _render_bins_for_date(
    date: str,
    date_data: dict,
    market_snapshot: dict,
) -> None:
    """Model forecast probabilities per bin with market-status visibility."""
    market_status = date_data.get("market_status", "")
    if not date_data.get("max_age_minutes") and market_snapshot:
        date_data = {**date_data, "max_age_minutes": market_snapshot.get("max_age_minutes")}

    st.markdown(f"#### {date} — {status_badge(market_status)}")
    if not is_tradable_status(market_status):
        st.caption("Not tradable for active paper allocation.")

    snap_line = format_snapshot_age_line(date_data, market_snapshot)
    if snap_line:
        st.caption(f"Snapshot: {snap_line}")

    banner = status_banner_message(date, date_data, market_status)
    if banner:
        if market_status == MARKET_STATUS_STALE_MARKET_DATA:
            st.error(banner)
        elif market_status == MARKET_STATUS_MISSING_FORECAST:
            st.warning(banner)
        elif market_status == MARKET_STATUS_CLOSED:
            st.info(banner)
        else:
            st.warning(banner)

    prob_rows = build_kalshi_bins_rows(date_data)
    contracts = date_data.get("contracts") or []
    if not prob_rows and market_status == MARKET_STATUS_MISSING_FORECAST and contracts:
        st.warning(
            f"Forecast distribution missing for {date}. "
            f"Showing {len(contracts)} contract(s) without fabricated probabilities."
        )
    elif not prob_rows:
        st.warning(f"⚠️ No contracts or forecast probabilities available for {date}.")
    else:
        df_probs = pd.DataFrame(prob_rows)
        st.dataframe(
            df_probs,
            width="stretch",
            hide_index=True,
            column_config={
                "Model Prob": st.column_config.NumberColumn("Model Prob", format="%.2f%%"),
            },
        )


def render_date_forecasts(
    date: str,
    date_data: dict,
    inside_expander: bool,
    use_11_cols: bool,
    allow_rec: bool,
    market_snapshot: dict | None = None,
):
    """Renders all forecast-related tables and metrics for a specific market date."""
    market_snapshot = market_snapshot or {}

    _render_bins_for_date(date, date_data, market_snapshot)

    # 2. Display Model Insights & Distribution Support if forecast source data exists
    forecast_src = date_data.get("forecast_source")
    f_data = load_forecast_data(forecast_src) if forecast_src else None
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

    # 3. Suggested Paper Contracts & Actions
    st.divider()
    signals = date_data.get("signals", [])

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
        reason = date_data.get("no_trade_reason") or "No active edge or risk parameters not met."
        if not date_data.get("no_trade_reason") and not signals:
            reason = "No suggested paper contracts available."
        st.warning(f"**Reason:** {reason}")

    if signals:
        df_sig = pd.DataFrame(signals)
        df_sig = normalize_signal_df(df_sig)

        if use_11_cols:
            event_ticker = date_data.get("event_ticker", "N/A")
            sig_rows = []
            for s in signals:
                warnings_list = s.get("warnings", [])
                warnings_str = ", ".join(warnings_list) if warnings_list else "None"
                
                sig_rows.append({
                    "Market Date": date,
                    "Market Ticker": event_ticker,
                    "Contract Ticker": s.get("market_ticker") or "N/A",
                    "Bin/Range": s.get("contract_range") or s.get("contract_range_label") or "N/A",
                    "Model Prob": s.get("model_probability") * 100 if s.get("model_probability") is not None else None,
                    "Market Prob": s.get("market_probability") * 100 if s.get("market_probability") is not None else None,
                    "Raw Edge": s.get("raw_edge", 0) * 100 if s.get("raw_edge") is not None else None,
                    "Executable Edge": s.get("executable_edge", s.get("edge", 0)) * 100 if s.get("executable_edge") is not None or s.get("edge") is not None else None,
                    "Paper Action": "BLOCKED" if not allow_rec else s.get("paper_action", "NO TRADE"),
                    "No-Trade Reason": s.get("no_trade_reason") or "Risk gate passed. Candidate for trade.",
                    "Warnings": warnings_str
                })
            df_final = pd.DataFrame(sig_rows)
            st.dataframe(
                df_final,
                width="stretch",
                hide_index=True,
                column_config={
                    "Model Prob": st.column_config.NumberColumn("Model Prob", format="%.1f%%"),
                    "Market Prob": st.column_config.NumberColumn("Market Prob", format="%.1f%%"),
                    "Raw Edge": st.column_config.NumberColumn("Raw Edge", format="%+.1f%%"),
                    "Executable Edge": st.column_config.NumberColumn("Executable Edge", format="%+.1f%%")
                }
            )
        else:
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
            st.dataframe(df_final, width="stretch", hide_index=True)

            blocked = [s for s in signals if isinstance(s.get("risk_decision"), dict) and not s["risk_decision"].get("passed", s["risk_decision"].get("all_passed", True))]
            if blocked:
                st.subheader("🚫 Risk Gate Blocks")
                for s in blocked:
                    rd = s["risk_decision"]
                    reason = rd.get("no_trade_reason") or rd.get("blocking_reason") or rd.get("reason") or "Risk gate blocked"
                    st.error(f"**{s.get('market_ticker', 'N/A')}**: {reason}")

    # Render date-specific warnings
    date_warnings = date_data.get("warnings", [])
    if date_warnings:
        with st.container():
            for w in date_warnings:
                st.warning(f"⚠️ [{date}] {w}")


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

    # Get events grouped by date, with fallback to top-level fields for single-date compatibility
    events_by_date = p_data.get("events_by_date")
    if not events_by_date:
        primary_date = p_data.get("primary_event_date") or "N/A"
        events_by_date = {
            primary_date: {
                "event_ticker": "N/A",
                "forecast_source": p_data.get("forecast_source"),
                "signals": p_data.get("signals", []),
                "dynamic_contract_probabilities": p_data.get("dynamic_contract_probabilities", {}),
                "status": p_data.get("status", "NO_SIGNAL"),
                "warnings": p_data.get("warnings", [])
            }
        }

    market_snapshot = p_data.get("market_snapshot") or {}
    open_market_dates = p_data.get("open_market_dates") or []
    primary_dates, pre_open_dates, closed_dates = partition_market_dates(
        events_by_date, open_market_dates
    )

    if open_market_dates:
        st.success(f"**Open market dates:** {', '.join(open_market_dates)}")

    if market_snapshot.get("is_stale"):
        st.warning(
            "Global Kalshi market snapshot is stale — refresh before paper evaluation."
        )

    st.subheader("🔮 Model Forecast Probabilities per Bin")

    if len(events_by_date) == 1:
        only_date = next(iter(events_by_date))
        render_date_forecasts(
            only_date,
            events_by_date[only_date],
            inside_expander=False,
            use_11_cols=False,
            allow_rec=allow_rec,
            market_snapshot=market_snapshot,
        )
    else:
        for date in primary_dates:
            render_date_forecasts(
                date,
                events_by_date[date],
                inside_expander=False,
                use_11_cols=True,
                allow_rec=allow_rec,
                market_snapshot=market_snapshot,
            )
        if pre_open_dates:
            with st.expander("Pre-open markets (secondary)", expanded=False):
                for date in pre_open_dates:
                    render_date_forecasts(
                        date,
                        events_by_date[date],
                        inside_expander=True,
                        use_11_cols=True,
                        allow_rec=allow_rec,
                        market_snapshot=market_snapshot,
                    )
        if closed_dates:
            with st.expander(
                "Closed / historical markets — not used for active allocation",
                expanded=False,
            ):
                for date in closed_dates:
                    render_date_forecasts(
                        date,
                        events_by_date[date],
                        inside_expander=True,
                        use_11_cols=True,
                        allow_rec=allow_rec,
                        market_snapshot=market_snapshot,
                    )


__all__ = ["render_active_forecasts"]


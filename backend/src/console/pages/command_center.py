"""Command Center tab — top-level status overview."""

from __future__ import annotations

from datetime import datetime
from shared.timestamp_utils import extract_embedded_timestamp, extract_timestamp_from_filename

import streamlit as st

from console.data_helpers import (
    aggregate_warnings,
    extract_best_signal,
    format_probability,
    format_temp,
    is_signal_stale_or_mismatched,
    load_json,
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

# UI allocation mode keys → engine mode strings (read-only display recomputation).
_ALLOCATION_MODE_OPTIONS = (
    ("guarantee_profit_mode", "guarantee_profit", "Guarantee Profit Mode"),
    ("risk_adjusted_mode", "risk_adjusted", "Risk-Adjusted Mode"),
    ("conservative_mode", "conservative", "Conservative Mode"),
)
_ALLOCATION_MODE_LABELS = {uk: lbl for uk, _em, lbl in _ALLOCATION_MODE_OPTIONS}


def _engine_mode_to_ui_key(engine_mode: str) -> str:
    if not engine_mode:
        return "risk_adjusted_mode"
    if engine_mode.startswith("guarantee_profit"):
        return "guarantee_profit_mode"
    if engine_mode == "conservative":
        return "conservative_mode"
    return "risk_adjusted_mode"


def _guaranteed_profit_reason(money_dist: dict) -> str:
    explicit = money_dist.get("guaranteed_profit_reason")
    if explicit:
        return str(explicit)
    if money_dist.get("guaranteed_profit_possible"):
        return (
            "Active contracts partition the outcome space with combined executable cost "
            "below $1.00 — dutch-book style allocation is feasible."
        )
    for warning in money_dist.get("warnings") or []:
        if "guaranteed" in str(warning).lower():
            return str(warning)
    return (
        "Guaranteed net-positive allocation is not mathematically available: "
        "contracts do not form a full partition below $1.00 combined cost, or "
        "risk gates block dutch allocation. Showing best risk-adjusted paper sizing."
    )


def _recompute_money_distribution(
    p_data: dict,
    bankroll: float,
    engine_mode: str,
) -> dict:
    """Display-only recomputation; does not persist bankroll or place orders."""
    from risk.money_distribution import distribute_money

    primary_date = p_data.get("primary_event_date") or "unknown"
    primary_event = (p_data.get("events_by_date") or {}).get(primary_date, {})
    signals = primary_event.get("signals") or p_data.get("signals") or []
    forecast_data = primary_event.get("forecast_data") or {}
    return distribute_money(
        bankroll=float(bankroll),
        active_signals=signals,
        forecast_data=forecast_data,
        weather_gate=p_data.get("weather_gate") or {},
        ledger_summary={"daily_pnl": 0.0, "weekly_pnl": 0.0, "active_trades_by_date": {}},
        target_date=primary_date,
        mode=engine_mode,
    )


def _render_money_distribution_panel(p_data: dict) -> None:
    """Paper-only capital allocation explorer (UI read-only; no orders or ledger writes)."""
    import pandas as pd

    st.subheader("💰 Paper Money Distribution by Bin")
    st.caption(
        "DRY-RUN / PAPER EVALUATION ONLY — no real trading, no order execution. "
        "Adjust bankroll or mode to explore allocations; nothing is saved to the ledger."
    )

    snapshot_dist = p_data.get("money_distribution") if isinstance(p_data, dict) else None
    default_bankroll = 1000.0
    if snapshot_dist and snapshot_dist.get("total_available_dollars") is not None:
        default_bankroll = float(snapshot_dist["total_available_dollars"])

    default_ui_mode = _engine_mode_to_ui_key(
        (snapshot_dist or {}).get("allocation_mode", "risk_adjusted")
    )
    ui_mode_keys = [opt[0] for opt in _ALLOCATION_MODE_OPTIONS]
    default_mode_index = ui_mode_keys.index(default_ui_mode) if default_ui_mode in ui_mode_keys else 1

    inp_col1, inp_col2 = st.columns(2)
    with inp_col1:
        bankroll_input = st.number_input(
            "Total Available Dollars",
            min_value=0.0,
            value=default_bankroll,
            step=50.0,
            help="Paper bankroll for display sizing only (not persisted).",
        )
    with inp_col2:
        selected_ui_mode = st.selectbox(
            "Allocation Mode",
            options=ui_mode_keys,
            index=default_mode_index,
            format_func=lambda k: _ALLOCATION_MODE_LABELS.get(k, k),
        )

    if selected_ui_mode not in ui_mode_keys:
        selected_ui_mode = default_ui_mode
    engine_mode = next(
        (em for uk, em, _ in _ALLOCATION_MODE_OPTIONS if uk == selected_ui_mode),
        "risk_adjusted",
    )

    money_dist = snapshot_dist
    recompute = (
        isinstance(p_data, dict)
        and (
            abs(bankroll_input - default_bankroll) > 0.01
            or selected_ui_mode != default_ui_mode
        )
    )
    if recompute:
        try:
            money_dist = _recompute_money_distribution(p_data, bankroll_input, engine_mode)
            st.caption("Showing live recomputation for the bankroll and mode selected above.")
        except Exception as exc:
            st.error(f"Could not recompute money distribution: {exc}")
            money_dist = snapshot_dist

    if not money_dist:
        st.info(
            "No money distribution block in the latest paper signal. "
            "Run `bash scripts/generate_paper_signal.sh` to populate allocations."
        )
        return

    safety = money_dist.get("safety") or {}
    if safety.get("no_real_trading") is not False and safety.get("no_order_execution") is not False:
        st.success(
            "Paper-only safety: no_real_trading=true, no_order_execution=true — "
            "this panel does not place or modify orders."
        )

    guarantee = bool(money_dist.get("guaranteed_profit_possible"))
    guarantee_reason = _guaranteed_profit_reason(money_dist)
    market_date = money_dist.get("market_date") or p_data.get("primary_event_date") or "N/A"

    st.markdown("**Summary**")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Guaranteed Profit Possible", "Yes" if guarantee else "No")
    s2.metric("Total Allocated", f"${money_dist.get('total_allocated', 0):,.2f}")
    s3.metric("Cash Unallocated", f"${money_dist.get('cash_unallocated', 0):,.2f}")
    prob_profit = money_dist.get("probability_of_profit")
    s4.metric(
        "Probability of Profit",
        f"{prob_profit * 100:.1f}%" if prob_profit is not None else "—",
        help="Fraction of model probability mass on net-positive portfolio outcomes.",
    )

    s5, s6, s7, s8 = st.columns(4)
    s5.metric("Portfolio Expected Profit", f"${money_dist.get('portfolio_expected_profit', 0):,.2f}")
    s6.metric("Worst Case Profit", f"${money_dist.get('worst_case_profit', 0):,.2f}")
    s7.metric("Best Case Profit", f"${money_dist.get('best_case_profit', 0):,.2f}")
    s8.metric("Market Date", market_date)

    st.write(f"**Guaranteed Profit Reason:** {guarantee_reason}")
    st.write(f"**Allocation Mode (engine):** `{money_dist.get('allocation_mode', 'N/A')}`")

    if guarantee:
        st.success("Guaranteed net-positive allocation is mathematically possible for this contract set.")
    else:
        st.warning(
            "Guaranteed net-positive allocation unavailable — "
            "allocations use risk-adjusted or conservative paper sizing."
        )

    events_by_date = p_data.get("events_by_date") or {}
    primary_date = p_data.get("primary_event_date")
    other_dates = sorted(d for d in events_by_date if d != primary_date)
    if other_dates and primary_date:
        st.info(
            f"Money distribution covers **primary date {primary_date}** only. "
            f"Other active market dates in this signal: {', '.join(other_dates)}."
        )

    liquidity_warnings = [
        w for w in (money_dist.get("warnings") or [])
        if "liquid" in str(w).lower() or "depth" in str(w).lower()
    ]
    if liquidity_warnings:
        for w in liquidity_warnings:
            st.warning(w)
    else:
        st.caption(
            "Liquidity / orderbook depth is not wired into money_distribution; "
            "allocation uses model edge and risk gates only."
        )

    rows = money_dist.get("rows") or []
    if rows:
        st.markdown("**Allocation by Contract**")
        alloc_df = pd.DataFrame(
            [
                {
                    "Contract": r.get("contract_ticker"),
                    "Market Date": market_date,
                    "Bin / Range": r.get("bin_range"),
                    "Model Prob": r.get("model_probability"),
                    "Market Prob": r.get("market_probability"),
                    "Executable Price": r.get("executable_price"),
                    "Executable Edge": r.get("executable_edge"),
                    "Recommended Paper Allocation": r.get("recommended_allocation_dollars"),
                    "Estimated Contracts": r.get("estimated_contracts"),
                    "Expected Profit": r.get("expected_profit"),
                    "Max Loss": r.get("max_loss"),
                    "No-Trade Reason": r.get("no_trade_reason") or "—",
                }
                for r in rows
            ]
        )
        st.dataframe(
            alloc_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Model Prob": st.column_config.NumberColumn("Model Prob", format="%.1%"),
                "Market Prob": st.column_config.NumberColumn("Market Prob", format="%.1%"),
                "Executable Price": st.column_config.NumberColumn(
                    "Executable Price", format="%.3f"
                ),
                "Executable Edge": st.column_config.NumberColumn(
                    "Executable Edge", format="%+.3f"
                ),
                "Recommended Paper Allocation": st.column_config.NumberColumn(
                    "Recommended Paper Allocation", format="$%.2f"
                ),
                "Estimated Contracts": st.column_config.NumberColumn(
                    "Estimated Contracts", format="%d"
                ),
                "Expected Profit": st.column_config.NumberColumn(
                    "Expected Profit", format="$%.2f"
                ),
                "Max Loss": st.column_config.NumberColumn("Max Loss", format="$%.2f"),
            },
        )

    outcomes = money_dist.get("pnl_by_outcome") or []
    if outcomes:
        st.markdown("**Portfolio PnL by Settlement Outcome**")
        outcome_df = pd.DataFrame(
            [
                {
                    "Settlement Outcome": o.get("outcome_bin"),
                    "Outcome Probability": o.get("probability"),
                    "Portfolio PnL": o.get("net_pnl"),
                    "Profitable?": 1 if (o.get("net_pnl") or 0) > 0.0001 else 0,
                }
                for o in outcomes
            ]
        )
        st.dataframe(
            outcome_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Outcome Probability": st.column_config.NumberColumn(
                    "Outcome Probability", format="%.1%"
                ),
                "Portfolio PnL": st.column_config.NumberColumn(
                    "Portfolio PnL", format="$%.2f"
                ),
                "Profitable?": st.column_config.NumberColumn(
                    "Profitable?", format="%d", help="1 = profitable, 0 = not profitable"
                ),
            },
        )

    extra_warnings = [
        w for w in (money_dist.get("warnings") or [])
        if w not in liquidity_warnings
    ]
    if extra_warnings:
        st.markdown("**Distribution Warnings**")
        for w in extra_warnings:
            st.warning(w)


def _render_suggested_paper_contracts_table(date: str, date_data: dict) -> None:
    """Suggested Paper Contracts & Actions table for one event date."""
    import pandas as pd

    st.subheader("📋 Suggested Paper Contracts & Actions")
    event_ticker = date_data.get("event_ticker", "N/A")
    market_status = date_data.get("market_status", "")
    signals = date_data.get("signals", [])
    tradable = is_tradable_status(market_status)

    if signals:
        sig_rows = []
        for s in signals:
            warnings_list = s.get("warnings", [])
            warnings_str = ", ".join(warnings_list) if warnings_list else "None"
            paper_action = s.get("paper_action", "NO TRADE")
            if not tradable and "BUY" in str(paper_action).upper():
                paper_action = "NO TRADE (market not tradable)"

            sig_rows.append({
                "Market Date": date,
                "Market Ticker": event_ticker,
                "Contract Ticker": s.get("market_ticker") or "N/A",
                "Bin/Range": s.get("contract_range") or s.get("contract_range_label") or "N/A",
                "Model Prob": s.get("model_probability") * 100 if s.get("model_probability") is not None else None,
                "Market Prob": s.get("market_probability") * 100 if s.get("market_probability") is not None else None,
                "Raw Edge": s.get("raw_edge", 0) * 100 if s.get("raw_edge") is not None else None,
                "Executable Edge": s.get("executable_edge", s.get("edge", 0)) * 100
                if s.get("executable_edge") is not None or s.get("edge") is not None
                else None,
                "Paper Action": paper_action,
                "No-Trade Reason": s.get("no_trade_reason") or "Risk gate passed. Candidate for trade.",
                "Warnings": warnings_str,
            })
        df_sig_rows = pd.DataFrame(sig_rows)
        st.dataframe(
            df_sig_rows,
            width="stretch",
            hide_index=True,
            column_config={
                "Model Prob": st.column_config.NumberColumn("Model Prob", format="%.1f%%"),
                "Market Prob": st.column_config.NumberColumn("Market Prob", format="%.1f%%"),
                "Raw Edge": st.column_config.NumberColumn("Raw Edge", format="%+.1f%%"),
                "Executable Edge": st.column_config.NumberColumn("Executable Edge", format="%+.1f%%"),
            },
        )
    else:
        st.info("No suggested paper contracts available.")

    date_warnings = date_data.get("warnings", [])
    for w in date_warnings:
        st.warning(f"⚠️ [{date}] {w}")


def _render_kalshi_bins_for_date(
    date: str,
    date_data: dict,
    market_snapshot: dict,
) -> None:
    """Kalshi Bins table and status banners for one event date."""
    import pandas as pd

    market_status = date_data.get("market_status", "")
    if not date_data.get("max_age_minutes") and market_snapshot:
        date_data = {**date_data, "max_age_minutes": market_snapshot.get("max_age_minutes")}

    st.markdown(f"#### {date} — {status_badge(market_status)}")
    if not is_tradable_status(market_status):
        st.caption("Not tradable for active paper allocation.")

    snap_line = format_snapshot_age_line(date_data, market_snapshot)
    if snap_line:
        st.caption(f"Snapshot: {snap_line}")

    if date_data.get("open_start_et") or date_data.get("open_end_et"):
        st.caption(
            f"Market window (ET): {date_data.get('open_start_et', '—')} → "
            f"{date_data.get('open_end_et', '—')}"
        )

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
            f"Showing {len(contracts)} open contract(s) without fabricated model probabilities."
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

    _render_suggested_paper_contracts_table(date, date_data)


def _render_kalshi_bins_and_contracts_section(p_data: dict, events_by_date: dict) -> None:
    """Open / stale / missing / closed market visibility for Kalshi bins."""
    market_snapshot = p_data.get("market_snapshot") if isinstance(p_data, dict) else {}
    if not isinstance(market_snapshot, dict):
        market_snapshot = {}

    open_market_dates = p_data.get("open_market_dates") or []
    primary_dates, pre_open_dates, closed_dates = partition_market_dates(
        events_by_date, open_market_dates
    )

    st.subheader("🔮 Kalshi Bins & Model Forecast Probabilities")

    if open_market_dates:
        st.success(f"**Open market dates:** {', '.join(open_market_dates)}")

    if market_snapshot.get("is_stale"):
        st.warning(
            "Global Kalshi market snapshot is stale "
            f"({market_snapshot.get('snapshot_age_minutes', '—')} min old, "
            f"max {market_snapshot.get('max_age_minutes', '—')} min). "
            "Refresh before paper evaluation."
        )

    for date in primary_dates:
        _render_kalshi_bins_for_date(date, events_by_date[date], market_snapshot)

    if pre_open_dates:
        with st.expander("Pre-open markets (secondary)", expanded=False):
            for date in pre_open_dates:
                _render_kalshi_bins_for_date(date, events_by_date[date], market_snapshot)

    if closed_dates:
        with st.expander(
            "Closed / historical markets — not used for active allocation",
            expanded=False,
        ):
            for date in closed_dates:
                _render_kalshi_bins_for_date(date, events_by_date[date], market_snapshot)


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
            latest_path = app_state["latest_kalshi_json"]
            ts = extract_embedded_timestamp(latest_path)
            if not ts:
                ts = extract_timestamp_from_filename(latest_path.name)
            if ts:
                mtime = ts.strftime('%Y-%m-%d %H:%M')
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

    events_by_date = p_data.get("events_by_date")
    if not events_by_date:
        primary_date = p_data.get("primary_event_date") or "N/A"
        events_by_date = {
            primary_date: {
                "event_ticker": "N/A",
                "forecast_source": p_data.get("forecast_source"),
                "signals": p_data.get("signals", []),
                "dynamic_contract_probabilities": p_data.get("dynamic_contract_probabilities", {}),
                "market_status": p_data.get("market_status", "OPEN"),
                "status": p_data.get("status", "NO_SIGNAL"),
                "warnings": p_data.get("warnings", []),
            }
        }

    _render_kalshi_bins_and_contracts_section(p_data, events_by_date)

    st.divider()

    _render_money_distribution_panel(p_data if isinstance(p_data, dict) else {})

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

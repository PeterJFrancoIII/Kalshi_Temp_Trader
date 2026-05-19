"""Kalshi Market Console tab — orderbook + hypothetical cost calculator."""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from console.data_helpers import (
    calculate_hypothetical_costs,
    derive_orderbook_prices,
    extract_market_rows,
)


def render_kalshi_market_console(m_data, o_data, s_data):
    st.header("🏪 Kalshi Market Console")
    st.warning("🚨 **DRY-RUN / PAPER ONLY — NO REAL TRADING EXECUTION**")

    col1, col2, col3, col4 = st.columns(4)
    m_time = m_data.get("fetched_at_utc", "N/A") if isinstance(m_data, dict) else "N/A"
    o_time = o_data.get("fetched_at_utc", "N/A") if isinstance(o_data, dict) else "N/A"
    col1.metric("Market Snapshot Time", m_time)
    col2.metric("Orderbook Snapshot Time", o_time)

    markets = m_data.get("markets", []) if isinstance(m_data, dict) else []
    obs = o_data.get("orderbooks", {}) if isinstance(o_data, dict) else {}
    col3.metric("Market Count", len(markets))
    col4.metric("Orderbook Count", len(obs))

    status = o_data.get("status", "N/A") if isinstance(o_data, dict) else "N/A"
    st.write(f"**Orderbook Status:** {status}")

    warnings = []
    if isinstance(m_data, dict) and m_data.get("warnings"):
        warnings.extend(m_data["warnings"])
    if isinstance(o_data, dict) and o_data.get("warnings"):
        warnings.extend(o_data["warnings"])

    if warnings:
        for w in warnings:
            st.warning(w)

    if status == "EMPTY":
        st.info("No active KXHIGHMIA markets/orderbooks available.")
        st.write("You can run the following command to update data:")
        st.code("bash scripts/update_kalshi_market_data.sh", language="bash")

    rows = extract_market_rows(markets, s_data, o_data)
    if rows:
        st.subheader("Active Contracts")

        signal_date = None
        if s_data and "forecast_source" in s_data:
            dm = re.search(r"(\d{4}-\d{2}-\d{2})", s_data["forecast_source"])
            if dm:
                signal_date = dm.group(1)

        df_active = pd.DataFrame(rows)
        if signal_date:
            mismatched = df_active[df_active["date"] != signal_date]
            if not mismatched.empty:
                st.warning(f"⚠️ **Date Mismatch Detected:** Signal date is {signal_date}, but some contracts are for other dates. Probabilities for mismatched dates will show as N/A.")

        rename_map = {
            "date": "Date",
            "ticker": "Ticker",
            "bin": "Bin",
            "title": "Title",
            "yes_bid": "YES Bid",
            "yes_ask": "YES Ask",
            "model_probability": "Model %",
            "market_probability": "Market %",
            "edge": "Edge",
            "action": "Action",
        }

        streamlit_col_config = {
            "model_probability": st.column_config.NumberColumn("Model %", format="%.1f%%"),
            "market_probability": st.column_config.NumberColumn("Market %", format="%.1f%%"),
            "edge": st.column_config.NumberColumn("Edge", format="%+.1f%%"),
        }

        df_active["model_probability"] = df_active["model_probability"].apply(lambda x: x * 100 if x is not None else None)
        df_active["market_probability"] = df_active["market_probability"].apply(lambda x: x * 100 if x is not None else None)
        df_active["edge"] = df_active["edge"].apply(lambda x: x * 100 if x is not None else None)

        display_cols = [c for c in rename_map.keys() if c in df_active.columns]
        st.dataframe(
            df_active[display_cols].rename(columns=rename_map),
            column_config=streamlit_col_config,
            width="stretch",
            hide_index=True,
        )

        tickers = [r["ticker"] for r in rows]
        selected_ticker = st.selectbox("Select Contract Ticker", tickers)

        if selected_ticker:
            selected_row = next((r for r in rows if r["ticker"] == selected_ticker), None)
            ob = obs.get(selected_ticker, {})
            prices = derive_orderbook_prices(ob)

            st.subheader(f"Contract: {selected_row['title'] if selected_row else selected_ticker}")
            st.write(f"**Bin:** {selected_row['bin'] if selected_row else 'N/A'}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Top YES Bid", prices["top_yes_bid"] if prices["top_yes_bid"] is not None else "N/A")
            c2.metric("Top NO Bid", prices["top_no_bid"] if prices["top_no_bid"] is not None else "N/A")
            c3.metric("Derived YES Ask", prices["derived_yes_ask"] if prices["derived_yes_ask"] is not None else "N/A")
            c4.metric("Derived NO Ask", prices["derived_no_ask"] if prices["derived_no_ask"] is not None else "N/A")

            st.info("💡 **Derived Ask Logic:** Kalshi orderbooks show YES and NO bids. YES ask can be derived from the best NO bid as 100 - NO bid; NO ask can be derived from the best YES bid as 100 - YES bid.")

            st.subheader("Orderbook Depth")
            dc1, dc2 = st.columns(2)
            with dc1:
                st.write("**YES Bids**")
                yes_bids = ob.get("yes_bids", [])
                if yes_bids:
                    st.dataframe(yes_bids[:5], columns=["Price", "Quantity"])
                elif prices.get("top_yes_bid") is not None:
                    st.write(f"Depth unavailable. Top Bid: {prices['top_yes_bid']}")
                else:
                    st.write("No bids available.")
            with dc2:
                st.write("**NO Bids**")
                no_bids = ob.get("no_bids", [])
                if no_bids:
                    st.dataframe(no_bids[:5], columns=["Price", "Quantity"])
                elif prices.get("top_no_bid") is not None:
                    st.write(f"Depth unavailable. Top Bid: {prices['top_no_bid']}")
                else:
                    st.write("No bids available.")

            st.subheader("Hypothetical Cost Calculator")
            quantity = st.number_input("Contracts Quantity", min_value=1, value=1, step=1)

            costs = calculate_hypothetical_costs(quantity, prices)

            buy_yes_str = f"${costs['buy_yes_cost']:.2f}" if costs.get("buy_yes_cost") is not None else "N/A"
            buy_no_str = f"${costs['buy_no_cost']:.2f}" if costs.get("buy_no_cost") is not None else "N/A"
            sell_yes_str = f"${costs['sell_yes_proceeds']:.2f}" if costs.get("sell_yes_proceeds") is not None else "N/A"
            sell_no_str = f"${costs['sell_no_proceeds']:.2f}" if costs.get("sell_no_proceeds") is not None else "N/A"

            cc1, cc2 = st.columns(2)
            with cc1:
                st.write("**Buy Estimates**")
                st.write(f"Buy YES estimated cost: {buy_yes_str}")
                st.write(f"Buy NO estimated cost: {buy_no_str}")
                st.write("Max loss for buy side = estimated cost")
            with cc2:
                st.write("**Sell Estimates**")
                st.write(f"Sell YES estimated proceeds: {sell_yes_str}")
                st.write(f"Sell NO estimated proceeds: {sell_no_str}")
                st.write(f"Max payout: ${costs['max_payout']:.2f}")

            st.button("Calculate Only", disabled=True, help="Paper calculation only")
    else:
        if status != "EMPTY":
            st.info("No active KXHIGHMIA markets available.")

    st.divider()
    st.subheader("🔍 Raw Artifacts")
    with st.expander("Raw Market Snapshot JSON"):
        st.json(m_data)
    with st.expander("Raw Orderbook Snapshot JSON"):
        st.json(o_data)
    with st.expander("Raw Paper Signal JSON"):
        st.json(s_data)


__all__ = ["render_kalshi_market_console"]

"""Calibration & Learning tab — quality reports, learning summary, manual corrections."""

from __future__ import annotations

import streamlit as st

try:
    from shared.manual_corrections import load_manual_corrections
except ImportError:  # pragma: no cover
    def load_manual_corrections() -> dict:
        return {}


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


__all__ = ["render_calibration_learning"]

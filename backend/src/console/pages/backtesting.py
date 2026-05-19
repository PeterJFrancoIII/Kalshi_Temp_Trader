"""Backtesting tab — Phase 9 historical replay reports."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from console.data_helpers import load_json
from shared.artifact_paths import BACKTEST_REPORTS_DIR


def render_backtesting():
    st.header("🔬 Backtesting & Calibration (Phase 9)")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")

    backtest_dir = BACKTEST_REPORTS_DIR
    latest_report = None
    if backtest_dir.exists():
        reports = list(backtest_dir.glob("backtest_report_*.json"))
        if reports:
            latest_report = max(reports, key=lambda p: p.stat().st_mtime)

    if latest_report:
        report = load_json(latest_report)
        if report:
            st.subheader("Latest Backtest Run")
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            meta_col1.metric("Start Date", report.get("start_date", "N/A"))
            meta_col2.metric("End Date", report.get("end_date", "N/A"))
            meta_col3.metric("Days Simulated", report.get("days_simulated", "N/A"))

            days_with_signal = report.get("days_with_signal", 0)
            days_missing = report.get("days_missing_data", 0)
            st.write(f"**Days With Signal:** {days_with_signal} | **Days Missing Data:** {days_missing}")

            cal_metrics = report.get("calibration_metrics", {})
            if cal_metrics:
                st.subheader("Calibration Metrics")
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                brier = cal_metrics.get("brier_score")
                crps = cal_metrics.get("crps")
                ece = cal_metrics.get("expected_calibration_error")
                log_l = cal_metrics.get("log_loss")
                m_col1.metric("Brier Score", f"{brier:.4f}" if brier is not None else "N/A",
                              help="Lower is better. Perfect = 0.")
                m_col2.metric("CRPS", f"{crps:.4f}" if crps is not None else "N/A",
                              help="Continuous Ranked Probability Score. Lower is better.")
                m_col3.metric("ECE", f"{ece:.4f}" if ece is not None else "N/A",
                              help="Expected Calibration Error. Lower is better.")
                m_col4.metric("Log Loss", f"{log_l:.4f}" if log_l is not None else "N/A",
                              help="Lower is better.")

                top_hit = cal_metrics.get("top_bin_hit_rate")
                if top_hit is not None:
                    st.metric("Top-Bin Hit Rate", f"{top_hit:.1%}")

            daily_results = report.get("daily_results", [])
            if daily_results:
                st.subheader("Per-Day Results")
                df_days = pd.DataFrame(daily_results)
                display_cols = [
                    "trade_date", "actual_max_f", "predicted_bin",
                    "model_probability", "brier_score", "result", "simulated_pnl",
                ]
                available = [c for c in display_cols if c in df_days.columns]
                if available:
                    df_show = df_days[available].copy()
                    if "model_probability" in df_show.columns:
                        df_show["model_probability"] = df_show["model_probability"].apply(
                            lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "N/A"
                        )
                    if "brier_score" in df_show.columns:
                        df_show["brier_score"] = df_show["brier_score"].apply(
                            lambda x: f"{x:.4f}" if pd.notnull(x) else "N/A"
                        )
                    st.dataframe(df_show.iloc[::-1], use_container_width=True, hide_index=True)
                else:
                    st.dataframe(df_days.iloc[::-1], use_container_width=True)

            with st.expander("Raw Backtest Report JSON"):
                st.json(report)
        else:
            st.warning(f"Could not parse backtest report: {latest_report.name}")
    else:
        st.info("No backtest report found.")
        st.write("Run a backtest to generate a report:")
        st.code("bash scripts/run_backtest.sh", language="bash")

    st.divider()
    st.subheader("📂 Available Backtest Reports")
    if backtest_dir.exists():
        reports_all = sorted(backtest_dir.glob("backtest_report_*.json"), reverse=True)
        if reports_all:
            for rpt in reports_all[:10]:
                size_kb = rpt.stat().st_size / 1024
                st.write(f"- `{rpt.name}` ({size_kb:.1f} KB)")
        else:
            st.write("No reports found in backtest directory.")
    else:
        st.write(f"Backtest reports directory does not exist yet: `{backtest_dir}`")


__all__ = ["render_backtesting"]

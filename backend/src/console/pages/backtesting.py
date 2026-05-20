"""Backtesting tab — Phase 9 historical replay reports."""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import streamlit as st

from console.data_helpers import load_json
from shared.artifact_paths import BACKTEST_REPORTS_DIR
from shared.timestamp_utils import extract_embedded_timestamp, extract_timestamp_from_filename


def render_backtesting():
    st.header("🔬 Backtesting & Calibration (Phase 9)")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")

    backtest_dir = BACKTEST_REPORTS_DIR
    
    # 1. Collect all candidates (legacy files and run directories) with parsed timestamps
    candidates = []
    if backtest_dir.exists():
        # Legacy files
        for p in backtest_dir.glob("backtest_report_*.json"):
            ts = extract_embedded_timestamp(p)
            if ts:
                candidates.append((ts, p))
            else:
                # Try filename fallback
                ts = extract_timestamp_from_filename(p.name)
                if ts:
                    candidates.append((ts, p))
                    
        # New directories (run_*)
        for d in backtest_dir.iterdir():
            if d.is_dir() and d.name.startswith("run_"):
                manifest_path = d / "replay_manifest.json"
                if manifest_path.exists():
                    ts = extract_embedded_timestamp(manifest_path)
                    if not ts:
                        ts = extract_timestamp_from_filename(d.name)
                    if ts:
                        candidates.append((ts, d))

    latest_path = None
    report = None
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        latest_path = candidates[0][1]

        # Load compiled report
        if latest_path.is_file():
            report = load_json(latest_path)
        else:
            # Compiled from run directory
            manifest = load_json(latest_path / "replay_manifest.json")
            if manifest:
                report = {
                    "start_date": manifest.get("start_date", "N/A"),
                    "end_date": manifest.get("end_date", "N/A"),
                    "generated_at_utc": manifest.get("generated_at_utc"),
                    "days_simulated": manifest.get("summary", {}).get("total_lookups", "N/A"),
                    "days_with_signal": manifest.get("summary", {}).get("resolved", 0),
                    "days_missing_data": manifest.get("summary", {}).get("failed", 0),
                    "calibration_metrics": {},
                    "daily_results": [],
                }
                
                perf_path = latest_path / "performance_summary.json"
                if perf_path.exists():
                    perf = load_json(perf_path)
                    if perf:
                        report["calibration_metrics"] = {
                            "total_settled_trades": perf.get("total_settled_trades", 0),
                            "wins": perf.get("wins", 0),
                            "losses": perf.get("losses", 0),
                            "win_rate": perf.get("win_rate", 0.0),
                            "total_simulated_pnl": perf.get("total_simulated_pnl", 0.0),
                            "average_edge": perf.get("average_edge", 0.0),
                            "average_entry_price": perf.get("average_entry_price", 0.0),
                            "pending_trades": perf.get("pending_trades", 0),
                        }
                        
                settlements_path = latest_path / "settlements.jsonl"
                if settlements_path.exists():
                    daily_results = []
                    try:
                        with open(settlements_path, "r") as f:
                            for line in f:
                                if line.strip():
                                    daily_results.append(json.loads(line))
                    except Exception:
                        pass
                    if daily_results:
                        for res in daily_results:
                            res["actual_max_f"] = res.get("actual_max_temp_f")
                            res["predicted_bin"] = res.get("forecast_bin")
                        report["daily_results"] = daily_results

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
            st.subheader("Calibration & Trading Metrics")
            
            # Check if it has Brier / CRPS (legacy style)
            brier = cal_metrics.get("brier_score")
            if brier is not None:
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                crps = cal_metrics.get("crps")
                ece = cal_metrics.get("expected_calibration_error")
                log_l = cal_metrics.get("log_loss")
                m_col1.metric("Brier Score", f"{brier:.4f}", help="Lower is better. Perfect = 0.")
                m_col2.metric("CRPS", f"{crps:.4f}" if crps is not None else "N/A", help="Continuous Ranked Probability Score. Lower is better.")
                m_col3.metric("ECE", f"{ece:.4f}" if ece is not None else "N/A", help="Expected Calibration Error. Lower is better.")
                m_col4.metric("Log Loss", f"{log_l:.4f}" if log_l is not None else "N/A", help="Lower is better.")
                
                top_hit = cal_metrics.get("top_bin_hit_rate")
                if top_hit is not None:
                    st.metric("Top-Bin Hit Rate", f"{top_hit:.1%}")
            
            # Check if it has new replay metrics (trading style)
            if "total_settled_trades" in cal_metrics:
                t_col1, t_col2, t_col3, t_col4 = st.columns(4)
                t_col1.metric("Total Settled Trades", cal_metrics.get("total_settled_trades", 0))
                t_col2.metric("Win Rate", f"{cal_metrics.get('win_rate', 0.0):.1%}")
                t_col3.metric("Simulated PnL", f"${cal_metrics.get('total_simulated_pnl', 0.0):.2f}")
                t_col4.metric("Pending Trades", cal_metrics.get("pending_trades", 0))

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
                st.dataframe(df_show.iloc[::-1], width="stretch", hide_index=True)
            else:
                st.dataframe(df_days.iloc[::-1], width="stretch")

        with st.expander("Raw Backtest Report JSON"):
            st.json(report)
    else:
        st.info("No backtest report found.")
        st.write("Run a backtest to generate a report:")
        st.code("bash scripts/run_backtest.sh", language="bash")

    st.divider()
    st.subheader("📂 Available Backtest Runs & Reports")
    if backtest_dir.exists():
        runs_all = []
        for rpt in backtest_dir.glob("backtest_report_*.json"):
            ts = extract_embedded_timestamp(rpt) or extract_timestamp_from_filename(rpt.name)
            if ts:
                runs_all.append((ts, rpt.name, f"File ({rpt.stat().st_size / 1024:.1f} KB)"))
        for d in backtest_dir.iterdir():
            if d.is_dir() and d.name.startswith("run_"):
                ts = extract_timestamp_from_filename(d.name)
                if ts:
                    runs_all.append((ts, d.name, "Directory (Run)"))
        
        if runs_all:
            runs_all.sort(key=lambda x: x[0], reverse=True)
            for ts, name, type_str in runs_all[:10]:
                st.write(f"- `{name}` — {type_str} | Date: {ts.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.write("No reports or runs found in backtest directory.")
    else:
        st.write(f"Backtest reports directory does not exist yet: `{backtest_dir}`")


__all__ = ["render_backtesting"]

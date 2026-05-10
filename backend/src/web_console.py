import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import streamlit as st

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data" / "processed"
STATUS_DIR = DATA / "status"
REPORTS_DIR = DATA / "reports"
LOGS_DIR = DATA / "logs"
CAL_DIR = DATA / "aggregate_calibration"
KALSHI_DIR = DATA / "kalshi_market_snapshots"
PAPER_DIR = DATA / "paper_trading"
LEARNING_DIR = DATA / "learning"
NWS_DIR = DATA / "weather_nws"
WEATHER_INGESTION_DIR = DATA / "weather_ingestion"

try:
    from shared.manual_corrections import load_manual_corrections
except ImportError:
    def load_manual_corrections():
        return {}

try:
    from twc_nws_comparison import render_twc_nws_comparison
except ImportError:
    def render_twc_nws_comparison(source_data: Any) -> None:
        st.warning("TWC vs NWS comparison module could not be imported.")
        st.json(source_data)


def latest_file(directory: Path, pattern: str) -> Optional[Path]:
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    return max(files, key=os.path.getmtime) if files else None


def load_json(path: Optional[Path]) -> Any:
    if path and path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_text(path: Optional[Path]) -> Optional[str]:
    if path and path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def forecast_summary(report_path: Optional[Path]) -> dict[str, str]:
    out = {"best_single_number": "Unknown", "top_probability_bin": "Unknown"}
    text = load_text(report_path)
    if not text:
        return out
    high = re.search(r"\*\*(?:Best Single-Number Estimate|Forecast High):\*\*\s*([\d.]+)", text)
    if high:
        out["best_single_number"] = high.group(1)
    section = re.search(r"## Probability Bins(.*?)(?:##|\Z)", text, re.DOTALL)
    if section:
        bins = []
        for label, prob in re.findall(r"\|\s*([^|]+?)\s*\|\s*([\d.]+)%\s*\|", section.group(1)):
            try:
                bins.append((label.strip(), float(prob)))
            except ValueError:
                pass
        if bins:
            bins.sort(key=lambda x: x[1], reverse=True)
            out["top_probability_bin"] = f"{bins[0][0]} ({bins[0][1]}%)"
    return out


def normalize_signal_df(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "forecast_bin": "bin",
        "contract_ticker": "market_ticker",
        "market_implied_probability": "market_probability",
        "action": "paper_action",
        "time_to_close": "time_to_close_minutes",
        "speed_to_roi": "speed_to_roi_score",
    }
    for canonical, alias in aliases.items():
        if canonical not in df.columns and alias in df.columns:
            df[canonical] = df[alias]
    return df


def snapshot_status(data: Any, path: Optional[Path]) -> str:
    if not path or not data:
        return "❌ MISSING"
    text = json.dumps(data, default=str).upper() if isinstance(data, (dict, list)) else str(data).upper()
    if "MISSING_API_KEY" in text:
        return "❌ MISSING API KEY"
    if isinstance(data, dict) and data.get("endpoint_status") == "ERROR":
        return "🔴 ERROR"
    if isinstance(data, dict) and data.get("stale_data"):
        return "⚠️ STALE"
    return "✅ CONNECTED"


def load_available_comparison_sources() -> dict[str, Any]:
    """Exact source-loading logic from pages/4_TWC_vs_NWS_Comparison.py.

    Keep this aligned with the standalone page so the main-console tab renders
    the full TWC vs NWS comparison instead of an empty placeholder.
    """
    latest_status_json = latest_file(STATUS_DIR, "kmia_daily_status_*.json")
    latest_weather_ingestion_json = WEATHER_INGESTION_DIR / "latest_weather_ingestion_status.json"
    latest_nws_json = NWS_DIR / "latest_nws_kmia_snapshot.json"
    if not latest_nws_json.exists():
        latest_nws_json = latest_file(NWS_DIR, "nws_kmia_snapshot_*.json")

    latest_report_json = latest_file(REPORTS_DIR, "*.json")

    sources: dict[str, Any] = {
        "status": load_json(latest_status_json),
        "weather_ingestion": load_json(latest_weather_ingestion_json),
        "nws": load_json(latest_nws_json),
        "latest_report_json": load_json(latest_report_json),
        "source_files": {
            "status": str(latest_status_json) if latest_status_json else None,
            "weather_ingestion": str(latest_weather_ingestion_json) if latest_weather_ingestion_json.exists() else None,
            "nws": str(latest_nws_json) if latest_nws_json else None,
            "latest_report_json": str(latest_report_json) if latest_report_json else None,
        },
    }

    for source_name in ["status", "weather_ingestion", "latest_report_json"]:
        payload = sources.get(source_name)
        if isinstance(payload, dict):
            for key in [
                "twc_nws_comparison",
                "twc_vs_nws_comparison",
                "forecast_comparison",
                "provider_comparison",
                "comparison_rows",
                "twc",
                "twc_forecast",
                "weather_company",
                "weather_company_forecast",
                "nws",
                "nws_forecast",
                "nbm",
                "nbm_forecast",
            ]:
                if key in payload and key not in sources:
                    sources[key] = payload[key]

    return sources


def load_console_state() -> dict[str, Any]:
    latest_status_json = latest_file(STATUS_DIR, "kmia_daily_status_*.json")
    latest_status_md = latest_file(STATUS_DIR, "kmia_daily_status_*.md")
    latest_forecast_md = latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.md") or latest_file(REPORTS_DIR, "kmia_forecast_*.md")
    latest_kalshi_json = KALSHI_DIR / "latest_kalshi_market_snapshot.json"
    latest_log = latest_file(LOGS_DIR, "kmia_daily_workflow_*.log")

    latest_nws_path = NWS_DIR / "latest_nws_kmia_snapshot.json"
    if not latest_nws_path.exists():
        latest_nws_path = latest_file(NWS_DIR, "nws_kmia_snapshot_*.json")
    n_data = load_json(latest_nws_path) if latest_nws_path else {}

    p_data = load_json(PAPER_DIR / "latest_paper_signal.json") or {}
    perf = load_json(PAPER_DIR / "latest_paper_trading_performance.json") or {}
    trades = read_jsonl(PAPER_DIR / "paper_trade_ledger.jsonl")
    settlements = read_jsonl(PAPER_DIR / "paper_trade_settlements.jsonl")
    l_data = load_json(LEARNING_DIR / "latest_learning_summary.json") or {}
    pq_data = load_json(LEARNING_DIR / "latest_prediction_quality_report.json") or {}
    pq_md = load_text(LEARNING_DIR / f"prediction_quality_report_{pq_data.get('trade_date')}.md") if pq_data.get("trade_date") else None
    cal_md = load_text(CAL_DIR / "aggregate_calibration.md")
    cal_json = load_json(CAL_DIR / "aggregate_calibration.json")

    fsum = forecast_summary(latest_forecast_md)
    system_status = "GREEN"
    action_needed = "None. System is working."
    kalshi_status = "MISSING"
    kalshi_last_upd = "N/A"
    if latest_kalshi_json.exists():
        kalshi_last_upd = datetime.fromtimestamp(latest_kalshi_json.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        mkts = load_json(latest_kalshi_json) or {}
        if mkts.get("selected_temperature_markets"):
            kalshi_status = "CONNECTED"
        elif mkts.get("total_markets_returned", 0) > 0:
            system_status = "YELLOW"
            kalshi_status = "CONNECTED (No Miami Markets)"
            action_needed = "Kalshi discovery found general markets, but no matching Miami temperature market."
        else:
            system_status = "YELLOW"
            kalshi_status = "CONNECTED (0 Markets)"
            action_needed = "Kalshi discovery returned 0 results."
    else:
        system_status = "YELLOW"
        action_needed = "Run: bash scripts/update_kalshi_market_data.sh"
    if not latest_status_json or not latest_forecast_md:
        system_status = "YELLOW"
        action_needed = "Review missing status or forecast files."

    best_sig = p_data.get("best_signal") if isinstance(p_data, dict) else None
    next_action = "Check logs" if system_status != "GREEN" else ("Run settlement check" if perf.get("pending_trades", 0) > 0 else "Ready")
    comparison_sources = load_available_comparison_sources()

    return {
        "system_status": system_status,
        "action_needed": action_needed,
        "forecast_val": fsum["best_single_number"],
        "top_bin": fsum["top_probability_bin"],
        "weather_live": "✅ CONNECTED" if comparison_sources.get("weather_ingestion") or latest_status_json else "❌ MISSING",
        "nws_live": snapshot_status(n_data, latest_nws_path),
        "kalshi_status": kalshi_status,
        "kalshi_last_upd": kalshi_last_upd,
        "paper_loop_status": "Active" if p_data else "Missing Data",
        "latest_signal_action": best_sig.get("paper_action", "Unknown") if isinstance(best_sig, dict) else "Unknown",
        "latest_signal_ticker": best_sig.get("market_ticker", "N/A") if isinstance(best_sig, dict) else "N/A",
        "open_paper_trades": len(trades),
        "pending_settlements": perf.get("pending_trades", 0),
        "settled_trades": perf.get("total_settled_trades", 0),
        "sim_pnl": perf.get("total_simulated_pnl", 0),
        "next_action": next_action,
        "latest_status_json": latest_status_json,
        "latest_status_md": latest_status_md,
        "latest_forecast_md": latest_forecast_md,
        "latest_kalshi_json": latest_kalshi_json,
        "latest_log": latest_log,
        "latest_nws_path": latest_nws_path,
        "n_data": n_data,
        "p_data": p_data,
        "perf": perf,
        "trades": trades,
        "settlements": settlements,
        "l_data": l_data,
        "pq_data": pq_data,
        "pq_md": pq_md,
        "cal_json": cal_json,
        "cal_md": cal_md,
        "comparison_sources": comparison_sources,
    }


def render_home(state: dict[str, Any]) -> None:
    st.header("🏠 Operator Home")
    st.error("🚨 DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION")
    cols = st.columns(4)
    cols[0].metric("System", state["system_status"])
    cols[0].caption(state["action_needed"])
    cols[1].metric("Forecast", f"{state['forecast_val']}°F")
    cols[1].caption(f"Top bin: {state['top_bin']}")
    cols[2].metric("NWS Live Data", state["nws_live"])
    if state.get("latest_nws_path"):
        cols[2].caption(state["latest_nws_path"].name)
    cols[3].metric("Kalshi Market", state["kalshi_status"])
    cols[3].caption(f"Updated: {state['kalshi_last_upd']}")
    st.divider()
    pcols = st.columns(4)
    pcols[0].metric("Paper Loop", state["paper_loop_status"])
    pcols[0].caption(f"Best signal: {state['latest_signal_ticker']} ({state['latest_signal_action']})")
    pcols[1].metric("Open Paper Trades", state["open_paper_trades"])
    pcols[1].caption(f"Pending settlements: {state['pending_settlements']}")
    pcols[2].metric("Settled Trades", state["settled_trades"])
    pcols[2].caption(f"Sim PnL: ${state['sim_pnl']:.2f}")
    pcols[3].metric("Next Action", state["next_action"])


def render_active_forecasts(p_data: dict[str, Any]) -> None:
    st.header("📊 Active Kalshi Contract Forecasts")
    st.error("🚨 NO REAL TRADING EXECUTION — DRY-RUN ONLY")
    if not p_data:
        st.warning("No active contract forecasts found.")
        st.code("bash scripts/update_kalshi_market_data.sh\nbash scripts/generate_paper_signal.sh")
        return
    best_sig = p_data.get("best_signal")
    if best_sig:
        st.subheader("🏆 Best Signal")
        st.info(f"**{best_sig.get('market_ticker', 'N/A')}** | Edge: {best_sig.get('edge', 0)*100:+.1f}% | Action: {best_sig.get('paper_action', 'N/A')}")
    signals = p_data.get("signals", [])
    if signals:
        df = normalize_signal_df(pd.DataFrame(signals))
        show = [c for c in ["market_ticker", "market_title", "status", "threshold_f", "model_probability", "market_probability", "edge", "time_to_close_minutes", "speed_to_roi_score", "paper_action"] if c in df.columns]
        st.dataframe(df[show] if show else df, width="stretch", hide_index=True)
    else:
        st.info("No active contract forecasts found in latest signal data.")


def render_paper_trading(state: dict[str, Any]) -> None:
    st.header("📈 Paper Trading Performance")
    st.error("🚨 NO REAL TRADING EXECUTION — DRY-RUN ONLY")
    perf = state["perf"]
    cols = st.columns(4)
    cols[0].metric("Settled Trades", perf.get("total_settled_trades", 0))
    cols[1].metric("Win Rate", f"{perf.get('win_rate', 0):.1%}")
    cols[2].metric("Simulated PnL", f"${perf.get('total_simulated_pnl', 0):.2f}")
    cols[3].metric("Pending Trades", perf.get("pending_trades", 0))
    if state["settlements"]:
        st.subheader("Latest Settlement Results")
        st.dataframe(pd.DataFrame(state["settlements"]).iloc[::-1], width="stretch", hide_index=True)
    st.subheader("Ledger")
    if state["trades"]:
        st.dataframe(pd.DataFrame(state["trades"]).iloc[::-1], width="stretch")
    else:
        st.write("No paper trades recorded yet.")


def render_twc_vs_nws(state: dict[str, Any]) -> None:
    st.header("TWC vs NWS Comparison")
    st.error("DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION")
    comparison_sources = load_available_comparison_sources()
    render_twc_nws_comparison(comparison_sources)
    with st.expander("Loaded comparison source files"):
        st.json(comparison_sources.get("source_files", {}))


def render_learning(state: dict[str, Any]) -> None:
    st.header("🎓 Calibration & Learning")
    st.error("🚨 NO REAL TRADING EXECUTION — DRY-RUN ONLY")
    if state["l_data"]:
        st.subheader("Learning Summary")
        st.json(state["l_data"])
    else:
        st.info("No learning summary found. Run `bash scripts/generate_learning_summary.sh`.")
    if state["pq_data"]:
        st.subheader("Prediction Quality Report")
        st.json(state["pq_data"])
    if state["pq_md"]:
        with st.expander("View Prediction Quality Markdown"):
            st.markdown(state["pq_md"])
    if state["cal_md"]:
        with st.expander("View Aggregate Calibration Markdown"):
            st.markdown(state["cal_md"])
    corrections = load_manual_corrections()
    if corrections:
        with st.expander("Manual Data Corrections"):
            st.json(corrections)


def render_system_health(state: dict[str, Any]) -> None:
    st.header("⚙️ System Health & Raw Data")
    c1, c2 = st.columns(2)
    with c1:
        for label, key in [("Status JSON", "latest_status_json"), ("Status Markdown", "latest_status_md"), ("Forecast Markdown", "latest_forecast_md")]:
            path = state.get(key)
            if path:
                with st.expander(f"View {label}: {path.name}"):
                    if path.suffix == ".json":
                        st.json(load_json(path))
                    else:
                        st.markdown(load_text(path) or "")
    with c2:
        path = state.get("latest_kalshi_json")
        if path and path.exists():
            with st.expander("View Kalshi JSON"):
                st.json(load_json(path))
        st.subheader("Daily Commands")
        st.code("bash scripts/run_kmia_daily_workflow.sh\nbash scripts/generate_paper_signal.sh\nbash scripts/record_paper_trade.sh")
    if state.get("latest_log"):
        with st.expander("View Tail of Latest Log"):
            st.code((load_text(state["latest_log"]) or "")[-5000:], language="text")


def main() -> None:
    st.set_page_config(page_title="KMIA Weather Console", page_icon="🌦️", layout="wide")
    st.title("KMIA Kalshi Weather Console")
    st.error("🚨 DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION")
    state = load_console_state()
    tabs = st.tabs([
        "Operator Home",
        "Active Kalshi Contract Forecasts",
        "Paper Trading Performance",
        "TWC vs NWS Comparison",
        "Calibration & Learning",
        "System Health & Raw Data",
    ])
    with tabs[0]:
        render_home(state)
    with tabs[1]:
        render_active_forecasts(state["p_data"])
    with tabs[2]:
        render_paper_trading(state)
    with tabs[3]:
        render_twc_vs_nws(state)
    with tabs[4]:
        render_learning(state)
    with tabs[5]:
        render_system_health(state)


if __name__ == "__main__":
    main()

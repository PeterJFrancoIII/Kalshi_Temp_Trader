import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import re
from typing import Optional, Tuple

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

# Resolution of Paths
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data" / "processed"
STATUS_DIR = DATA / "status"
REPORTS_DIR = DATA / "reports"
LOGS_DIR = DATA / "logs"
CAL_DIR = DATA / "aggregate_calibration"
KALSHI_DIR = DATA / "kalshi_market_snapshots"
HISTORY_FILE = DATA / "history" / "kmia_daily_history.jsonl"
PAPER_DIR = DATA / "paper_trading"
LEARNING_DIR = DATA / "learning"
NWS_DIR = DATA / "weather_nws"
WEATHER_INGESTION_DIR = DATA / "weather_ingestion"

try:
    from shared.manual_corrections import load_manual_corrections
except ImportError:
    def load_manual_corrections(): return {}

# --- CORE HELPERS ---
def latest_file(directory: Path, pattern: str) -> Optional[Path]:
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def load_latest_json(directory: Path, pattern: str) -> tuple[Optional[dict], Optional[Path]]:
    path = latest_file(directory, pattern)
    if path:
        return load_json(path), path
    return None, None

def load_text(path):
    if path and path.exists():
        with open(path, 'r') as f:
            return f.read()
    return None

def load_json(path):
    if path and path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return None

def normalize_signal_df(df):
    """Normalize aliases for signal dataframes."""
    if "forecast_bin" not in df.columns and "bin" in df.columns:
        df["forecast_bin"] = df["bin"]
    if "contract_ticker" not in df.columns and "market_ticker" in df.columns:
        df["contract_ticker"] = df["market_ticker"]
    if "market_implied_probability" not in df.columns and "market_probability" in df.columns:
        df["market_implied_probability"] = df["market_probability"]
    if "action" not in df.columns and "paper_action" in df.columns:
        df["action"] = df["paper_action"]
    if "time_to_close" not in df.columns and "time_to_close_minutes" in df.columns:
        df["time_to_close"] = df["time_to_close_minutes"]
    if "speed_to_roi" not in df.columns and "speed_to_roi_score" in df.columns:
        df["speed_to_roi"] = df["speed_to_roi_score"]
    return df

def safe_dataframe(df, display_columns, fallback_message="No displayable columns found.", formatters=None):
    """Safely render a DataFrame ignoring missing columns."""
    available_columns = [c for c in display_columns if c in df.columns]
    if available_columns:
        df_display = df[available_columns]
        if formatters:
            valid_formatters = {k: v for k, v in formatters.items() if k in available_columns}
            st.dataframe(df_display.style.format(valid_formatters), use_container_width=True)
        else:
            st.dataframe(df_display, use_container_width=True)
    else:
        st.info(fallback_message)
        st.dataframe(df, use_container_width=True)

def load_latest_forecast_summary(report_path):
    """
    Extracts today's forecast and top bin from the latest markdown report.
    Returns a dict with status keys.
    """
    res = {
        "best_single_number": "Unknown",
        "top_probability_bin": "Unknown",
        "source_file": str(report_path) if report_path else None,
        "warnings": []
    }

    if not report_path:
        return res

    if isinstance(report_path, str):
        if not os.path.isabs(report_path) and "/" not in report_path:
            report_path = REPORTS_DIR / report_path
        else:
            report_path = Path(report_path)

    if not report_path.exists():
        res["warnings"].append(f"Report file not found: {report_path.name}")
        return res
    
    content = load_text(report_path)
    if not content:
        res["warnings"].append(f"Report file empty: {report_path.name}")
        return res
    
    sn_match = re.search(r"\*\*(?:Best Single-Number Estimate|Forecast High):\*\*\s*([\d.]+)", content)
    if sn_match:
        res["best_single_number"] = sn_match.group(1)
        
    bin_section = re.search(r"## Probability Bins(.*?)(?:##|\Z)", content, re.DOTALL)
    if bin_section:
        rows = re.findall(r"\|\s*([^|]+?)\s*\|\s*([\d.]+)%\s*\|", bin_section.group(1))
        bins = []
        for b_label, b_prob in rows:
            try:
                bins.append((b_label.strip(), float(b_prob)))
            except ValueError:
                continue
        
        if bins:
            bins.sort(key=lambda x: x[1], reverse=True)
            res["top_probability_bin"] = f"{bins[0][0]} ({bins[0][1]}%)"
            
    return res

def extract_nws_observation_rows(n_data):
    candidate_paths = [
        ("recent_observations_table",),
        ("observations",),
        ("recent_observations",),
        ("live_observations",),
        ("parsed_observations",),
        ("api_inputs", "recent_observations_table"),
        ("api_inputs", "observations"),
        ("raw", "observations"),
    ]
    if not isinstance(n_data, dict):
        return []
    for path in candidate_paths:
        node = n_data
        for key in path:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                node = None
                break
        if isinstance(node, list) and node and all(isinstance(x, dict) for x in node):
            return node
    return []

def extract_best_signal(p_data: dict) -> Optional[dict]:
    if not isinstance(p_data, dict):
        return None
    best_sig = p_data.get("best_signal")
    if not best_sig and p_data.get("signals"):
        best_sig = p_data["signals"][0]
    return best_sig

def aggregate_warnings(p_data: dict, mkts: dict, n_data: dict, status_data: dict) -> list[str]:
    all_warnings = []
    if p_data and isinstance(p_data, dict) and p_data.get("warnings"):
        all_warnings.extend(p_data["warnings"])
    if mkts and isinstance(mkts, dict) and mkts.get("warnings"):
        all_warnings.extend(mkts["warnings"])
    if n_data and isinstance(n_data, dict) and n_data.get("warnings"):
        all_warnings.extend(n_data["warnings"])
    if status_data and isinstance(status_data, dict) and status_data.get("warnings"):
        all_warnings.extend(status_data["warnings"])
    return all_warnings


def derive_orderbook_prices(orderbook: dict) -> dict:
    """
    Derives YES/NO asks from bids (100 - opposite bid).
    """
    prices = {
        "top_yes_bid": None,
        "top_no_bid": None,
        "derived_yes_ask": None,
        "derived_no_ask": None
    }
    if not isinstance(orderbook, dict):
        return prices
        
    yes_bids = orderbook.get("yes_bids", [])
    no_bids = orderbook.get("no_bids", [])
    
    if yes_bids and len(yes_bids) > 0:
        prices["top_yes_bid"] = yes_bids[0][0]
    if no_bids and len(no_bids) > 0:
        prices["top_no_bid"] = no_bids[0][0]
        
    if prices["top_no_bid"] is not None:
        prices["derived_yes_ask"] = 100 - prices["top_no_bid"]
    if prices["top_yes_bid"] is not None:
        prices["derived_no_ask"] = 100 - prices["top_yes_bid"]
        
    return prices


def calculate_hypothetical_costs(quantity: int, prices: dict) -> dict:
    """
    Calculates costs and proceeds for paper trading.
    """
    results = {
        "buy_yes_cost": None,
        "buy_no_cost": None,
        "sell_yes_proceeds": None,
        "sell_no_proceeds": None,
        "max_payout": quantity * 1.00,
        "max_loss_buy_yes": None,
        "max_loss_buy_no": None
    }
    
    if prices.get("derived_yes_ask") is not None:
        results["buy_yes_cost"] = quantity * prices["derived_yes_ask"] / 100.0
        results["max_loss_buy_yes"] = results["buy_yes_cost"]
    if prices.get("derived_no_ask") is not None:
        results["buy_no_cost"] = quantity * prices["derived_no_ask"] / 100.0
        results["max_loss_buy_no"] = results["buy_no_cost"]
        
    if prices.get("top_yes_bid") is not None:
        results["sell_yes_proceeds"] = quantity * prices["top_yes_bid"] / 100.0
    if prices.get("top_no_bid") is not None:
        results["sell_no_proceeds"] = quantity * prices["top_no_bid"] / 100.0
        
    return results


def extract_market_rows(markets: list, paper_signals: dict, orderbooks: dict) -> list[dict]:
    """
    Aggregates data for the active contracts table.
    """
    rows = []
    if not isinstance(markets, list):
        return rows
        
    signals = paper_signals.get("signals", []) if isinstance(paper_signals, dict) else []
    signal_map = {sig.get("market_ticker"): sig for sig in signals if sig.get("market_ticker")}
    
    obs_dict = orderbooks.get("orderbooks", {}) if isinstance(orderbooks, dict) else {}
    
    for mkt in markets:
        ticker = mkt.get("ticker")
        sig = signal_map.get(ticker, {})
        ob = obs_dict.get(ticker, {})
        
        prices = derive_orderbook_prices(ob)
        
        row = {
            "ticker": ticker,
            "bin": mkt.get("contract_bin") or mkt.get("ticker"),
            "title": mkt.get("title", ""),
            "subtitle": mkt.get("subtitle", ""),
            "yes_bid": prices["top_yes_bid"] if prices["top_yes_bid"] is not None else mkt.get("yes_bid"),
            "yes_ask": prices["derived_yes_ask"] if prices["derived_yes_ask"] is not None else mkt.get("yes_ask"),
            "last_price": mkt.get("last_price"),
            "model_probability": sig.get("model_probability"),
            "market_probability": sig.get("market_probability"),
            "edge": sig.get("edge"),
            "expected_value": sig.get("expected_value"),
            "paper_action": sig.get("paper_action"),
            "warnings": ", ".join(mkt.get("warnings", [])) if mkt.get("warnings") else ""
        }
        rows.append(row)
    return rows


# --- RENDERING HELPERS ---

def render_command_center(app_state, p_data, mkts):
    st.header("🏠 Command Center")
    
    # 2. Top-level mode/status cards
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

    # 3. Weather status cards
    st.subheader("🌦️ Weather Status (NWS KMIA)")
    n_data = app_state.get("n_data", {})
    if n_data:
        wc1, wc2, wc3, wc4 = st.columns(4)
        wc1.metric("Current Temp", f"{n_data.get('current_temp_f', 'N/A')}°F")
        wc2.metric("Observed Max Today", f"{n_data.get('observed_max_so_far_f', 'N/A')}°F")
        wc3.metric("Latest Obs Time", n_data.get("latest_observation_time", "N/A"))
        wc4.metric("Source", n_data.get("observation_source", "N/A"))
        
        if n_data.get("stale_data"):
            st.warning("⚠️ Weather data is stale!")
    else:
        st.warning("No live NWS snapshot found.")

    st.divider()

    # 4. Kalshi market status card
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

    # 5. Best Signal Panel
    st.subheader("🏆 Best Signal")
    best_sig = extract_best_signal(p_data)
        
    if best_sig:
        st.info(f"**{best_sig.get('market_ticker', 'N/A')}** | Action: {best_sig.get('paper_action', 'N/A')}")
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Model Prob", f"{best_sig.get('model_probability', 0)*100:.1f}%")
        sc2.metric("Market Prob", f"{best_sig.get('market_probability', 0)*100:.1f}%")
        sc3.metric("Edge", f"{best_sig.get('edge', 0)*100:+.1f}%")
        sc4.metric("Confidence", best_sig.get("confidence", "N/A").upper())
        
        with st.expander("Signal Details", expanded=True):
            st.write(f"**Contract:** {best_sig.get('market_title', 'N/A')}")
            st.write(f"**Status:** {best_sig.get('status', 'N/A')}")
            st.write(f"**Expected Value:** {best_sig.get('expected_value', 'N/A')}")
            st.write(f"**Yes Bid:** {best_sig.get('yes_bid', 'N/A')} | **Yes Ask:** {best_sig.get('yes_ask', 'N/A')}")
            st.write(f"**Last Price:** {best_sig.get('last_price', 'N/A')}")
            if best_sig.get("warnings"):
                st.warning(" | ".join(best_sig["warnings"]))
    else:
        st.error("### NO SIGNAL")
        if p_data.get("warnings"):
            st.warning(" | ".join(p_data["warnings"]))

    st.divider()

    # 6. Warnings / no-trade reasons section
    st.subheader("⚠️ Operator Attention")
    status_data = load_json(app_state.get("latest_status_json"))
    all_warnings = aggregate_warnings(p_data, mkts, n_data, status_data)
        
    if all_warnings:
        for w in all_warnings:
            st.warning(w)
    else:
        st.success("No critical warnings detected.")

    st.divider()

    # 8. Action Commands
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

    # 7. Raw Data Expanders
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


def render_kalshi_market_console(m_data, o_data, s_data):
    st.header("🏪 Kalshi Market Console")
    st.warning("🚨 **DRY-RUN / PAPER ONLY — NO REAL TRADING EXECUTION**")
    
    # 3. Market status summary
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
        
    # 4. Active contract table
    rows = extract_market_rows(markets, s_data, o_data)
    if rows:
        st.subheader("Active Contracts")
        st.dataframe(rows)
        
        # 5. Selected contract control
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
            
            # 6. Orderbook depth
            st.subheader("Orderbook Depth")
            dc1, dc2 = st.columns(2)
            with dc1:
                st.write("**YES Bids**")
                yes_bids = ob.get("yes_bids", [])
                if yes_bids:
                    st.dataframe(yes_bids[:5], columns=["Price", "Quantity"])
                else:
                    st.write("No bids available.")
            with dc2:
                st.write("**NO Bids**")
                no_bids = ob.get("no_bids", [])
                if no_bids:
                    st.dataframe(no_bids[:5], columns=["Price", "Quantity"])
                else:
                    st.write("No bids available.")
                    
            # 7. Hypothetical cost calculator
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
                st.write(f"Max loss for buy side = estimated cost")
            with cc2:
                st.write("**Sell Estimates**")
                st.write(f"Sell YES estimated proceeds: {sell_yes_str}")
                st.write(f"Sell NO estimated proceeds: {sell_no_str}")
                st.write(f"Max payout: ${costs['max_payout']:.2f}")
                
            st.button("Calculate Only", disabled=True, help="Paper calculation only")
    else:
        if status != "EMPTY":
            st.info("No active KXHIGHMIA markets available.")
            
    # 9. Raw artifacts
    st.divider()
    st.subheader("🔍 Raw Artifacts")
    with st.expander("Raw Market Snapshot JSON"):
        st.json(m_data)
    with st.expander("Raw Orderbook Snapshot JSON"):
        st.json(o_data)
    with st.expander("Raw Paper Signal JSON"):
        st.json(s_data)


def render_active_forecasts(p_data):
    st.header("📊 Active Kalshi Contract Forecasts")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
    
    if p_data:
        best_sig = p_data.get("best_signal")
        if best_sig:
            st.subheader("🏆 Best Signal")
            st.info(f"**{best_sig.get('market_ticker', 'N/A')}** | Edge: {best_sig.get('edge', 0)*100:+.1f}% | Action: {best_sig.get('paper_action', 'N/A')}")
            bs_c1, bs_c2, bs_c3, bs_c4 = st.columns(4)
            bs_c1.metric("Model Prob", f"{best_sig.get('model_probability', 0)*100:.1f}%")
            bs_c2.metric("Market Prob", f"{best_sig.get('market_probability', 0)*100:.1f}%")
            bs_c3.metric("Edge", f"{best_sig.get('edge', 0)*100:+.1f}%")
            bs_c4.metric("Confidence", best_sig.get("confidence", "N/A").upper())

        st.divider()
        signals = p_data.get("signals", [])
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
                "edge": "Edge",
                "time_to_close_minutes": "Time to Close",
                "speed_to_roi_score": "Speed-to-ROI",
                "paper_action": "Paper Action"
            }
            df_display_sig = df_sig.copy()
            if "model_probability" in df_display_sig.columns:
                df_display_sig["model_probability"] = df_display_sig["model_probability"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "N/A")
            if "market_probability" in df_display_sig.columns:
                df_display_sig["market_probability"] = df_display_sig["market_probability"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "N/A")
            if "edge" in df_display_sig.columns:
                df_display_sig["edge"] = df_display_sig["edge"].apply(lambda x: f"{x*100:+.1f}%" if pd.notnull(x) else "N/A")
            if "time_to_close_minutes" in df_display_sig.columns:
                df_display_sig["time_to_close_minutes"] = df_display_sig["time_to_close_minutes"].apply(lambda x: f"{x:.1f}m" if pd.notnull(x) else "N/A")
            
            existing_cols_sig = [c for c in col_map_sig.keys() if c in df_display_sig.columns]
            df_final = df_display_sig[existing_cols_sig].rename(columns=col_map_sig)
            st.dataframe(df_final, use_container_width=True, hide_index=True)
        else:
            st.info("No active contract forecasts found in latest signal data.")
    else:
        st.warning("No active contract forecasts found. Run:")
        st.code("bash scripts/update_kalshi_market_data.sh\nbash scripts/generate_paper_signal.sh")


def render_paper_trading(perf, settlements, trades):
    st.header("📈 Paper Trading Performance")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
    
    if perf:
        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        p_col1.metric("Settled Trades", perf.get("total_settled_trades", 0))
        p_col2.metric("Win Rate", f"{perf.get('win_rate', 0):.1%}")
        p_col3.metric("Simulated PnL", f"${perf.get('total_simulated_pnl', 0):.2f}")
        p_col4.metric("Pending Trades", perf.get("pending_trades", 0))
    else:
        st.info("No performance data available. Run `bash scripts/settle_paper_trades.sh`.")

    if settlements:
        st.subheader("Latest Settlement Results")
        df_settle = pd.DataFrame(settlements)
        s_cols = ["trade_date", "market_ticker", "actual_max_temp_f", "actual_bin", "result", "simulated_pnl"]
        existing_s_cols = [c for c in s_cols if c in df_settle.columns]
        st.dataframe(df_settle[existing_s_cols].iloc[::-1], use_container_width=True, hide_index=True)

    st.divider()
    st.header("Ledger")
    st.metric("Open Paper Trades", len(trades))
    if trades:
        df_trades = pd.DataFrame(trades)
        st.dataframe(df_trades.iloc[::-1])
    else:
        st.write("No paper trades recorded yet.")


def render_weather_nws(w_data, n_data):
    st.header("🌦️ Weather / NWS Live Data")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")
    
    if n_data:
        status_text = "🟢 CONNECTED"
        if n_data.get("stale_data"):
            status_text = "🟡 STALE"
        if n_data.get("endpoint_status") == "ERROR":
            status_text = "🔴 ERROR"
            
        st.subheader(f"NWS Status: {status_text}")
        
        nc1, nc2, nc3, nc4 = st.columns(4)
        nc1.metric("Current Temp", f"{n_data.get('current_temp_f', 'N/A')}°F")
        nc2.metric("Observed Max Today", f"{n_data.get('observed_max_so_far_f', 'N/A')}°F")
        nc3.metric("Wind", f"{n_data.get('wind_direction_compass', 'N/A')} {n_data.get('wind_speed_mph', 'N/A')} mph")
        nc4.metric("Stale Data", "Yes" if n_data.get("stale_data") else "No")
        
        st.write(f"**Latest Observation Time:** {n_data.get('latest_observation_time', 'N/A')} (UTC)")
        if n_data.get("wind_gust_mph"):
            st.write(f"**Recent Gust:** {n_data.get('wind_gust_mph')} mph")
        if n_data.get("clouds_x100ft"):
            st.write(f"**Clouds:** {n_data.get('clouds_x100ft')}")
        
        st.subheader("Recent Observations (KMIA)")
        obs_rows = extract_nws_observation_rows(n_data)
        if obs_rows:
            df_obs = pd.DataFrame(obs_rows)
            display_columns = [
                "time_et",
                "temperature_f",
                "dewpoint_f",
                "relative_humidity_pct",
                "wind_direction_compass",
                "wind_direction_degrees",
                "wind_speed_mph",
                "wind_gust_mph",
                "sea_level_pressure_mb",
                "barometric_pressure_mb",
                "precipitation_last_hour_in",
                "clouds_x100ft",
            ]
            available_columns = [c for c in display_columns if c in df_obs.columns]
            st.dataframe(df_obs[available_columns] if available_columns else df_obs, use_container_width=True, hide_index=True)
        else:
            st.warning("NWS snapshot loaded, but no parsed observation rows were found.")
            if isinstance(n_data, dict):
                st.caption("Available NWS snapshot keys: " + ", ".join(n_data.keys()))
        
        if n_data.get("warnings"):
            st.warning(" | ".join(n_data.get("warnings")))
            
        with st.expander("Links & Raw JSON"):
            st.write(f"- [NWS Time Series (KMIA)]({n_data.get('timeseries_source_url')})")
            st.write(f"- [API Observations URL]({n_data.get('api_observations_url')})")
            st.json(n_data)
    else:
        st.info("No live NWS snapshot found. Run `bash scripts/update_nws_live_data.sh`.")

    if w_data:
        st.subheader("Daily Weather Ingestion Status")
        with st.expander("View Daily Weather Status JSON"):
            st.json(w_data)


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


def render_system_health(app_state):
    st.header("⚙️ System Health & Raw Data")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Latest System Status")
        if app_state["latest_status_json"]:
            with st.expander("View Status JSON"):
                st.json(load_json(app_state["latest_status_json"]))
        if app_state["latest_status_md"]:
            with st.expander("View Status MD"):
                st.markdown(load_text(app_state["latest_status_md"]))
                
        st.subheader("Forecast Report")
        if app_state["latest_forecast_md"]:
            with st.expander("View Forecast MD"):
                st.markdown(load_text(app_state["latest_forecast_md"]))
                
    with col2:
        st.subheader("Kalshi Market Discovery")
        if app_state["latest_kalshi_json"].exists():
            with st.expander("View Kalshi JSON"):
                st.json(load_json(app_state["latest_kalshi_json"]))
                
        st.subheader("Operator Notes & Workflow")
        st.write('''
        ### Daily Commands
        ```bash
        bash scripts/run_kmia_daily_workflow.sh
        bash scripts/generate_paper_signal.sh
        bash scripts/record_paper_trade.sh
        ```
        ''')

    st.divider()
    st.subheader("Latest Workflow Logs")
    if app_state["latest_log"]:
        with st.expander("View Tail of Latest Log"):
            st.code(load_text(app_state["latest_log"])[-5000:], language="text")

    st.divider()
    st.subheader("Discovered Processed Files")
    file_info = []
    for d in [STATUS_DIR, REPORTS_DIR, LOGS_DIR, CAL_DIR, KALSHI_DIR, PAPER_DIR]:
        if d.exists():
            for f in d.glob("*"):
                if f.is_file():
                    file_info.append({"Dir": d.name, "File": f.name, "Size": f.stat().st_size})
    if file_info:
        st.table(pd.DataFrame(file_info))


# --- MAIN ---
if __name__ == "__main__":
    st.set_page_config(
        page_title="KMIA Weather Console",
        page_icon="🌦️",
        layout="wide"
    )

    st.title("KMIA Kalshi Weather Console")
    st.error("🚨 **DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION**")

    # --- DATA LOADING (Centralized) ---
    latest_status_json = latest_file(STATUS_DIR, "kmia_daily_status_*.json")
    latest_status_md = latest_file(STATUS_DIR, "kmia_daily_status_*.md")
    
    latest_forecast_md = latest_file(REPORTS_DIR, "kmia_forecast_*rules_v2_climatology*.md")
    if not latest_forecast_md:
        latest_forecast_md = latest_file(REPORTS_DIR, "kmia_forecast_*.md")

    latest_kalshi_json = KALSHI_DIR / "latest_kalshi_market_snapshot.json"
    latest_log = latest_file(LOGS_DIR, "kmia_daily_workflow_*.log")
    
    agg_cal_json_path = CAL_DIR / "aggregate_calibration.json"
    agg_cal_md_path = CAL_DIR / "aggregate_calibration.md"
    cal_json = load_json(agg_cal_json_path) if agg_cal_json_path.exists() else None
    cal_md = load_text(agg_cal_md_path) if agg_cal_md_path.exists() else None

    # Weather
    latest_weather_json = WEATHER_INGESTION_DIR / "latest_weather_ingestion_status.json"
    w_data_status, w_path = load_latest_json(STATUS_DIR, "kmia_daily_status_*.json")
    w_data_ingest = load_json(latest_weather_json) if latest_weather_json.exists() else None
    w_data = w_data_ingest or w_data_status # Combine or use what's available
    
    # NWS
    latest_nws_path = NWS_DIR / "latest_nws_kmia_snapshot.json"
    if not latest_nws_path.exists():
        latest_nws_path = latest_file(NWS_DIR, "nws_kmia_snapshot_*.json")
    n_data = load_json(latest_nws_path) if latest_nws_path else {}

    # Paper Trading
    latest_paper_json = PAPER_DIR / "latest_paper_signal.json"
    p_data = load_json(latest_paper_json) if latest_paper_json.exists() else {}
    
    latest_orderbooks_json = KALSHI_DIR / "latest_kalshi_orderbooks.json"
    o_data = load_json(latest_orderbooks_json) if latest_orderbooks_json.exists() else {}
    
    PERF_FILE = PAPER_DIR / "latest_paper_trading_performance.json"
    perf = load_json(PERF_FILE) if PERF_FILE.exists() else {}
    
    LEDGER_FILE = PAPER_DIR / "paper_trade_ledger.jsonl"
    trades = []
    open_paper_trades = 0
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        trades.append(json.loads(line))
                        open_paper_trades += 1
                    except:
                        continue

    SETTLE_FILE = PAPER_DIR / "paper_trade_settlements.jsonl"
    settlements = []
    if SETTLE_FILE.exists():
        with open(SETTLE_FILE, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        settlements.append(json.loads(line))
                    except:
                        continue

    # Learning & Prediction Quality
    latest_learning_json = LEARNING_DIR / "latest_learning_summary.json"
    l_data = load_json(latest_learning_json) if latest_learning_json.exists() else {}
    
    pq_json = LEARNING_DIR / "latest_prediction_quality_report.json"
    pq_data = load_json(pq_json) if pq_json.exists() else {}
    pq_md = None
    if pq_data and pq_data.get("trade_date"):
        md_path = LEARNING_DIR / f"prediction_quality_report_{pq_data['trade_date']}.md"
        pq_md = load_text(md_path)

    # --- STATE DERIVATION ---
    app_state = {
        "system_status": "GREEN",
        "action_needed": "None. System is working.",
        "forecast_val": "Unknown",
        "top_bin": "Unknown",
        "weather_live": "✅ CONNECTED" if w_path else "❌ MISSING",
        "w_path": w_path,
        "nws_live": "❌ MISSING",
        "latest_nws_path": latest_nws_path,
        "n_data": n_data,
        "kalshi_status": "MISSING",
        "kalshi_last_upd": "N/A",
        "paper_loop_status": "Active" if p_data else "Missing Data",
        "latest_signal_action": "Unknown",
        "open_paper_trades": open_paper_trades,
        "pending_settlements": perf.get("pending_trades", 0),
        "settled_trades": perf.get("total_settled_trades", 0),
        "sim_pnl": perf.get("total_simulated_pnl", 0),
        "next_action": "Ready",
        "latest_status_json": latest_status_json,
        "latest_status_md": latest_status_md,
        "latest_forecast_md": latest_forecast_md,
        "latest_kalshi_json": latest_kalshi_json,
        "latest_log": latest_log
    }

    # NWS live status
    if n_data:
        is_stale = n_data.get("stale_data", False)
        is_error = n_data.get("endpoint_status") == "ERROR"
        has_temp = n_data.get("current_temp_f") is not None
        if not is_stale or not is_error or has_temp:
            app_state["nws_live"] = "✅ CONNECTED"
        else:
            app_state["nws_live"] = "⚠️ STALE"

    # Kalshi status
    mkts = {}
    if latest_kalshi_json.exists():
        app_state["kalshi_last_upd"] = datetime.fromtimestamp(latest_kalshi_json.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        mkts = load_json(latest_kalshi_json)
        if mkts.get("selected_temperature_markets"):
            app_state["kalshi_status"] = "CONNECTED"
        elif mkts.get("total_markets_returned", 0) > 0:
            app_state["system_status"] = "YELLOW"
            app_state["kalshi_status"] = "CONNECTED (No Miami Markets)"
            app_state["action_needed"] = "Kalshi discovery found general markets, but no matching Miami temperature market."
        else:
            app_state["system_status"] = "YELLOW"
            app_state["kalshi_status"] = "CONNECTED (0 Markets)"
            app_state["action_needed"] = "Kalshi discovery returned 0 results."
    else:
        app_state["system_status"] = "YELLOW"
        app_state["action_needed"] = "Run: bash scripts/update_kalshi_market_data.sh"

    # Evaluate System Health combined
    if not latest_status_json or not latest_forecast_md or (w_data_status and w_data_status.get("is_stale")) or (n_data and n_data.get("stale_data")):
        app_state["system_status"] = "YELLOW"
        app_state["action_needed"] = "Review missing files or stale weather data."

    # Forecast extraction
    status_data = load_json(latest_status_json) if latest_status_json else None
    if isinstance(status_data, dict):
        forecast_info = status_data.get("forecast", {})
        if not forecast_info:
            f_dict = status_data.get("forecasts", {})
            if isinstance(f_dict, dict):
                forecast_info = f_dict.get("rules_v2_climatology") or (next(iter(f_dict.values())) if f_dict else {})
                
        if forecast_info:
            if isinstance(forecast_info, str):
                summary = load_latest_forecast_summary(forecast_info)
                app_state["forecast_val"] = summary.get("best_single_number", "Unknown")
                app_state["top_bin"] = summary.get("top_probability_bin", "Unknown")
            elif isinstance(forecast_info, dict):
                app_state["forecast_val"] = str(forecast_info.get("best_single_number", "Unknown"))
                app_state["top_bin"] = forecast_info.get("top_probability_bin", "Unknown")
    
    if app_state["forecast_val"] == "Unknown" or app_state["top_bin"] == "Unknown":
        summary = load_latest_forecast_summary(latest_forecast_md)
        app_state["forecast_val"] = summary.get("best_single_number", "Unknown")
        app_state["top_bin"] = summary.get("top_probability_bin", "Unknown")

    # Paper signal latest action
    best_sig = p_data.get("best_signal")
    if isinstance(best_sig, dict):
        app_state["latest_signal_action"] = best_sig.get("paper_action", "Unknown")
        app_state["latest_signal_ticker"] = best_sig.get("market_ticker", "Unknown")

    # Next action logic
    if app_state["system_status"] != "GREEN":
        app_state["next_action"] = "Check logs"
    elif app_state["pending_settlements"] > 0:
        app_state["next_action"] = "Wait for official KMIA settlement"
    elif app_state["open_paper_trades"] == 0:
        app_state["next_action"] = "Wait for next signal"
    else:
        app_state["next_action"] = "Wait for official KMIA settlement"

    # --- SIDEBAR ---
    st.sidebar.header("System Overview")
    st.sidebar.metric("Station", "KMIA")
    st.sidebar.metric("Mode", "Paper Evaluation")

    if latest_status_json:
        st.sidebar.success("✅ Status File Found")
    else:
        st.sidebar.error("❌ Status File Missing")

    if latest_forecast_md:
        st.sidebar.success("✅ Forecast File Found")
    else:
        st.sidebar.error("❌ Forecast File Missing")

    st.sidebar.divider()
    st.sidebar.info(f"**Project Root:** `{ROOT}`")
    st.sidebar.info(f"**Last Dashboard Refresh:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- MAIN TABS ---
    tabs = st.tabs([
        "Command Center", 
        "Kalshi Market Console",
        "Active Kalshi Forecasts", 
        "Paper Trading", 
        "Weather / NWS", 
        "Calibration / Learning", 
        "System Health"
    ])
    
    with tabs[0]:
        render_command_center(app_state, p_data, mkts)
        
    with tabs[1]:
        render_kalshi_market_console(mkts, o_data, p_data)
        
    with tabs[2]:
        render_active_forecasts(p_data)
        
    with tabs[3]:
        render_paper_trading(perf, settlements, trades)
        
    with tabs[4]:
        render_weather_nws(w_data, n_data)
        
    with tabs[5]:
        render_calibration_learning(pq_data, pq_md, l_data, cal_json, cal_md)
        
    with tabs[6]:
        render_system_health(app_state)

"""Pure helpers used by the Streamlit web console.

This module is shared by every page in :mod:`console.pages` and by the
top-level :mod:`web_console` entry point. The helpers fall into three
buckets:

1. File / JSON access (``latest_file``, ``load_json``, ``load_text``,
   ``load_latest_json``).
2. Display formatters (``format_probability``, ``pretty_format_bin``,
   ``format_num``, ``format_temp``, ``format_pnl``).
3. Domain extractors (``extract_bin_from_market``,
   ``extract_nws_observation_rows``, ``extract_best_signal``,
   ``aggregate_warnings``, ``derive_orderbook_prices``,
   ``calculate_hypothetical_costs``, ``extract_market_rows``,
   ``load_forecast_data``, ``load_latest_forecast_summary``,
   ``normalize_signal_df``, ``is_signal_stale_or_mismatched``).

Only :func:`safe_dataframe` performs Streamlit I/O. The rest are
side-effect free and unit-testable in isolation.

NO REAL TRADING EXECUTION.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from shared.artifact_paths import REPORTS_DIR
from shared.timestamp_utils import parse_ticker_date, extract_embedded_timestamp, extract_timestamp_from_filename


# --- File / JSON ----------------------------------------------------------

def latest_file(directory: Path, pattern: str) -> Optional[Path]:
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    if not files:
        return None

    candidates = []
    for f in files:
        ts = None
        if f.suffix.lower() == '.json':
            ts = extract_embedded_timestamp(f)
        if ts is None:
            ts = extract_timestamp_from_filename(f.name)
        if ts is not None:
            candidates.append((ts, f))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]

    return None


def load_text(path):
    if path and path.exists():
        with open(path, 'r') as f:
            return f.read()
    return None


def load_json(path):
    if path:
        path = Path(path)
        if path.suffix.lower() != '.json':
            return None
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, ValueError, OSError):
                return None
    return None


def load_latest_json(directory: Path, pattern: str) -> tuple[Optional[dict], Optional[Path]]:
    path = latest_file(directory, pattern)
    if path:
        return load_json(path), path
    return None, None


# --- Formatters -----------------------------------------------------------

def format_probability(value, show_plus=False):
    if value is None:
        return "—"
    try:
        prefix = "+" if show_plus and float(value) > 0 else ""
        return f"{prefix}{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def extract_bin_from_market(mkt: dict) -> Optional[str]:
    """Extracts a standardized forecast-style bin label from market metadata."""
    if not isinstance(mkt, dict):
        return None
    strike_type = mkt.get("strike_type")
    floor = mkt.get("floor_strike")
    cap = mkt.get("cap_strike")

    if strike_type == "greater":
        return f">={int(floor) + 1}" if floor is not None else None
    elif strike_type == "less":
        return f"<={int(cap) - 1}" if cap is not None else None
    elif floor is not None and cap is not None:
        return f"{int(floor)}-{int(cap)}"
    return None


def pretty_format_bin(label: str) -> str:
    """Pretty-prints bin labels for UI display."""
    if not label or label == "unknown":
        return label

    res = label.replace(">=", "≥").replace("<=", "≤")
    if any(c.isdigit() for c in res):
        if "°F" not in res:
            res += "°F"
    return res


def format_num(val, unit=""):
    """Formats a number to 1 decimal place with an optional unit."""
    if val is None or val == "N/A" or val == "":
        return "—"
    try:
        res = f"{float(val):.1f}"
        if unit:
            if unit == "%":
                res += unit
            else:
                res += f" {unit}"
        return res
    except (ValueError, TypeError):
        return str(val)


def format_temp(val):
    """Formats a temperature to 1 decimal place with °F."""
    if val is None or val == "N/A" or val == "":
        return "—"
    try:
        return f"{float(val):.1f}°F"
    except (ValueError, TypeError):
        return str(val)


def format_pnl(val):
    """Formats PnL with $ and +/- prefix, using em-dash for None."""
    if val is None or val == "N/A" or val == "" or pd.isna(val):
        return "—"
    try:
        val_f = float(val)
        if val_f > 0:
            return f"+${val_f:.2f}"
        elif val_f < 0:
            return f"-${abs(val_f):.2f}"
        else:
            return "$0.00"
    except (ValueError, TypeError):
        return str(val)


# --- Domain extractors ----------------------------------------------------

def load_forecast_data(forecast_filename):
    if not forecast_filename:
        return None
    path = REPORTS_DIR / forecast_filename
    if path.exists():
        return load_json(path)
    if os.path.isabs(forecast_filename) and os.path.exists(forecast_filename):
        return load_json(Path(forecast_filename))
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
    """Safely render a DataFrame ignoring missing columns and using scalar formatting."""
    available_columns = [c for c in display_columns if c in df.columns]
    if available_columns:
        df_display = df[available_columns].copy()
        if formatters:
            for col, fmt in formatters.items():
                if col in df_display.columns:
                    if callable(fmt):
                        df_display[col] = df_display[col].apply(fmt)
                    else:
                        df_display[col] = df_display[col].apply(
                            lambda x: fmt.format(x) if x is not None and not pd.isna(x) else "—"
                        )
        st.dataframe(df_display, width="stretch", hide_index=True)
    else:
        st.info(fallback_message)
        st.dataframe(df, width="stretch", hide_index=True)


def load_latest_forecast_summary(report_path):
    """Extracts today's forecast and top bin from the latest markdown report."""
    res = {
        "best_single_number": "Unknown",
        "top_probability_bin": "Unknown",
        "source_file": str(report_path) if report_path else None,
        "warnings": [],
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
    """Derives YES/NO asks from bids (100 - opposite bid)."""
    prices = {
        "top_yes_bid": None,
        "top_no_bid": None,
        "derived_yes_ask": None,
        "derived_no_ask": None,
    }
    if not isinstance(orderbook, dict):
        return prices

    yes_bids = orderbook.get("yes_bids", [])
    no_bids = orderbook.get("no_bids", [])

    if yes_bids and len(yes_bids) > 0:
        prices["top_yes_bid"] = yes_bids[0][0]
    else:
        val = orderbook.get("top_yes_bid_dollars")
        if val is not None:
            prices["top_yes_bid"] = int(val * 100)

    if no_bids and len(no_bids) > 0:
        prices["top_no_bid"] = no_bids[0][0]
    else:
        val = orderbook.get("top_no_bid_dollars")
        if val is not None:
            prices["top_no_bid"] = int(val * 100)

    if no_bids and len(no_bids) > 0:
        prices["derived_yes_ask"] = 100 - no_bids[0][0]
    elif orderbook.get("top_yes_ask_dollars") is not None:
        prices["derived_yes_ask"] = int(orderbook.get("top_yes_ask_dollars") * 100)
    elif prices["top_no_bid"] is not None:
        prices["derived_yes_ask"] = 100 - prices["top_no_bid"]

    if yes_bids and len(yes_bids) > 0:
        prices["derived_no_ask"] = 100 - yes_bids[0][0]
    elif orderbook.get("top_no_ask_dollars") is not None:
        prices["derived_no_ask"] = int(orderbook.get("top_no_ask_dollars") * 100)
    elif prices["top_yes_bid"] is not None:
        prices["derived_no_ask"] = 100 - prices["top_yes_bid"]

    return prices


def calculate_hypothetical_costs(quantity: int, prices: dict) -> dict:
    """Calculates costs and proceeds for paper trading."""
    results = {
        "buy_yes_cost": None,
        "buy_no_cost": None,
        "sell_yes_proceeds": None,
        "sell_no_proceeds": None,
        "max_payout": quantity * 1.00,
        "max_loss_buy_yes": None,
        "max_loss_buy_no": None,
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
    """Aggregates data for the active contracts table."""
    rows = []
    if not isinstance(markets, list):
        return rows

    signals = paper_signals.get("signals", []) if isinstance(paper_signals, dict) else []
    signal_map = {sig.get("market_ticker"): sig for sig in signals if sig.get("market_ticker")}

    signal_date = None
    forecast_source = paper_signals.get("forecast_source", "") if isinstance(paper_signals, dict) else ""
    if forecast_source:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", forecast_source)
        if date_match:
            signal_date = date_match.group(1)

    obs_dict = orderbooks.get("orderbooks", {}) if isinstance(orderbooks, dict) else {}

    for mkt in markets:
        ticker = mkt.get("ticker", "")
        ticker_date = parse_ticker_date(ticker)
        sig = signal_map.get(ticker, {})
        ob = obs_dict.get(ticker, {})

        prices = derive_orderbook_prices(ob)

        cb_data = mkt.get("contract_bin")
        if isinstance(cb_data, dict):
            bin_label = cb_data.get("label")
        else:
            bin_label = cb_data or extract_bin_from_market(mkt) or ticker

        model_prob = sig.get("model_probability")
        if (
            model_prob is None
            and ticker_date == signal_date
            and paper_signals
            and "dynamic_contract_probabilities" in paper_signals
        ):
            if bin_label in paper_signals["dynamic_contract_probabilities"]:
                model_prob = paper_signals["dynamic_contract_probabilities"][bin_label]

        display_bin = pretty_format_bin(bin_label)

        row = {
            "date": ticker_date,
            "ticker": ticker,
            "bin": display_bin,
            "title": mkt.get("title", ""),
            "yes_bid": prices["top_yes_bid"] if prices["top_yes_bid"] is not None else mkt.get("yes_bid"),
            "yes_ask": prices["derived_yes_ask"] if prices["derived_yes_ask"] is not None else mkt.get("yes_ask"),
            "model_probability": model_prob,
            "market_probability": sig.get("market_probability"),
            "edge": sig.get("edge"),
            "action": sig.get("paper_action", "N/A" if ticker_date == signal_date else "DATE MISMATCH"),
            "stale": mkt.get("stale", False),
        }

        rows.append(row)
    return rows


def is_signal_stale_or_mismatched(p_data, mkts):
    """Checks if the best signal is stale or mismatched with active markets."""
    best_sig = extract_best_signal(p_data)
    active_markets = mkts.get("selected_temperature_markets", []) if mkts else []
    active_tickers = [m.get("ticker") for m in active_markets]

    if len(active_markets) == 0 or (best_sig and best_sig.get("market_ticker") not in active_tickers):
        if best_sig and best_sig.get("paper_action") == "PAPER BUY CANDIDATE":
            return True
    return False


__all__ = [
    "aggregate_warnings",
    "calculate_hypothetical_costs",
    "derive_orderbook_prices",
    "extract_best_signal",
    "extract_bin_from_market",
    "extract_market_rows",
    "extract_nws_observation_rows",
    "format_num",
    "format_pnl",
    "format_probability",
    "format_temp",
    "is_signal_stale_or_mismatched",
    "latest_file",
    "load_forecast_data",
    "load_json",
    "load_latest_forecast_summary",
    "load_latest_json",
    "load_text",
    "normalize_signal_df",
    "pretty_format_bin",
    "safe_dataframe",
]

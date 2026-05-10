"""Streamlit page for configurable TWC vs NWS comparison.

Run with the main console:
    streamlit run backend/src/web_console.py

Streamlit will expose this file as an additional console page.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st

# Streamlit multipage files execute from backend/src/pages. Add backend/src
# explicitly so sibling console modules import reliably on local machines.
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from twc_nws_comparison import render_twc_nws_comparison


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "backend" / "data" / "processed"
STATUS_DIR = DATA / "status"
REPORTS_DIR = DATA / "reports"
NWS_DIR = DATA / "weather_nws"
WEATHER_INGESTION_DIR = DATA / "weather_ingestion"


def latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def load_json(path: Path | None) -> dict[str, Any] | list[Any] | None:
    if not path or not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_available_comparison_sources() -> dict[str, Any]:
    """Load likely local payloads that may contain TWC/NWS comparison rows."""
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

    # Flatten common top-level comparison payloads into a single search space
    # without changing the underlying comparison math.
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


st.set_page_config(
    page_title="TWC vs NWS Comparison",
    page_icon="🌦️",
    layout="wide",
)

st.title("TWC vs NWS Comparison")
st.error("DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION")

comparison_sources = load_available_comparison_sources()
render_twc_nws_comparison(comparison_sources)

with st.expander("Loaded comparison source files"):
    st.json(comparison_sources.get("source_files", {}))

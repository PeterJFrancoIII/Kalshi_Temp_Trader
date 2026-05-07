import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "backend" / "data" / "processed"
NWS_DIR = DATA / "weather_nws"
TWC_DIR = DATA / "weather_company"


def latest_file(directory: Path, pattern: str) -> Optional[Path]:
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def load_json(path: Optional[Path]) -> Dict[str, Any]:
    if path and path.exists():
        with path.open("r") as f:
            return json.load(f)
    return {}


def as_status(value: Any) -> str:
    if not value:
        return "MISSING"
    if isinstance(value, dict) and value.get("endpoint_status") == "ERROR":
        return "ERROR"
    if isinstance(value, dict) and value.get("stale_data"):
        return "STALE"
    if isinstance(value, dict) and value.get("quality_flags"):
        return "CHECK FLAGS"
    return "CONNECTED"


def extract_nws_rows(nws: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("recent_observations_table", "observations", "recent_observations"):
        rows = nws.get(key)
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    return []


def render_summary(nws: Dict[str, Any], twc: Dict[str, Any]) -> None:
    st.header("KMIA Weather Provider Comparison")
    st.error("🚨 NO REAL TRADING EXECUTION — DRY-RUN / PAPER EVALUATION ONLY")
    st.info("NWS KMIA remains the settlement and verification target. TWC is shown as forecast guidance for comparison and future bias/variance analysis.")

    twc_current = twc.get("current_conditions", {}) if isinstance(twc, dict) else {}
    twc_features = twc.get("derived_features", {}) if isinstance(twc, dict) else {}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NWS Current Temp", f"{nws.get('current_temp_f', 'N/A')}°F")
    c2.metric("NWS Max So Far", f"{nws.get('observed_max_so_far_f', 'N/A')}°F")
    c3.metric("TWC Current Temp", f"{twc_current.get('temperature_f', 'N/A')}°F")
    c4.metric("TWC Forecast High", f"{twc_features.get('forecast_high_f', 'N/A')}°F")

    n1, n2, n3, n4 = st.columns(4)
    n1.metric("NWS Status", as_status(nws))
    n2.metric("TWC Status", as_status(twc))
    n3.metric("TWC Hourly Max", f"{twc_features.get('hourly_max_temp_f', 'N/A')}°F")
    n4.metric("TWC Sea-Breeze Signal", twc_features.get("sea_breeze_shift_hour_et") or "N/A")

    nws_forecast = nws.get("forecast_high_f")
    twc_high = twc_features.get("forecast_high_f")
    if isinstance(nws_forecast, (int, float)) and isinstance(twc_high, (int, float)):
        st.metric("TWC - NWS Forecast High Spread", f"{twc_high - nws_forecast:+.1f}°F")


def render_twc_tables(twc: Dict[str, Any]) -> None:
    st.subheader("The Weather Company Snapshot")
    if not twc:
        st.warning("No TWC snapshot found. Run `bash scripts/update_twc_kmia_data.sh`.")
        return

    if twc.get("quality_flags"):
        st.warning("TWC quality flags: " + ", ".join(twc.get("quality_flags", [])))

    daily = twc.get("daily_forecast", [])
    hourly = twc.get("hourly_forecast", [])

    if daily:
        st.markdown("**Daily Forecast**")
        df_daily = pd.DataFrame(daily)
        daily_cols = ["valid_time_utc", "max_temp_f", "min_temp_f", "precip_probability_pct", "narrative"]
        st.dataframe(df_daily[[c for c in daily_cols if c in df_daily.columns]], use_container_width=True, hide_index=True)

    if hourly:
        st.markdown("**Hourly Forecast**")
        df_hourly = pd.DataFrame(hourly)
        hourly_cols = [
            "valid_time_local", "valid_time_utc", "temperature_f", "dewpoint_f",
            "relative_humidity_pct", "wind_direction_degrees", "wind_direction_cardinal",
            "wind_speed_mph", "cloud_cover_pct", "precip_probability_pct", "phrase"
        ]
        st.dataframe(df_hourly[[c for c in hourly_cols if c in df_hourly.columns]], use_container_width=True, hide_index=True)

    with st.expander("TWC endpoint status and raw normalized JSON"):
        st.json({"endpoint_status": twc.get("endpoint_status", {}), "snapshot": twc})


def render_nws_tables(nws: Dict[str, Any]) -> None:
    st.subheader("NWS KMIA Snapshot")
    if not nws:
        st.warning("No NWS snapshot found. Run `bash scripts/update_nws_live_data.sh`.")
        return

    rows = extract_nws_rows(nws)
    if rows:
        df = pd.DataFrame(rows)
        cols = [
            "time_et", "temperature_f", "dewpoint_f", "relative_humidity_pct",
            "wind_direction_compass", "wind_direction_degrees", "wind_speed_mph",
            "wind_gust_mph", "clouds_x100ft", "raw_message"
        ]
        st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)
    else:
        st.info("NWS snapshot loaded, but no parsed recent observation rows were found.")

    with st.expander("NWS raw JSON"):
        st.json(nws)


def main() -> None:
    st.set_page_config(page_title="KMIA NWS vs TWC", page_icon="🌦️", layout="wide")

    latest_nws = NWS_DIR / "latest_nws_kmia_snapshot.json"
    if not latest_nws.exists():
        latest_nws = latest_file(NWS_DIR, "nws_kmia_snapshot_*.json")

    latest_twc = TWC_DIR / "latest_twc_kmia_snapshot.json"
    if not latest_twc.exists():
        latest_twc = latest_file(TWC_DIR, "twc_kmia_snapshot_*.json")

    nws = load_json(latest_nws)
    twc = load_json(latest_twc)

    st.caption(f"NWS source: {latest_nws.name if latest_nws else 'missing'}")
    st.caption(f"TWC source: {latest_twc.name if latest_twc else 'missing'}")

    render_summary(nws, twc)
    st.divider()

    left, right = st.columns(2)
    with left:
        render_nws_tables(nws)
    with right:
        render_twc_tables(twc)

    st.divider()
    st.subheader("Historical variance objective")
    st.write(
        "Next calibration step: join official NWS KMIA daily max settlements to archived "
        "TWC forecast-high snapshots by forecast date and forecast issue horizon, then compute "
        "median(TWC forecast high - NWS KMIA observed max), MAE, and bin-boundary miss rates."
    )


if __name__ == "__main__":
    main()

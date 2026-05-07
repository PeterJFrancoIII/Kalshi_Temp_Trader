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


def provider_status(value: Dict[str, Any], provider: str) -> str:
    if not value:
        return "MISSING"
    if provider == "nws":
        if value.get("endpoint_status") == "ERROR":
            return "ERROR"
        if value.get("stale_data"):
            return "STALE"
        return "CONNECTED"
    if value.get("quality_flags"):
        return "CHECK FLAGS"
    return "CONNECTED"


def extract_nws_rows(nws: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("recent_observations_table", "observations", "recent_observations"):
        rows = nws.get(key)
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    return []


def twc_forecast_spread(nws: Dict[str, Any], twc: Dict[str, Any]) -> Optional[float]:
    twc_high = twc.get("derived_features", {}).get("forecast_high_f")
    nws_high = nws.get("forecast_high_f")
    if isinstance(twc_high, (int, float)) and isinstance(nws_high, (int, float)):
        return float(twc_high) - float(nws_high)
    return None


def render_provider_summary(nws: Dict[str, Any], twc: Dict[str, Any]) -> None:
    twc_current = twc.get("current_conditions", {}) if isinstance(twc, dict) else {}
    twc_features = twc.get("derived_features", {}) if isinstance(twc, dict) else {}
    spread = twc_forecast_spread(nws, twc)

    st.header("🌦️ Weather Providers: NWS KMIA vs The Weather Company")
    st.error("🚨 NO REAL TRADING EXECUTION — DRY-RUN / PAPER EVALUATION ONLY")
    st.info(
        "NWS KMIA remains the official target and settlement reference. "
        "The Weather Company is shown beside NWS as forecast guidance for bias, variance, and sea-breeze analysis."
    )

    row1 = st.columns(4)
    row1[0].metric("NWS Current Temp", f"{nws.get('current_temp_f', 'N/A')}°F")
    row1[1].metric("NWS Max So Far", f"{nws.get('observed_max_so_far_f', 'N/A')}°F")
    row1[2].metric("TWC Current Temp", f"{twc_current.get('temperature_f', 'N/A')}°F")
    row1[3].metric("TWC Forecast High", f"{twc_features.get('forecast_high_f', 'N/A')}°F")

    row2 = st.columns(4)
    row2[0].metric("NWS Status", provider_status(nws, "nws"))
    row2[1].metric("TWC Status", provider_status(twc, "twc"))
    row2[2].metric("TWC Hourly Max", f"{twc_features.get('hourly_max_temp_f', 'N/A')}°F")
    row2[3].metric("TWC - NWS Forecast Spread", f"{spread:+.1f}°F" if spread is not None else "N/A")

    st.caption(f"TWC sea-breeze signal: {twc_features.get('sea_breeze_shift_hour_et') or 'N/A'}")


def render_nws_section(nws: Dict[str, Any]) -> None:
    st.subheader("NWS KMIA Live Station Data")
    if not nws:
        st.warning("No NWS snapshot found. Run `bash scripts/update_nws_live_data.sh`.")
        return

    ncols = st.columns(4)
    ncols[0].metric("Forecast High", f"{nws.get('forecast_high_f', 'N/A')}°F")
    ncols[1].metric("Dewpoint", f"{nws.get('dewpoint_f', 'N/A')}°F")
    ncols[2].metric("Wind", f"{nws.get('wind_direction_compass', 'N/A')} {nws.get('wind_speed_mph', 'N/A')} mph")
    ncols[3].metric("Stale", "Yes" if nws.get("stale_data") else "No")

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


def render_twc_section(twc: Dict[str, Any]) -> None:
    st.subheader("The Weather Company Forecast Guidance")
    if not twc:
        st.warning("No TWC snapshot found. Run `bash scripts/update_twc_kmia_data.sh`.")
        return

    if twc.get("quality_flags"):
        st.warning("TWC quality flags: " + ", ".join(twc.get("quality_flags", [])))

    current = twc.get("current_conditions", {})
    features = twc.get("derived_features", {})
    tcols = st.columns(4)
    tcols[0].metric("Current Temp", f"{current.get('temperature_f', 'N/A')}°F")
    tcols[1].metric("Forecast High", f"{features.get('forecast_high_f', 'N/A')}°F")
    tcols[2].metric("Hourly Max", f"{features.get('hourly_max_temp_f', 'N/A')}°F")
    tcols[3].metric("Max Cloud Cover", f"{features.get('max_cloud_cover_pct', 'N/A')}%")

    daily = twc.get("daily_forecast", [])
    hourly = twc.get("hourly_forecast", [])

    if daily:
        st.markdown("**TWC Daily Forecast**")
        df_daily = pd.DataFrame(daily)
        daily_cols = ["valid_time_utc", "max_temp_f", "min_temp_f", "precip_probability_pct", "narrative"]
        st.dataframe(df_daily[[c for c in daily_cols if c in df_daily.columns]], use_container_width=True, hide_index=True)

    if hourly:
        st.markdown("**TWC Hourly Forecast**")
        df_hourly = pd.DataFrame(hourly)
        hourly_cols = [
            "valid_time_local", "valid_time_utc", "temperature_f", "dewpoint_f",
            "relative_humidity_pct", "wind_direction_degrees", "wind_direction_cardinal",
            "wind_speed_mph", "cloud_cover_pct", "precip_probability_pct", "phrase"
        ]
        st.dataframe(df_hourly[[c for c in hourly_cols if c in df_hourly.columns]], use_container_width=True, hide_index=True)
    else:
        st.info("No TWC hourly forecast rows found. Check the TWC hourly endpoint entitlement/path.")

    with st.expander("TWC endpoint status and raw normalized JSON"):
        st.json({"endpoint_status": twc.get("endpoint_status", {}), "snapshot": twc})


def main() -> None:
    st.set_page_config(page_title="KMIA Weather Providers", page_icon="🌦️", layout="wide")

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

    render_provider_summary(nws, twc)
    st.divider()

    left, right = st.columns(2)
    with left:
        render_nws_section(nws)
    with right:
        render_twc_section(twc)

    st.divider()
    st.subheader("Historical variance objective")
    st.write(
        "Next calibration step: join official NWS KMIA daily max settlements to archived "
        "TWC forecast-high snapshots by forecast date and forecast issue horizon, then compute "
        "median(TWC forecast high - NWS KMIA observed max), MAE, within-1/2/3°F rates, "
        "and Kalshi bin-boundary miss rates."
    )


if __name__ == "__main__":
    main()

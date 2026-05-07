import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def parse_ts(value: Any) -> Optional[pd.Timestamp]:
    if value is None or value == "":
        return None
    try:
        ts = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(ts):
            return None
        return ts
    except Exception:
        return None


def first_number(row: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        val = row.get(key)
        if isinstance(val, (int, float)) and not pd.isna(val):
            return float(val)
    return None


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


def normalize_nws_rows(nws: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for row in extract_nws_rows(nws):
        ts = parse_ts(row.get("timestamp_utc") or row.get("valid_time_utc") or row.get("time_utc"))
        if ts is None and row.get("date_et") and row.get("time_et"):
            ts = parse_ts(f"{row.get('date_et')} {row.get('time_et')}")
        rows.append({
            "provider": "NWS",
            "time_utc": ts,
            "time_label": row.get("time_et") or row.get("timestamp_utc") or row.get("valid_time_utc"),
            "temperature_f": first_number(row, "temperature_f", "current_temp_f"),
            "dewpoint_f": first_number(row, "dewpoint_f"),
            "relative_humidity_pct": first_number(row, "relative_humidity_pct", "humidity"),
            "wind_direction_degrees": first_number(row, "wind_direction_degrees"),
            "wind_direction": row.get("wind_direction_compass") or row.get("wind_direction_cardinal"),
            "wind_speed_mph": first_number(row, "wind_speed_mph"),
            "wind_gust_mph": first_number(row, "wind_gust_mph"),
            "clouds": row.get("clouds_x100ft"),
            "precip_probability_pct": None,
            "source_text": row.get("raw_message") or row.get("text_description"),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["time_utc"]).sort_values("time_utc")
    return df


def normalize_twc_rows(twc: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    hourly = twc.get("hourly_forecast", []) if isinstance(twc, dict) else []
    for row in hourly:
        if not isinstance(row, dict):
            continue
        ts = parse_ts(row.get("valid_time_utc") or row.get("valid_time_local"))
        rows.append({
            "provider": "TWC",
            "time_utc": ts,
            "time_label": row.get("valid_time_local") or row.get("valid_time_utc"),
            "temperature_f": first_number(row, "temperature_f"),
            "dewpoint_f": first_number(row, "dewpoint_f"),
            "relative_humidity_pct": first_number(row, "relative_humidity_pct"),
            "wind_direction_degrees": first_number(row, "wind_direction_degrees"),
            "wind_direction": row.get("wind_direction_cardinal"),
            "wind_speed_mph": first_number(row, "wind_speed_mph"),
            "wind_gust_mph": None,
            "clouds": first_number(row, "cloud_cover_pct"),
            "precip_probability_pct": first_number(row, "precip_probability_pct"),
            "source_text": row.get("phrase"),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["time_utc"]).sort_values("time_utc")
    return df


def add_spreads(row: Dict[str, Any]) -> Dict[str, Any]:
    for metric in [
        "temperature_f",
        "dewpoint_f",
        "relative_humidity_pct",
        "wind_speed_mph",
        "wind_direction_degrees",
        "precip_probability_pct",
    ]:
        n = row.get(f"nws_{metric}")
        t = row.get(f"twc_{metric}")
        row[f"spread_{metric}"] = round(t - n, 2) if isinstance(n, (int, float)) and isinstance(t, (int, float)) else None
    return row


def build_matched_table(nws_df: pd.DataFrame, twc_df: pd.DataFrame, tolerance_minutes: int, match_direction: str) -> pd.DataFrame:
    if nws_df.empty or twc_df.empty:
        return pd.DataFrame()

    tolerance = pd.Timedelta(minutes=tolerance_minutes)
    direction = "nearest"
    if match_direction in ("backward", "forward"):
        direction = match_direction

    nws_sorted = nws_df.sort_values("time_utc")
    twc_sorted = twc_df.sort_values("time_utc")
    merged = pd.merge_asof(
        nws_sorted,
        twc_sorted,
        on="time_utc",
        direction=direction,
        tolerance=tolerance,
        suffixes=("_nws_raw", "_twc_raw"),
    )

    rows = []
    for _, r in merged.iterrows():
        if pd.isna(r.get("provider_twc_raw")):
            continue
        item = {
            "matched_time_utc": r.get("time_utc"),
            "nws_time_label": r.get("time_label_nws_raw"),
            "twc_time_label": r.get("time_label_twc_raw"),
            "nws_temperature_f": r.get("temperature_f_nws_raw"),
            "twc_temperature_f": r.get("temperature_f_twc_raw"),
            "nws_dewpoint_f": r.get("dewpoint_f_nws_raw"),
            "twc_dewpoint_f": r.get("dewpoint_f_twc_raw"),
            "nws_relative_humidity_pct": r.get("relative_humidity_pct_nws_raw"),
            "twc_relative_humidity_pct": r.get("relative_humidity_pct_twc_raw"),
            "nws_wind_direction_degrees": r.get("wind_direction_degrees_nws_raw"),
            "twc_wind_direction_degrees": r.get("wind_direction_degrees_twc_raw"),
            "nws_wind_direction": r.get("wind_direction_nws_raw"),
            "twc_wind_direction": r.get("wind_direction_twc_raw"),
            "nws_wind_speed_mph": r.get("wind_speed_mph_nws_raw"),
            "twc_wind_speed_mph": r.get("wind_speed_mph_twc_raw"),
            "nws_wind_gust_mph": r.get("wind_gust_mph_nws_raw"),
            "nws_clouds": r.get("clouds_nws_raw"),
            "twc_cloud_cover_pct": r.get("clouds_twc_raw"),
            "twc_precip_probability_pct": r.get("precip_probability_pct_twc_raw"),
            "nws_source_text": r.get("source_text_nws_raw"),
            "twc_source_text": r.get("source_text_twc_raw"),
        }
        rows.append(add_spreads(item))
    return pd.DataFrame(rows)


def render_provider_summary(nws: Dict[str, Any], twc: Dict[str, Any], matched: pd.DataFrame) -> None:
    twc_current = twc.get("current_conditions", {}) if isinstance(twc, dict) else {}
    twc_features = twc.get("derived_features", {}) if isinstance(twc, dict) else {}

    st.header("🌦️ Weather Providers: NWS KMIA vs The Weather Company")
    st.error("🚨 NO REAL TRADING EXECUTION — DRY-RUN / PAPER EVALUATION ONLY")
    st.info(
        "NWS KMIA remains the official target and settlement reference. "
        "TWC is shown beside NWS as forecast guidance, with automatic interval matching and spread calculations."
    )

    row1 = st.columns(4)
    row1[0].metric("NWS Current Temp", f"{nws.get('current_temp_f', 'N/A')}°F")
    row1[1].metric("NWS Max So Far", f"{nws.get('observed_max_so_far_f', 'N/A')}°F")
    row1[2].metric("TWC Current Temp", f"{twc_current.get('temperature_f', 'N/A')}°F")
    row1[3].metric("TWC Forecast High", f"{twc_features.get('forecast_high_f', 'N/A')}°F")

    row2 = st.columns(4)
    row2[0].metric("NWS Status", provider_status(nws, "nws"))
    row2[1].metric("TWC Status", provider_status(twc, "twc"))
    row2[2].metric("Matched Intervals", len(matched))
    if not matched.empty and "spread_temperature_f" in matched.columns:
        med = matched["spread_temperature_f"].dropna().median()
        row2[3].metric("Median Temp Spread", f"{med:+.1f}°F" if pd.notna(med) else "N/A")
    else:
        row2[3].metric("Median Temp Spread", "N/A")


def render_controls() -> Tuple[int, str, List[str], bool]:
    st.sidebar.subheader("Weather comparison controls")
    tolerance = st.sidebar.slider("Auto-match tolerance", min_value=5, max_value=180, value=75, step=5, help="Maximum allowed time gap between an NWS row and a TWC row.")
    direction_label = st.sidebar.selectbox(
        "Match method",
        ["nearest", "backward", "forward"],
        index=0,
        help="nearest = closest report time; backward = latest TWC row at/before NWS time; forward = first TWC row at/after NWS time.",
    )
    table_mode = st.sidebar.multiselect(
        "Show table groups",
        ["temperature", "humidity", "wind", "cloud_precip", "source_text"],
        default=["temperature", "humidity", "wind"],
    )
    show_raw = st.sidebar.checkbox("Show raw provider tables", value=False)
    return tolerance, direction_label, table_mode, show_raw


def visible_columns(groups: List[str]) -> List[str]:
    cols = ["matched_time_utc", "nws_time_label", "twc_time_label"]
    if "temperature" in groups:
        cols += ["nws_temperature_f", "twc_temperature_f", "spread_temperature_f"]
    if "humidity" in groups:
        cols += ["nws_dewpoint_f", "twc_dewpoint_f", "spread_dewpoint_f", "nws_relative_humidity_pct", "twc_relative_humidity_pct", "spread_relative_humidity_pct"]
    if "wind" in groups:
        cols += ["nws_wind_direction", "twc_wind_direction", "nws_wind_direction_degrees", "twc_wind_direction_degrees", "spread_wind_direction_degrees", "nws_wind_speed_mph", "twc_wind_speed_mph", "spread_wind_speed_mph", "nws_wind_gust_mph"]
    if "cloud_precip" in groups:
        cols += ["nws_clouds", "twc_cloud_cover_pct", "twc_precip_probability_pct"]
    if "source_text" in groups:
        cols += ["nws_source_text", "twc_source_text"]
    return cols


def render_matched_table(matched: pd.DataFrame, groups: List[str]) -> None:
    st.subheader("Matched NWS vs TWC Intervals")
    if matched.empty:
        st.warning(
            "No matched NWS/TWC intervals found. This usually means TWC hourly data is unavailable, "
            "or the match tolerance is too small for the available report times."
        )
        return
    cols = [c for c in visible_columns(groups) if c in matched.columns]
    view = matched[cols].copy()
    if "matched_time_utc" in view.columns:
        view["matched_time_utc"] = pd.to_datetime(view["matched_time_utc"], utc=True).dt.strftime("%Y-%m-%d %H:%M UTC")
    st.dataframe(view, use_container_width=True, hide_index=True)

    spread_cols = [c for c in matched.columns if c.startswith("spread_")]
    if spread_cols:
        summary = []
        for col in spread_cols:
            vals = matched[col].dropna()
            if vals.empty:
                continue
            summary.append({
                "metric": col.replace("spread_", "TWC_minus_NWS_"),
                "median": vals.median(),
                "mean": vals.mean(),
                "max_abs": vals.abs().max(),
                "count": len(vals),
            })
        if summary:
            st.markdown("**Spread summary**")
            st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)


def render_raw_sections(nws_df: pd.DataFrame, twc_df: pd.DataFrame, nws: Dict[str, Any], twc: Dict[str, Any]) -> None:
    st.subheader("Raw Provider Tables")
    left, right = st.columns(2)
    with left:
        st.markdown("**NWS normalized rows**")
        if nws_df.empty:
            st.info("No NWS normalized rows found.")
        else:
            st.dataframe(nws_df, use_container_width=True, hide_index=True)
        with st.expander("NWS raw JSON"):
            st.json(nws)
    with right:
        st.markdown("**TWC normalized hourly rows**")
        if twc_df.empty:
            st.info("No TWC hourly rows found. Check hourly endpoint entitlement/path.")
        else:
            st.dataframe(twc_df, use_container_width=True, hide_index=True)
        with st.expander("TWC raw JSON"):
            st.json(twc)


def render_daily_twc(twc: Dict[str, Any]) -> None:
    daily = twc.get("daily_forecast", []) if isinstance(twc, dict) else []
    if not daily:
        return
    st.subheader("TWC Daily Forecast")
    df = pd.DataFrame(daily)
    cols = ["valid_time_utc", "max_temp_f", "min_temp_f", "precip_probability_pct", "narrative"]
    st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)


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
    nws_df = normalize_nws_rows(nws)
    twc_df = normalize_twc_rows(twc)

    tolerance, match_direction, groups, show_raw = render_controls()
    matched = build_matched_table(nws_df, twc_df, tolerance, match_direction)

    st.caption(f"NWS source: {latest_nws.name if latest_nws else 'missing'}")
    st.caption(f"TWC source: {latest_twc.name if latest_twc else 'missing'}")

    render_provider_summary(nws, twc, matched)
    st.divider()
    render_matched_table(matched, groups)
    st.divider()
    render_daily_twc(twc)

    if show_raw:
        st.divider()
        render_raw_sections(nws_df, twc_df, nws, twc)

    st.divider()
    st.subheader("Historical variance objective")
    st.write(
        "Next calibration step: join official NWS KMIA daily max settlements to archived "
        "TWC forecast-high snapshots by forecast date and issue horizon, then compute median "
        "TWC-minus-NWS variance, MAE, within-1/2/3°F rates, and Kalshi bin-boundary miss rates."
    )


if __name__ == "__main__":
    main()

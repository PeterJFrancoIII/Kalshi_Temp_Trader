import json
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

DISPLAY_COLUMNS = [
    "Time ET",
    "Provider",
    "Temp °F",
    "Dewpoint °F",
    "RH %",
    "Wind",
    "Wind mph",
    "Gust mph",
    "Clouds",
    "Precip %",
    "Phrase / Raw",
]


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
        if isinstance(value, (int, float)):
            ts = pd.to_datetime(value, unit="s", utc=True, errors="coerce")
        else:
            ts = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(ts):
            return None
        return ts
    except Exception:
        return None


def format_et(ts: Any) -> str:
    parsed = parse_ts(ts)
    if parsed is None:
        return "N/A"
    return parsed.tz_convert("America/New_York").strftime("%m/%d %I:%M %p")


def first_number(row: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        val = row.get(key)
        if isinstance(val, (int, float)) and not pd.isna(val):
            return float(val)
    return None


def compact_num(value: Any, decimals: int = 0) -> Any:
    if isinstance(value, (int, float)) and not pd.isna(value):
        if decimals == 0:
            return int(round(value))
        return round(float(value), decimals)
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
    for path in [
        ("recent_observations_table",),
        ("observations",),
        ("recent_observations",),
        ("api_inputs", "recent_observations_table"),
        ("api_inputs", "observations"),
        ("raw", "observations"),
    ]:
        node: Any = nws
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, list):
            return [r for r in node if isinstance(r, dict)]
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
            "time_et": format_et(ts) if ts is not None else row.get("time_et", "N/A"),
            "temperature_f": first_number(row, "temperature_f", "current_temp_f"),
            "dewpoint_f": first_number(row, "dewpoint_f"),
            "relative_humidity_pct": first_number(row, "relative_humidity_pct", "humidity"),
            "wind_direction_degrees": first_number(row, "wind_direction_degrees"),
            "wind_direction": row.get("wind_direction_compass") or row.get("wind_direction_cardinal"),
            "wind_speed_mph": first_number(row, "wind_speed_mph"),
            "wind_gust_mph": first_number(row, "wind_gust_mph"),
            "clouds": row.get("clouds_x100ft"),
            "precip_probability_pct": None,
            "phrase": row.get("raw_message") or row.get("text_description"),
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
            "time_et": format_et(ts) if ts is not None else row.get("valid_time_local", "N/A"),
            "temperature_f": first_number(row, "temperature_f"),
            "dewpoint_f": first_number(row, "dewpoint_f"),
            "relative_humidity_pct": first_number(row, "relative_humidity_pct"),
            "wind_direction_degrees": first_number(row, "wind_direction_degrees"),
            "wind_direction": row.get("wind_direction_cardinal"),
            "wind_speed_mph": first_number(row, "wind_speed_mph"),
            "wind_gust_mph": None,
            "clouds": first_number(row, "cloud_cover_pct"),
            "precip_probability_pct": first_number(row, "precip_probability_pct"),
            "phrase": row.get("phrase"),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["time_utc"]).sort_values("time_utc")
    return df


def to_display_df(df: pd.DataFrame, provider_label: Optional[str] = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    out = pd.DataFrame({
        "Time ET": df["time_et"],
        "Provider": provider_label or df["provider"],
        "Temp °F": df["temperature_f"].map(lambda v: compact_num(v)),
        "Dewpoint °F": df["dewpoint_f"].map(lambda v: compact_num(v)),
        "RH %": df["relative_humidity_pct"].map(lambda v: compact_num(v)),
        "Wind": df.apply(lambda r: f"{r.get('wind_direction') or 'N/A'} {compact_num(r.get('wind_direction_degrees')) if pd.notna(r.get('wind_direction_degrees')) else ''}°".strip(), axis=1),
        "Wind mph": df["wind_speed_mph"].map(lambda v: compact_num(v)),
        "Gust mph": df["wind_gust_mph"].map(lambda v: compact_num(v)) if "wind_gust_mph" in df else None,
        "Clouds": df["clouds"],
        "Precip %": df["precip_probability_pct"].map(lambda v: compact_num(v)) if "precip_probability_pct" in df else None,
        "Phrase / Raw": df["phrase"],
    })
    return out[DISPLAY_COLUMNS]


def add_spreads(row: Dict[str, Any]) -> Dict[str, Any]:
    for metric in ["temperature_f", "dewpoint_f", "relative_humidity_pct", "wind_speed_mph", "wind_direction_degrees"]:
        n = row.get(f"nws_{metric}")
        t = row.get(f"twc_{metric}")
        row[f"spread_{metric}"] = round(t - n, 2) if isinstance(n, (int, float)) and isinstance(t, (int, float)) else None
    return row


def build_matched_table(nws_df: pd.DataFrame, twc_df: pd.DataFrame, tolerance_minutes: int, match_direction: str) -> pd.DataFrame:
    if nws_df.empty or twc_df.empty:
        return pd.DataFrame()
    direction = match_direction if match_direction in ("backward", "forward") else "nearest"
    merged = pd.merge_asof(
        nws_df.sort_values("time_utc"),
        twc_df.sort_values("time_utc"),
        on="time_utc",
        direction=direction,
        tolerance=pd.Timedelta(minutes=tolerance_minutes),
        suffixes=("_nws", "_twc"),
    )
    rows = []
    for _, r in merged.iterrows():
        if pd.isna(r.get("provider_twc")):
            continue
        item = {
            "Time ET": format_et(r.get("time_utc")),
            "NWS Temp °F": compact_num(r.get("temperature_f_nws")),
            "TWC Temp °F": compact_num(r.get("temperature_f_twc")),
            "Temp Spread": r.get("temperature_f_twc") - r.get("temperature_f_nws") if pd.notna(r.get("temperature_f_twc")) and pd.notna(r.get("temperature_f_nws")) else None,
            "NWS Dewpoint °F": compact_num(r.get("dewpoint_f_nws")),
            "TWC Dewpoint °F": compact_num(r.get("dewpoint_f_twc")),
            "Dewpoint Spread": r.get("dewpoint_f_twc") - r.get("dewpoint_f_nws") if pd.notna(r.get("dewpoint_f_twc")) and pd.notna(r.get("dewpoint_f_nws")) else None,
            "NWS RH %": compact_num(r.get("relative_humidity_pct_nws")),
            "TWC RH %": compact_num(r.get("relative_humidity_pct_twc")),
            "RH Spread": r.get("relative_humidity_pct_twc") - r.get("relative_humidity_pct_nws") if pd.notna(r.get("relative_humidity_pct_twc")) and pd.notna(r.get("relative_humidity_pct_nws")) else None,
            "NWS Wind": f"{r.get('wind_direction_nws') or 'N/A'} {compact_num(r.get('wind_direction_degrees_nws')) if pd.notna(r.get('wind_direction_degrees_nws')) else ''}°".strip(),
            "TWC Wind": f"{r.get('wind_direction_twc') or 'N/A'} {compact_num(r.get('wind_direction_degrees_twc')) if pd.notna(r.get('wind_direction_degrees_twc')) else ''}°".strip(),
            "NWS Wind mph": compact_num(r.get("wind_speed_mph_nws")),
            "TWC Wind mph": compact_num(r.get("wind_speed_mph_twc")),
            "Wind mph Spread": r.get("wind_speed_mph_twc") - r.get("wind_speed_mph_nws") if pd.notna(r.get("wind_speed_mph_twc")) and pd.notna(r.get("wind_speed_mph_nws")) else None,
            "NWS Clouds": r.get("clouds_nws"),
            "TWC Cloud %": compact_num(r.get("clouds_twc")),
            "TWC Precip %": compact_num(r.get("precip_probability_pct_twc")),
            "NWS Raw": r.get("phrase_nws"),
            "TWC Phrase": r.get("phrase_twc"),
        }
        rows.append(item)
    return pd.DataFrame(rows)


def render_controls() -> Tuple[int, str, List[str], bool]:
    st.sidebar.subheader("Weather comparison controls")
    tolerance = st.sidebar.slider("Auto-match tolerance", 5, 180, 75, 5)
    direction = st.sidebar.selectbox("Match method", ["nearest", "backward", "forward"], index=0)
    groups = st.sidebar.multiselect(
        "Show comparison groups",
        ["temperature", "humidity", "wind", "cloud_precip", "source_text"],
        default=["temperature", "humidity", "wind"],
    )
    show_raw = st.sidebar.checkbox("Show raw JSON expanders", value=False)
    return tolerance, direction, groups, show_raw


def matched_columns(groups: List[str]) -> List[str]:
    cols = ["Time ET"]
    if "temperature" in groups:
        cols += ["NWS Temp °F", "TWC Temp °F", "Temp Spread"]
    if "humidity" in groups:
        cols += ["NWS Dewpoint °F", "TWC Dewpoint °F", "Dewpoint Spread", "NWS RH %", "TWC RH %", "RH Spread"]
    if "wind" in groups:
        cols += ["NWS Wind", "TWC Wind", "NWS Wind mph", "TWC Wind mph", "Wind mph Spread"]
    if "cloud_precip" in groups:
        cols += ["NWS Clouds", "TWC Cloud %", "TWC Precip %"]
    if "source_text" in groups:
        cols += ["NWS Raw", "TWC Phrase"]
    return cols


def render_summary(nws: Dict[str, Any], twc: Dict[str, Any], matched: pd.DataFrame) -> None:
    features = twc.get("derived_features", {}) if isinstance(twc, dict) else {}
    st.header("🌦️ Weather Providers: NWS KMIA vs The Weather Company")
    st.error("🚨 NO REAL TRADING EXECUTION — DRY-RUN / PAPER EVALUATION ONLY")
    st.info("NWS KMIA is the official target. TWC hourly data is shown in the same table style for comparison and spread analysis.")
    cols = st.columns(4)
    cols[0].metric("NWS Current Temp", f"{nws.get('current_temp_f', 'N/A')}°F")
    cols[1].metric("NWS Max So Far", f"{nws.get('observed_max_so_far_f', 'N/A')}°F")
    cols[2].metric("TWC Forecast High", f"{features.get('forecast_high_f', 'N/A')}°F")
    cols[3].metric("TWC Hourly Max", f"{features.get('hourly_max_temp_f', 'N/A')}°F")
    cols2 = st.columns(4)
    cols2[0].metric("NWS Status", provider_status(nws, "nws"))
    cols2[1].metric("TWC Status", provider_status(twc, "twc"))
    cols2[2].metric("Matched Intervals", len(matched))
    if not matched.empty and "Temp Spread" in matched:
        med = matched["Temp Spread"].dropna().median()
        cols2[3].metric("Median Temp Spread", f"{med:+.1f}°F" if pd.notna(med) else "N/A")
    else:
        cols2[3].metric("Median Temp Spread", "N/A")


def render_provider_tables(nws_df: pd.DataFrame, twc_df: pd.DataFrame) -> None:
    st.subheader("Provider Tables — Same Column Format")
    tab1, tab2 = st.tabs(["NWS KMIA Hourly Observations", "TWC Hourly Forecast"])
    with tab1:
        st.dataframe(to_display_df(nws_df, "NWS"), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(to_display_df(twc_df, "TWC"), use_container_width=True, hide_index=True)


def render_matched_table(matched: pd.DataFrame, groups: List[str]) -> None:
    st.subheader("Matched Interval Comparison")
    if matched.empty:
        st.warning("No matched NWS/TWC intervals found. Check that TWC hourly rows are present and increase the tolerance if needed.")
        return
    cols = [c for c in matched_columns(groups) if c in matched.columns]
    view = matched[cols].copy()
    st.dataframe(view, use_container_width=True, hide_index=True)
    spread_cols = [c for c in ["Temp Spread", "Dewpoint Spread", "RH Spread", "Wind mph Spread"] if c in matched.columns]
    summary = []
    for col in spread_cols:
        vals = matched[col].dropna()
        if not vals.empty:
            summary.append({"Metric": col, "Median": vals.median(), "Mean": vals.mean(), "Max Abs": vals.abs().max(), "Count": len(vals)})
    if summary:
        st.markdown("**Spread Summary**")
        st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)


def render_daily_twc(twc: Dict[str, Any]) -> None:
    daily = twc.get("daily_forecast", []) if isinstance(twc, dict) else []
    if not daily:
        return
    st.subheader("TWC Daily Forecast Summary")
    df = pd.DataFrame(daily)
    rename = {
        "valid_time_utc": "Valid UTC",
        "max_temp_f": "Max °F",
        "min_temp_f": "Min °F",
        "precip_probability_pct": "Precip %",
        "narrative": "Narrative",
    }
    cols = [c for c in rename if c in df.columns]
    st.dataframe(df[cols].rename(columns=rename), use_container_width=True, hide_index=True)


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
    tolerance, direction, groups, show_raw = render_controls()
    matched = build_matched_table(nws_df, twc_df, tolerance, direction)
    st.caption(f"NWS source: {latest_nws.name if latest_nws else 'missing'}")
    st.caption(f"TWC source: {latest_twc.name if latest_twc else 'missing'}")
    render_summary(nws, twc, matched)
    st.divider()
    render_provider_tables(nws_df, twc_df)
    st.divider()
    render_matched_table(matched, groups)
    st.divider()
    render_daily_twc(twc)
    if show_raw:
        st.divider()
        with st.expander("NWS raw JSON"):
            st.json(nws)
        with st.expander("TWC raw JSON"):
            st.json(twc)
    st.divider()
    st.subheader("Historical variance objective")
    st.write("Join official NWS KMIA daily max settlements to archived TWC hourly/daily snapshots by target date and issue horizon, then compute median TWC-minus-NWS variance, MAE, within-1/2/3°F rates, and bin-boundary miss rates.")


if __name__ == "__main__":
    main()

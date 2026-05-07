import json
import os
import subprocess
import time
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
NWS_UPDATE_SCRIPT = ROOT / "scripts" / "update_nws_live_data.sh"
TWC_UPDATE_SCRIPT = ROOT / "scripts" / "update_twc_kmia_data.sh"

DEFAULT_AUTO_REFRESH_SECONDS = int(os.getenv("WEATHER_PROVIDERS_AUTO_REFRESH_SECONDS", "60"))
MIN_UPDATE_SECONDS = int(os.getenv("WEATHER_PROVIDER_MIN_UPDATE_SECONDS", "45"))
NWS_STALE_SECONDS = int(os.getenv("NWS_PROVIDER_STALE_SECONDS", "900"))
TWC_STALE_SECONDS = int(os.getenv("TWC_PROVIDER_STALE_SECONDS", "1800"))

DISPLAY_COLUMNS = [
    "Time ET", "Provider", "Type", "Temp °F", "Dewpoint °F", "RH %", "Wind",
    "Wind mph", "Gust mph", "Clouds", "Precip %", "Phrase / Raw",
]


def latest_file(directory: Path, pattern: str) -> Optional[Path]:
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def file_age_seconds(path: Optional[Path]) -> Optional[float]:
    return max(0.0, time.time() - path.stat().st_mtime) if path and path.exists() else None


def load_json(path: Optional[Path]) -> Dict[str, Any]:
    if path and path.exists():
        with path.open("r") as f:
            return json.load(f)
    return {}


def run_update(script: Path, label: str) -> Tuple[bool, str]:
    if not script.exists():
        return False, f"{label} update script not found: {script}"
    try:
        result = subprocess.run(
            ["bash", str(script)], cwd=str(ROOT), capture_output=True,
            text=True, timeout=45, env=os.environ.copy()
        )
        msg = (result.stdout or "")[-1200:]
        if result.stderr:
            msg += "\n" + result.stderr[-1200:]
        return result.returncode == 0, msg.strip()
    except Exception as exc:
        return False, f"{label} update failed: {exc}"


def maybe_update_provider(path: Optional[Path], stale_seconds: int, script: Path, label: str, force: bool = False) -> Tuple[Optional[Path], Optional[str]]:
    key = f"last_{label.lower()}_update_attempt"
    last_attempt = st.session_state.get(key, 0.0)
    age = file_age_seconds(path)
    stale = force or age is None or age > stale_seconds
    if not stale:
        return path, None
    if time.time() - last_attempt < MIN_UPDATE_SECONDS:
        return path, f"{label} is stale, but update was throttled."
    st.session_state[key] = time.time()
    ok, msg = run_update(script, label)
    if not ok:
        return path, msg
    if label == "NWS":
        new_path = NWS_DIR / "latest_nws_kmia_snapshot.json"
        if not new_path.exists():
            new_path = latest_file(NWS_DIR, "nws_kmia_snapshot_*.json")
    else:
        new_path = TWC_DIR / "latest_twc_kmia_snapshot.json"
        if not new_path.exists():
            new_path = latest_file(TWC_DIR, "twc_kmia_snapshot_*.json")
    return new_path, msg


def parse_ts(value: Any) -> Optional[pd.Timestamp]:
    if value is None or value == "":
        return None
    try:
        ts = pd.to_datetime(value, unit="s", utc=True, errors="coerce") if isinstance(value, (int, float)) else pd.to_datetime(value, utc=True, errors="coerce")
        return None if pd.isna(ts) else ts
    except Exception:
        return None


def format_et(ts: Any) -> str:
    parsed = parse_ts(ts)
    return "N/A" if parsed is None else parsed.tz_convert("America/New_York").strftime("%m/%d %I:%M %p")


def first_number(row: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        val = row.get(key)
        if isinstance(val, (int, float)) and not pd.isna(val):
            return float(val)
    return None


def compact_num(value: Any, decimals: int = 0) -> Any:
    if isinstance(value, (int, float)) and not pd.isna(value):
        return int(round(value)) if decimals == 0 else round(float(value), decimals)
    return None


def nested_get(data: Any, path: Tuple[str, ...]) -> Any:
    node = data
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
    return node


def first_list(data: Dict[str, Any], paths: List[Tuple[str, ...]]) -> List[Dict[str, Any]]:
    for path in paths:
        node = nested_get(data, path)
        if isinstance(node, list):
            return [r for r in node if isinstance(r, dict)]
    return []


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


def extract_nws_observed_rows(nws: Dict[str, Any]) -> List[Dict[str, Any]]:
    return first_list(nws, [
        ("recent_observations_table",), ("observations",), ("recent_observations",),
        ("api_inputs", "recent_observations_table"), ("api_inputs", "observations"), ("raw", "observations"),
    ])


def extract_nws_forecast_rows(nws: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = first_list(nws, [
        ("hourly_forecast",), ("forecast_hourly",), ("hourly",),
        ("api_inputs", "hourly_forecast"), ("raw", "hourly_forecast"),
        ("forecast", "hourly"), ("forecasts", "hourly"),
        ("api_forecast_hourly",), ("forecast_periods",),
        ("properties", "periods"), ("raw", "forecast", "properties", "periods"),
    ])
    return rows


def normalize_rows(rows: List[Dict[str, Any]], provider: str, row_type: str) -> pd.DataFrame:
    normalized = []
    for row in rows:
        ts = parse_ts(row.get("timestamp_utc") or row.get("valid_time_utc") or row.get("validTimeUtc") or row.get("time_utc") or row.get("startTime") or row.get("start_time"))
        if ts is None and row.get("date_et") and row.get("time_et"):
            ts = parse_ts(f"{row.get('date_et')} {row.get('time_et')}")
        temp = first_number(row, "temperature_f", "current_temp_f", "temperature", "temp", "temperatureMax")
        wind_dir = row.get("wind_direction_compass") or row.get("wind_direction_cardinal") or row.get("windDirectionCardinal") or row.get("windDirection") or row.get("windDirectionText")
        normalized.append({
            "provider": provider,
            "type": row_type,
            "time_utc": ts,
            "time_et": format_et(ts) if ts is not None else row.get("time_et") or row.get("valid_time_local") or row.get("validTimeLocal") or "N/A",
            "temperature_f": temp,
            "dewpoint_f": first_number(row, "dewpoint_f", "temperatureDewPoint", "dewPoint", "dewpt"),
            "relative_humidity_pct": first_number(row, "relative_humidity_pct", "relativeHumidity", "humidity"),
            "wind_direction_degrees": first_number(row, "wind_direction_degrees", "windDirection", "wdir"),
            "wind_direction": wind_dir,
            "wind_speed_mph": first_number(row, "wind_speed_mph", "windSpeed", "wspd"),
            "wind_gust_mph": first_number(row, "wind_gust_mph", "windGust", "gust"),
            "clouds": row.get("clouds_x100ft") or first_number(row, "cloud_cover_pct", "cloudCover", "clds"),
            "precip_probability_pct": first_number(row, "precip_probability_pct", "precipChance", "probabilityOfPrecipitation", "pop"),
            "phrase": row.get("raw_message") or row.get("shortForecast") or row.get("detailedForecast") or row.get("phrase") or row.get("wxPhraseLong") or row.get("narrative"),
        })
    df = pd.DataFrame(normalized)
    if not df.empty:
        df = df.dropna(subset=["time_utc"]).sort_values("time_utc")
    return df


def normalize_nws_observed(nws: Dict[str, Any]) -> pd.DataFrame:
    return normalize_rows(extract_nws_observed_rows(nws), "NWS", "Observed")


def normalize_nws_forecast(nws: Dict[str, Any]) -> pd.DataFrame:
    return normalize_rows(extract_nws_forecast_rows(nws), "NWS", "Forecast")


def normalize_twc_forecast(twc: Dict[str, Any]) -> pd.DataFrame:
    rows = twc.get("hourly_forecast", []) if isinstance(twc, dict) else []
    return normalize_rows([r for r in rows if isinstance(r, dict)], "TWC", "Forecast")


def to_display_df(df: pd.DataFrame, provider_label: Optional[str] = None, max_rows: Optional[int] = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    display_df = df.head(max_rows) if max_rows else df
    out = pd.DataFrame({
        "Time ET": display_df["time_et"],
        "Provider": provider_label or display_df["provider"],
        "Type": display_df["type"],
        "Temp °F": display_df["temperature_f"].map(lambda v: compact_num(v)),
        "Dewpoint °F": display_df["dewpoint_f"].map(lambda v: compact_num(v)),
        "RH %": display_df["relative_humidity_pct"].map(lambda v: compact_num(v)),
        "Wind": display_df.apply(lambda r: f"{r.get('wind_direction') or 'N/A'} {compact_num(r.get('wind_direction_degrees')) if pd.notna(r.get('wind_direction_degrees')) else ''}°".strip(), axis=1),
        "Wind mph": display_df["wind_speed_mph"].map(lambda v: compact_num(v)),
        "Gust mph": display_df["wind_gust_mph"].map(lambda v: compact_num(v)) if "wind_gust_mph" in display_df else None,
        "Clouds": display_df["clouds"],
        "Precip %": display_df["precip_probability_pct"].map(lambda v: compact_num(v)) if "precip_probability_pct" in display_df else None,
        "Phrase / Raw": display_df["phrase"],
    })
    return out[DISPLAY_COLUMNS]


def build_matched_table(nws_forecast_df: pd.DataFrame, twc_forecast_df: pd.DataFrame, tolerance_minutes: int, match_direction: str) -> pd.DataFrame:
    if nws_forecast_df.empty or twc_forecast_df.empty:
        return pd.DataFrame()
    direction = match_direction if match_direction in ("backward", "forward") else "nearest"
    merged = pd.merge_asof(
        nws_forecast_df.sort_values("time_utc"), twc_forecast_df.sort_values("time_utc"),
        on="time_utc", direction=direction, tolerance=pd.Timedelta(minutes=tolerance_minutes), suffixes=("_nws", "_twc")
    )
    rows = []
    for _, r in merged.iterrows():
        if pd.isna(r.get("provider_twc")):
            continue
        rows.append({
            "Time ET": format_et(r.get("time_utc")),
            "NWS Forecast °F": compact_num(r.get("temperature_f_nws")),
            "TWC Forecast °F": compact_num(r.get("temperature_f_twc")),
            "Forecast Spread": r.get("temperature_f_twc") - r.get("temperature_f_nws") if pd.notna(r.get("temperature_f_twc")) and pd.notna(r.get("temperature_f_nws")) else None,
            "NWS Dewpoint °F": compact_num(r.get("dewpoint_f_nws")),
            "TWC Dewpoint °F": compact_num(r.get("dewpoint_f_twc")),
            "NWS RH %": compact_num(r.get("relative_humidity_pct_nws")),
            "TWC RH %": compact_num(r.get("relative_humidity_pct_twc")),
            "NWS Wind": f"{r.get('wind_direction_nws') or 'N/A'} {compact_num(r.get('wind_direction_degrees_nws')) if pd.notna(r.get('wind_direction_degrees_nws')) else ''}°".strip(),
            "TWC Wind": f"{r.get('wind_direction_twc') or 'N/A'} {compact_num(r.get('wind_direction_degrees_twc')) if pd.notna(r.get('wind_direction_degrees_twc')) else ''}°".strip(),
            "NWS Wind mph": compact_num(r.get("wind_speed_mph_nws")),
            "TWC Wind mph": compact_num(r.get("wind_speed_mph_twc")),
            "NWS Phrase": r.get("phrase_nws"),
            "TWC Phrase": r.get("phrase_twc"),
        })
    return pd.DataFrame(rows)


def render_controls() -> Tuple[int, str, List[str], bool, bool, int, bool]:
    st.sidebar.subheader("Weather comparison controls")
    auto_update = st.sidebar.checkbox("Auto-update stale provider snapshots", value=True)
    auto_rerun = st.sidebar.checkbox("Auto-refresh page", value=True)
    refresh_seconds = st.sidebar.slider("Page refresh seconds", 30, 300, DEFAULT_AUTO_REFRESH_SECONDS, 15)
    tolerance = st.sidebar.slider("Forecast match tolerance", 5, 180, 75, 5)
    direction = st.sidebar.selectbox("Match method", ["nearest", "backward", "forward"], index=0)
    groups = st.sidebar.multiselect("Show comparison groups", ["temperature", "humidity", "wind", "source_text"], default=["temperature", "wind"])
    show_raw = st.sidebar.checkbox("Show raw JSON expanders", value=False)
    return tolerance, direction, groups, show_raw, auto_update, refresh_seconds, auto_rerun


def matched_columns(groups: List[str]) -> List[str]:
    cols = ["Time ET"]
    if "temperature" in groups:
        cols += ["NWS Forecast °F", "TWC Forecast °F", "Forecast Spread"]
    if "humidity" in groups:
        cols += ["NWS Dewpoint °F", "TWC Dewpoint °F", "NWS RH %", "TWC RH %"]
    if "wind" in groups:
        cols += ["NWS Wind", "TWC Wind", "NWS Wind mph", "TWC Wind mph"]
    if "source_text" in groups:
        cols += ["NWS Phrase", "TWC Phrase"]
    return cols


def render_summary(nws: Dict[str, Any], twc: Dict[str, Any], matched: pd.DataFrame, nws_age: Optional[float], twc_age: Optional[float]) -> None:
    features = twc.get("derived_features", {}) if isinstance(twc, dict) else {}
    st.header("🌦️ Forecast Providers: NWS KMIA vs The Weather Company")
    st.error("🚨 NO REAL TRADING EXECUTION — DRY-RUN / PAPER EVALUATION ONLY")
    st.info("This page compares **NWS forecast rows** against **TWC forecast rows**. NWS observed KMIA station rows are shown separately for verification only.")
    cols = st.columns(4)
    cols[0].metric("NWS Observed Temp", f"{nws.get('current_temp_f', 'N/A')}°F")
    cols[1].metric("NWS Observed Max", f"{nws.get('observed_max_so_far_f', 'N/A')}°F")
    cols[2].metric("TWC Forecast High", f"{features.get('forecast_high_f', 'N/A')}°F")
    cols[3].metric("TWC Hourly Max", f"{features.get('hourly_max_temp_f', 'N/A')}°F")
    cols2 = st.columns(4)
    cols2[0].metric("NWS Status", provider_status(nws, "nws"))
    cols2[1].metric("TWC Status", provider_status(twc, "twc"))
    cols2[2].metric("Matched Forecast Intervals", len(matched))
    med = matched["Forecast Spread"].dropna().median() if not matched.empty and "Forecast Spread" in matched else None
    cols2[3].metric("Median Forecast Spread", f"{med:+.1f}°F" if med is not None and pd.notna(med) else "N/A")
    st.caption(f"Snapshot age — NWS: {int(nws_age or 0)}s | TWC: {int(twc_age or 0)}s")


def render_provider_tables(nws_forecast_df: pd.DataFrame, twc_forecast_df: pd.DataFrame, nws_observed_df: pd.DataFrame) -> None:
    st.subheader("Provider Forecast Tables — Same Column Format")
    tab1, tab2, tab3 = st.tabs(["NWS Hourly Forecast", "TWC Hourly Forecast", "NWS KMIA Observed / Verification"])
    with tab1:
        if nws_forecast_df.empty:
            st.warning("No NWS hourly forecast rows found in the current NWS snapshot. The NWS client may need to persist hourly forecast periods into the snapshot.")
        st.dataframe(to_display_df(nws_forecast_df, "NWS", max_rows=72), width="stretch", hide_index=True)
    with tab2:
        st.dataframe(to_display_df(twc_forecast_df, "TWC", max_rows=72), width="stretch", hide_index=True)
    with tab3:
        st.dataframe(to_display_df(nws_observed_df.sort_values("time_utc", ascending=False), "NWS", max_rows=48), width="stretch", hide_index=True)


def render_matched_table(matched: pd.DataFrame, groups: List[str]) -> None:
    st.subheader("Matched Forecast Interval Comparison")
    if matched.empty:
        st.warning("No matched NWS/TWC forecast intervals found. Check that the NWS snapshot includes hourly forecast rows and that TWC hourly rows are present.")
        return
    view = matched[[c for c in matched_columns(groups) if c in matched.columns]].copy()
    st.dataframe(view, width="stretch", hide_index=True)
    vals = matched["Forecast Spread"].dropna() if "Forecast Spread" in matched else pd.Series(dtype=float)
    if not vals.empty:
        st.markdown("**Forecast Spread Summary**")
        st.dataframe(pd.DataFrame([{"Metric": "TWC Forecast - NWS Forecast", "Median": vals.median(), "Mean": vals.mean(), "Max Abs": vals.abs().max(), "Count": len(vals)}]), width="stretch", hide_index=True)


def render_daily_twc(twc: Dict[str, Any]) -> None:
    daily = twc.get("daily_forecast", []) if isinstance(twc, dict) else []
    if not daily:
        return
    st.subheader("TWC Daily Forecast Summary")
    df = pd.DataFrame(daily)
    rename = {"valid_time_utc": "Valid UTC", "max_temp_f": "Max °F", "min_temp_f": "Min °F", "precip_probability_pct": "Precip %", "narrative": "Narrative"}
    cols = [c for c in rename if c in df.columns]
    st.dataframe(df[cols].rename(columns=rename), width="stretch", hide_index=True)


def main() -> None:
    st.set_page_config(page_title="KMIA Weather Providers", page_icon="🌦️", layout="wide")
    tolerance, direction, groups, show_raw, auto_update, refresh_seconds, auto_rerun = render_controls()
    latest_nws = NWS_DIR / "latest_nws_kmia_snapshot.json"
    if not latest_nws.exists():
        latest_nws = latest_file(NWS_DIR, "nws_kmia_snapshot_*.json")
    latest_twc = TWC_DIR / "latest_twc_kmia_snapshot.json"
    if not latest_twc.exists():
        latest_twc = latest_file(TWC_DIR, "twc_kmia_snapshot_*.json")
    if st.sidebar.button("Refresh provider data now"):
        latest_nws, nws_msg = maybe_update_provider(latest_nws, 0, NWS_UPDATE_SCRIPT, "NWS", force=True)
        latest_twc, twc_msg = maybe_update_provider(latest_twc, 0, TWC_UPDATE_SCRIPT, "TWC", force=True)
        with st.expander("Manual refresh log", expanded=True):
            st.text((nws_msg or "") + "\n" + (twc_msg or ""))
    if auto_update:
        latest_nws, nws_msg = maybe_update_provider(latest_nws, NWS_STALE_SECONDS, NWS_UPDATE_SCRIPT, "NWS")
        latest_twc, twc_msg = maybe_update_provider(latest_twc, TWC_STALE_SECONDS, TWC_UPDATE_SCRIPT, "TWC")
        if nws_msg and "UPDATE COMPLETE" not in nws_msg and "throttled" not in nws_msg:
            st.sidebar.warning(nws_msg[:500])
        if twc_msg and "UPDATE COMPLETE" not in twc_msg and "throttled" not in twc_msg:
            st.sidebar.warning(twc_msg[:500])
    nws = load_json(latest_nws)
    twc = load_json(latest_twc)
    nws_age = file_age_seconds(latest_nws)
    twc_age = file_age_seconds(latest_twc)
    nws_observed_df = normalize_nws_observed(nws)
    nws_forecast_df = normalize_nws_forecast(nws)
    twc_forecast_df = normalize_twc_forecast(twc)
    matched = build_matched_table(nws_forecast_df, twc_forecast_df, tolerance, direction)
    st.caption(f"NWS source: {latest_nws.name if latest_nws else 'missing'}")
    st.caption(f"TWC source: {latest_twc.name if latest_twc else 'missing'}")
    render_summary(nws, twc, matched, nws_age, twc_age)
    st.divider()
    render_provider_tables(nws_forecast_df, twc_forecast_df, nws_observed_df)
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
    st.write("Compare forecast-vs-forecast by issue/valid time, then separately score both providers against official NWS KMIA observed max at settlement.")
    if auto_rerun:
        time.sleep(refresh_seconds)
        st.rerun()


if __name__ == "__main__":
    main()

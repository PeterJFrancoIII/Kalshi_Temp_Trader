from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "backend" / "data" / "processed"
NWS_DIR = DATA / "weather_nws"
TWC_DIR = DATA / "weather_company"

DISPLAY_COLUMNS = [
    "Time ET", "Provider", "Type", "Temp F", "Dewpoint F", "RH %",
    "Wind", "Wind mph", "Gust mph", "Clouds", "Precip %", "Phrase / Raw",
]
DAILY_COLUMNS = ["Day", "Provider", "Period", "High F", "Low F", "Precip %", "Wind", "Wind mph", "Narrative"]


def latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def load_json(path: Path | None) -> dict[str, Any]:
    if path and path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def file_age_seconds(path: Path | None) -> float | None:
    return max(0.0, time.time() - path.stat().st_mtime) if path and path.exists() else None


def parse_ts(value: Any) -> pd.Timestamp | None:
    if value is None or value == "":
        return None
    try:
        ts = pd.to_datetime(value, unit="s", utc=True, errors="coerce") if isinstance(value, (int, float)) else pd.to_datetime(value, utc=True, errors="coerce")
        return None if pd.isna(ts) else ts
    except Exception:
        return None


def format_et(value: Any) -> str:
    ts = parse_ts(value)
    return "N/A" if ts is None else ts.tz_convert("America/New_York").strftime("%m/%d %I:%M %p")


def date_key(value: Any, fallback: Any = None) -> str | None:
    ts = parse_ts(value)
    if ts is not None:
        return ts.tz_convert("America/New_York").strftime("%Y-%m-%d")
    if fallback:
        fb = pd.to_datetime(fallback, errors="coerce")
        if not pd.isna(fb):
            return fb.strftime("%Y-%m-%d")
    return None


def format_day(value: Any, fallback: Any = None) -> str:
    ts = parse_ts(value)
    if ts is not None:
        return ts.tz_convert("America/New_York").strftime("%a %m/%d")
    if fallback:
        fb = pd.to_datetime(fallback, errors="coerce")
        if not pd.isna(fb):
            return fb.strftime("%a %m/%d")
    return str(fallback or "N/A")


def first_number(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, (int, float)) and not pd.isna(value):
            return float(value)
    return None


def compact(value: Any) -> Any:
    return int(round(value)) if isinstance(value, (int, float)) and not pd.isna(value) else None


def first_list(data: dict[str, Any], paths: list[tuple[str, ...]]) -> list[dict[str, Any]]:
    for path in paths:
        node: Any = data
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, list):
            return [row for row in node if isinstance(row, dict)]
    return []


def normalize_time(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "time_utc" not in df.columns:
        return df
    out = df.copy()
    out["time_utc"] = pd.to_datetime(out["time_utc"], utc=True, errors="coerce")
    out = out.dropna(subset=["time_utc"])
    out["time_utc"] = out["time_utc"].astype("datetime64[ns, UTC]")
    return out


def provider_status(payload: dict[str, Any], provider: str) -> str:
    if not payload:
        return "MISSING"
    text = json.dumps(payload, default=str).upper()
    if "MISSING_API_KEY" in text:
        return "MISSING API KEY"
    if provider == "nws" and payload.get("endpoint_status") == "ERROR":
        return "ERROR"
    if payload.get("stale_data"):
        return "STALE"
    return "CONNECTED"


def extract_nws_observed(nws: dict[str, Any]) -> list[dict[str, Any]]:
    return first_list(nws, [
        ("recent_observations_table",), ("observations",), ("recent_observations",),
        ("api_inputs", "recent_observations_table"), ("api_inputs", "observations"),
        ("raw", "observations"),
    ])


def extract_nws_forecast(nws: dict[str, Any]) -> list[dict[str, Any]]:
    return first_list(nws, [
        ("hourly_forecast",), ("forecast_hourly",), ("hourly",),
        ("api_inputs", "hourly_forecast"), ("raw", "hourly_forecast"),
        ("forecast", "hourly"), ("forecasts", "hourly"), ("api_forecast_hourly",),
        ("forecast_periods",), ("properties", "periods"),
        ("raw", "forecast", "properties", "periods"),
    ])


def normalize_rows(rows: list[dict[str, Any]], provider: str, row_type: str) -> pd.DataFrame:
    out = []
    for row in rows:
        ts = parse_ts(row.get("timestamp_utc") or row.get("valid_time_utc") or row.get("validTimeUtc") or row.get("time_utc") or row.get("startTime") or row.get("start_time"))
        if ts is None and row.get("date_et") and row.get("time_et"):
            ts = parse_ts(f"{row.get('date_et')} {row.get('time_et')}")
        wind_dir = row.get("wind_direction_compass") or row.get("wind_direction_cardinal") or row.get("windDirectionCardinal") or row.get("windDirection") or row.get("windDirectionText")
        out.append({
            "provider": provider,
            "type": row_type,
            "time_utc": ts,
            "time_et": format_et(ts) if ts is not None else row.get("time_et") or row.get("valid_time_local") or row.get("validTimeLocal") or "N/A",
            "temperature_f": first_number(row, "temperature_f", "current_temp_f", "temperature", "temp", "temperatureMax", "max_temp_f"),
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
    df = pd.DataFrame(out)
    return normalize_time(df).sort_values("time_utc") if not df.empty else df


def normalize_twc_observed(twc: dict[str, Any]) -> pd.DataFrame:
    current = twc.get("current_conditions", {}) if isinstance(twc, dict) else {}
    if not isinstance(current, dict) or not current:
        return pd.DataFrame()
    if not any(current.get(k) is not None for k in ["temperature_f", "dewpoint_f", "relative_humidity_pct", "wind_speed_mph"]):
        return pd.DataFrame()
    ts = parse_ts(current.get("observation_time_utc")) or parse_ts(twc.get("fetched_at_utc"))
    return normalize_time(pd.DataFrame([{
        "provider": "TWC", "type": "Observed", "time_utc": ts, "time_et": format_et(ts),
        "temperature_f": first_number(current, "temperature_f"),
        "dewpoint_f": first_number(current, "dewpoint_f"),
        "relative_humidity_pct": first_number(current, "relative_humidity_pct"),
        "wind_direction_degrees": first_number(current, "wind_direction_degrees"),
        "wind_direction": current.get("wind_direction_cardinal"),
        "wind_speed_mph": first_number(current, "wind_speed_mph"),
        "wind_gust_mph": None, "clouds": None, "precip_probability_pct": None,
        "phrase": current.get("phrase"),
    }]))


def normalize_nws_daily(nws: dict[str, Any]) -> pd.DataFrame:
    rows = nws.get("daily_forecast", []) if isinstance(nws, dict) else []
    out = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("isDaytime", True):
            continue
        valid = row.get("valid_time_utc")
        out.append({
            "date_key": date_key(valid, row.get("forecast_date_et")),
            "Day": row.get("display_day") or format_day(valid, row.get("forecast_date_et")),
            "Provider": "NWS", "Period": row.get("period_name") or "Day",
            "High F": compact(first_number(row, "temperature_f", "temperature")),
            "Low F": None,
            "Precip %": compact(first_number(row, "precip_probability_pct", "precipChance", "pop")),
            "Wind": row.get("wind_direction_compass") or row.get("wind_direction"),
            "Wind mph": compact(first_number(row, "wind_speed_mph", "windSpeed")),
            "Narrative": row.get("shortForecast") or row.get("detailedForecast") or row.get("raw_message"),
        })
    df = pd.DataFrame(out)
    return df.sort_values("date_key") if not df.empty else df


def normalize_twc_daily(twc: dict[str, Any]) -> pd.DataFrame:
    rows = twc.get("daily_forecast", []) if isinstance(twc, dict) else []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        valid = row.get("valid_time_utc")
        out.append({
            "date_key": date_key(valid), "Day": format_day(valid), "Provider": "TWC", "Period": "Daily",
            "High F": compact(first_number(row, "max_temp_f", "temperatureMax")),
            "Low F": compact(first_number(row, "min_temp_f", "temperatureMin")),
            "Precip %": compact(first_number(row, "precip_probability_pct", "precipChance", "pop")),
            "Wind": None, "Wind mph": None, "Narrative": row.get("narrative"),
        })
    df = pd.DataFrame(out)
    return df.sort_values("date_key") if not df.empty else df


def display_df(df: pd.DataFrame, provider_label: str | None = None, max_rows: int | None = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    src = df.head(max_rows) if max_rows else df
    out = pd.DataFrame({
        "Time ET": src["time_et"],
        "Provider": provider_label or src["provider"],
        "Type": src["type"],
        "Temp F": src["temperature_f"].map(compact),
        "Dewpoint F": src["dewpoint_f"].map(compact),
        "RH %": src["relative_humidity_pct"].map(compact),
        "Wind": src.apply(lambda r: f"{r.get('wind_direction') or 'N/A'} {compact(r.get('wind_direction_degrees')) if pd.notna(r.get('wind_direction_degrees')) else ''}".strip(), axis=1),
        "Wind mph": src["wind_speed_mph"].map(compact),
        "Gust mph": src["wind_gust_mph"].map(compact) if "wind_gust_mph" in src else None,
        "Clouds": src["clouds"],
        "Precip %": src["precip_probability_pct"].map(compact) if "precip_probability_pct" in src else None,
        "Phrase / Raw": src["phrase"],
    })
    return out[DISPLAY_COLUMNS]


def build_hourly_match(nws_df: pd.DataFrame, twc_df: pd.DataFrame, tolerance: int, direction: str) -> pd.DataFrame:
    nws_df = normalize_time(nws_df)
    twc_df = normalize_time(twc_df)
    if nws_df.empty or twc_df.empty:
        return pd.DataFrame()
    merge_direction = direction if direction in ("backward", "forward") else "nearest"
    merged = pd.merge_asof(nws_df.sort_values("time_utc"), twc_df.sort_values("time_utc"), on="time_utc", direction=merge_direction, tolerance=pd.Timedelta(minutes=tolerance), suffixes=("_nws", "_twc"))
    rows = []
    for _, r in merged.iterrows():
        if pd.isna(r.get("provider_twc")):
            continue
        rows.append({
            "Time ET": format_et(r.get("time_utc")),
            "NWS Forecast F": compact(r.get("temperature_f_nws")),
            "TWC Forecast F": compact(r.get("temperature_f_twc")),
            "Forecast Spread": r.get("temperature_f_twc") - r.get("temperature_f_nws") if pd.notna(r.get("temperature_f_twc")) and pd.notna(r.get("temperature_f_nws")) else None,
            "NWS Dewpoint F": compact(r.get("dewpoint_f_nws")),
            "TWC Dewpoint F": compact(r.get("dewpoint_f_twc")),
            "NWS RH %": compact(r.get("relative_humidity_pct_nws")),
            "TWC RH %": compact(r.get("relative_humidity_pct_twc")),
            "NWS Wind": f"{r.get('wind_direction_nws') or 'N/A'} {compact(r.get('wind_direction_degrees_nws')) if pd.notna(r.get('wind_direction_degrees_nws')) else ''}".strip(),
            "TWC Wind": f"{r.get('wind_direction_twc') or 'N/A'} {compact(r.get('wind_direction_degrees_twc')) if pd.notna(r.get('wind_direction_degrees_twc')) else ''}".strip(),
            "NWS Wind mph": compact(r.get("wind_speed_mph_nws")),
            "TWC Wind mph": compact(r.get("wind_speed_mph_twc")),
            "NWS Phrase": r.get("phrase_nws"),
            "TWC Phrase": r.get("phrase_twc"),
        })
    return pd.DataFrame(rows)


def build_observed_match(nws_df: pd.DataFrame, twc_df: pd.DataFrame, tolerance: int, direction: str) -> pd.DataFrame:
    nws_df = normalize_time(nws_df)
    twc_df = normalize_time(twc_df)
    if nws_df.empty or twc_df.empty:
        return pd.DataFrame()
    merge_direction = direction if direction in ("backward", "forward") else "nearest"
    merged = pd.merge_asof(nws_df.sort_values("time_utc"), twc_df.sort_values("time_utc"), on="time_utc", direction=merge_direction, tolerance=pd.Timedelta(minutes=tolerance), suffixes=("_nws", "_twc"))
    rows = []
    for _, r in merged.iterrows():
        if pd.isna(r.get("provider_twc")):
            continue
        rows.append({
            "Time ET": format_et(r.get("time_utc")),
            "NWS Observed F": compact(r.get("temperature_f_nws")),
            "TWC Observed F": compact(r.get("temperature_f_twc")),
            "Observed Temp Spread": r.get("temperature_f_twc") - r.get("temperature_f_nws") if pd.notna(r.get("temperature_f_twc")) and pd.notna(r.get("temperature_f_nws")) else None,
            "NWS Dewpoint F": compact(r.get("dewpoint_f_nws")),
            "TWC Dewpoint F": compact(r.get("dewpoint_f_twc")),
            "NWS Wind mph": compact(r.get("wind_speed_mph_nws")),
            "TWC Wind mph": compact(r.get("wind_speed_mph_twc")),
            "NWS Raw": r.get("phrase_nws"),
            "TWC Phrase": r.get("phrase_twc"),
        })
    return pd.DataFrame(rows)


def build_daily_match(nws_daily: pd.DataFrame, twc_daily: pd.DataFrame) -> pd.DataFrame:
    if nws_daily.empty or twc_daily.empty:
        return pd.DataFrame()
    merged = pd.merge(nws_daily, twc_daily, on="date_key", how="inner", suffixes=(" NWS", " TWC"))
    rows = []
    for _, r in merged.iterrows():
        nws_high = r.get("High F NWS")
        twc_high = r.get("High F TWC")
        rows.append({
            "Day": r.get("Day NWS") or r.get("Day TWC"),
            "NWS High F": nws_high,
            "TWC High F": twc_high,
            "Daily High Spread": twc_high - nws_high if pd.notna(nws_high) and pd.notna(twc_high) else None,
            "NWS Precip %": r.get("Precip % NWS"),
            "TWC Precip %": r.get("Precip % TWC"),
            "NWS Narrative": r.get("Narrative NWS"),
            "TWC Narrative": r.get("Narrative TWC"),
        })
    return pd.DataFrame(rows)


def main() -> None:
    st.set_page_config(page_title="TWC vs NWS Comparison", page_icon="🌦️", layout="wide")
    st.title("TWC vs NWS Comparison")
    st.error("DRY-RUN / PAPER EVALUATION ONLY — NO REAL TRADING EXECUTION")

    st.sidebar.subheader("Weather comparison controls")
    tolerance = st.sidebar.slider("Forecast/observed match tolerance", 5, 180, 20, 5)
    direction = st.sidebar.selectbox("Match method", ["nearest", "backward", "forward"], index=0)
    groups = st.sidebar.multiselect("Show matched forecast groups", ["temperature", "humidity", "wind", "source_text"], default=["temperature", "wind"])
    show_raw = st.sidebar.checkbox("Show raw JSON expanders", value=False)

    latest_nws = NWS_DIR / "latest_nws_kmia_snapshot.json"
    if not latest_nws.exists():
        latest_nws = latest_file(NWS_DIR, "nws_kmia_snapshot_*.json")
    latest_twc = TWC_DIR / "latest_twc_kmia_snapshot.json"
    if not latest_twc.exists():
        latest_twc = latest_file(TWC_DIR, "twc_kmia_snapshot_*.json")

    nws = load_json(latest_nws)
    twc = load_json(latest_twc)
    features = twc.get("derived_features", {}) if isinstance(twc, dict) else {}

    nws_forecast = normalize_rows(extract_nws_forecast(nws), "NWS", "Forecast")
    twc_forecast = normalize_rows([r for r in twc.get("hourly_forecast", []) if isinstance(r, dict)], "TWC", "Forecast") if isinstance(twc, dict) else pd.DataFrame()
    nws_observed = normalize_rows(extract_nws_observed(nws), "NWS", "Observed")
    twc_observed = normalize_twc_observed(twc)
    nws_daily = normalize_nws_daily(nws)
    twc_daily = normalize_twc_daily(twc)

    matched_forecast = build_hourly_match(nws_forecast, twc_forecast, tolerance, direction)
    matched_observed = build_observed_match(nws_observed, twc_observed, tolerance, direction)
    matched_daily = build_daily_match(nws_daily, twc_daily)

    c = st.columns(4)
    c[0].metric("NWS Observed Temp", f"{nws.get('current_temp_f', 'N/A')}F")
    c[1].metric("NWS Observed Max", f"{nws.get('observed_max_so_far_f', 'N/A')}F")
    c[2].metric("TWC Forecast High", f"{features.get('forecast_high_f', 'N/A')}F")
    c[3].metric("TWC Hourly Max", f"{features.get('hourly_max_temp_f', 'N/A')}F")
    s = st.columns(4)
    s[0].metric("NWS Status", provider_status(nws, "nws"))
    s[1].metric("TWC Status", provider_status(twc, "twc"))
    s[2].metric("Matched Forecast Intervals", len(matched_forecast))
    med = matched_forecast["Forecast Spread"].dropna().median() if not matched_forecast.empty and "Forecast Spread" in matched_forecast else None
    s[3].metric("Median Forecast Spread", f"{med:+.1f}F" if med is not None and pd.notna(med) else "N/A")
    st.caption(f"Snapshot files — NWS: {latest_nws.name if latest_nws else 'Missing'} | TWC: {latest_twc.name if latest_twc else 'Missing'}")
    st.caption(f"Snapshot age — NWS: {int(file_age_seconds(latest_nws) or 0)}s | TWC: {int(file_age_seconds(latest_twc) or 0)}s")

    st.subheader("Hourly Forecast Tables")
    tab1, tab2, tab3 = st.tabs(["Matched Hourly Forecast Interval Comparison", "NWS Hourly Forecast", "TWC Hourly Forecast"])
    with tab1:
        if matched_forecast.empty:
            st.warning("No matched NWS/TWC forecast intervals found. Check that NWS and TWC hourly forecast rows are present.")
        else:
            cols = ["Time ET"]
            if "temperature" in groups:
                cols += ["NWS Forecast F", "TWC Forecast F", "Forecast Spread"]
            if "humidity" in groups:
                cols += ["NWS Dewpoint F", "TWC Dewpoint F", "NWS RH %", "TWC RH %"]
            if "wind" in groups:
                cols += ["NWS Wind", "TWC Wind", "NWS Wind mph", "TWC Wind mph"]
            if "source_text" in groups:
                cols += ["NWS Phrase", "TWC Phrase"]
            st.dataframe(matched_forecast[[col for col in cols if col in matched_forecast.columns]], width="stretch", hide_index=True)
    with tab2:
        st.dataframe(display_df(nws_forecast, "NWS", 72), width="stretch", hide_index=True)
    with tab3:
        st.dataframe(display_df(twc_forecast, "TWC", 72), width="stretch", hide_index=True)

    st.subheader("Observed Tables")
    tab4, tab5, tab6 = st.tabs(["Matched Hourly Observed Interval Comparison", "NWS Observed", "TWC Observed"])
    with tab4:
        if matched_observed.empty:
            st.warning("No matched observed intervals yet. This requires both NWS observed rows and TWC current-condition rows.")
        else:
            st.dataframe(matched_observed, width="stretch", hide_index=True)
    with tab5:
        st.dataframe(display_df(nws_observed.sort_values("time_utc", ascending=False) if not nws_observed.empty else nws_observed, "NWS", 48), width="stretch", hide_index=True)
    with tab6:
        if twc_observed.empty:
            status = twc.get("endpoint_status", {}).get("current_conditions", {}) if isinstance(twc, dict) else {}
            st.warning("No TWC observed/current-condition rows are available.")
            if status:
                st.json(status)
        else:
            st.dataframe(display_df(twc_observed.sort_values("time_utc", ascending=False), "TWC", 48), width="stretch", hide_index=True)

    st.subheader("Daily Forecast Summary")
    tab7, tab8, tab9 = st.tabs(["Matched Daily Forecast Comparison", "NWS Daily Forecast", "TWC Daily Forecast"])
    with tab7:
        if matched_daily.empty:
            st.warning("No matched daily forecast rows found yet.")
        else:
            st.dataframe(matched_daily, width="stretch", hide_index=True)
    with tab8:
        if nws_daily.empty:
            st.warning("No NWS daily forecast rows found.")
        else:
            st.dataframe(nws_daily[[c for c in DAILY_COLUMNS if c in nws_daily.columns]], width="stretch", hide_index=True)
    with tab9:
        if twc_daily.empty:
            st.warning("No TWC daily forecast rows found.")
        else:
            st.dataframe(twc_daily[[c for c in DAILY_COLUMNS if c in twc_daily.columns]], width="stretch", hide_index=True)

    if show_raw:
        st.subheader("Raw Provider Snapshots")
        raw1, raw2 = st.tabs(["NWS Raw JSON", "TWC Raw JSON"])
        with raw1:
            st.json(nws)
        with raw2:
            st.json(twc)


if __name__ == "__main__":
    main()

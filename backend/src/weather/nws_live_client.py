import json
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dateutil import tz

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

USER_AGENT = "KMIA-Kalshi-Bot/1.0 (https://github.com/PeterJFrancoIII/Kalshi_Temp_Trader)"
OBHISTORY_URL = "https://www.weather.gov/data/obhistory/KMIA.html"
ET_TZ = tz.gettz("America/New_York")

try:
    from ingestion.kmia_obhistory_parser import ParsedObservation, parse_obhistory
except ImportError:  # pragma: no cover - keeps direct script execution robust in unusual PYTHONPATHs
    ParsedObservation = None

    def parse_obhistory(raw_html: str, reference_datetime: Optional[datetime] = None):
        return [], ["ObHistory parser unavailable"]


def c_to_f(c: Optional[float]) -> Optional[float]:
    if c is None:
        return None
    return round((c * 9 / 5) + 32, 1)


def pa_to_mb(pa: Optional[float]) -> Optional[float]:
    if pa is None:
        return None
    return round(pa * 0.01, 2)


def m_to_in(m: Optional[float]) -> Optional[float]:
    if m is None:
        return None
    return round(m * 39.3701, 2)


def get_et_now() -> datetime:
    return datetime.now(ET_TZ)


def to_et(ts_str: str) -> datetime:
    if ts_str.endswith("Z"):
        ts_str = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_str)
    return dt.astimezone(ET_TZ)


def degrees_to_compass(degrees: Optional[float]) -> str:
    if degrees is None:
        return ""
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((degrees + 11.25) / 22.5) % 16
    return points[idx]


def convert_nws_wind_to_mph(value_obj: Dict[str, Any]) -> Optional[float]:
    val = value_obj.get("value")
    if val is None:
        return None
    unit = value_obj.get("unitCode", "")

    if "m_s-1" in unit:
        return round(val * 2.23694, 1)
    if "km_h-1" in unit:
        return round(val * 0.621371, 1)
    if "mi_h-1" in unit:
        return round(val, 1)
    return round(val, 1)


def parse_nws_cloud_layers(layers: Optional[List[Dict[str, Any]]]) -> str:
    if not layers:
        return ""

    parts = []
    for layer in layers:
        amount = layer.get("amount", "")
        base_obj = layer.get("base", {})
        val = base_obj.get("value")
        unit = base_obj.get("unitCode", "")

        if val is None:
            if amount:
                parts.append(amount)
            continue

        feet = val
        if "wmoUnit:m" in unit:
            feet = val * 3.28084

        x100ft = int(round(feet / 100))
        parts.append(f"{amount}{x100ft:03d}")

    return " ".join(parts)


def fetch_kmia_point_metadata() -> Dict[str, Any]:
    url = "https://api.weather.gov/points/25.7959,-80.2870"
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def fetch_kmia_forecast(forecast_url: str) -> Dict[str, Any]:
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(forecast_url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def fetch_kmia_hourly_forecast(hourly_url: str) -> Dict[str, Any]:
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(hourly_url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def fetch_latest_kmia_observation() -> Dict[str, Any]:
    url = "https://api.weather.gov/stations/KMIA/observations/latest"
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def fetch_recent_kmia_observations(limit: int = 100) -> List[Dict[str, Any]]:
    url = f"https://api.weather.gov/stations/KMIA/observations?limit={limit}"
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("features", [])
    except Exception:
        return []


def fetch_kmia_obhistory_html() -> Optional[str]:
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(OBHISTORY_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def _feature_to_row(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    p = feature.get("properties", {})
    ts_utc = p.get("timestamp")
    if not ts_utc:
        return None

    dt_et = to_et(ts_utc)
    return {
        "timestamp_utc": ts_utc,
        "date_et": dt_et.strftime("%Y-%m-%d"),
        "time_et": dt_et.strftime("%I:%M %p ET").lstrip("0"),
        "temperature_f": c_to_f(p.get("temperature", {}).get("value")),
        "dewpoint_f": c_to_f(p.get("dewpoint", {}).get("value")),
        "relative_humidity_pct": round(p.get("relativeHumidity", {}).get("value"), 1)
        if p.get("relativeHumidity", {}).get("value") is not None else None,
        "wind_direction_degrees": p.get("windDirection", {}).get("value"),
        "wind_direction_compass": degrees_to_compass(p.get("windDirection", {}).get("value")),
        "wind_speed_mph": convert_nws_wind_to_mph(p.get("windSpeed", {})),
        "wind_gust_mph": convert_nws_wind_to_mph(p.get("windGust", {})),
        "sea_level_pressure_mb": pa_to_mb(p.get("seaLevelPressure", {}).get("value")),
        "barometric_pressure_mb": pa_to_mb(p.get("barometricPressure", {}).get("value")),
        "precipitation_last_hour_in": m_to_in(p.get("precipitationLastHour", {}).get("value")),
        "clouds_x100ft": parse_nws_cloud_layers(p.get("cloudLayers")),
        "text_description": p.get("textDescription"),
        "raw_message": p.get("rawMessage"),
        "source": "api.weather.gov",
    }


def _obhistory_obs_to_row(obs: Any) -> Optional[Dict[str, Any]]:
    ts = getattr(obs, "timestamp", None)
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ET_TZ)
    dt_et = ts.astimezone(ET_TZ)
    ts_utc = dt_et.astimezone(timezone.utc).isoformat()

    wind_direction = getattr(obs, "wind_direction", None)
    return {
        "timestamp_utc": ts_utc,
        "date_et": dt_et.strftime("%Y-%m-%d"),
        "time_et": dt_et.strftime("%I:%M %p ET").lstrip("0"),
        "temperature_f": getattr(obs, "temperature_f", None),
        "dewpoint_f": getattr(obs, "dewpoint_f", None),
        "relative_humidity_pct": getattr(obs, "humidity", None),
        "wind_direction_degrees": wind_direction,
        "wind_direction_compass": degrees_to_compass(wind_direction),
        "wind_speed_mph": getattr(obs, "wind_speed_mph", None),
        "wind_gust_mph": getattr(obs, "wind_gust_mph", None),
        "sea_level_pressure_mb": None,
        "barometric_pressure_mb": None,
        "pressure_in": getattr(obs, "pressure_in", None),
        "precipitation_last_hour_in": getattr(obs, "precipitation_in", None),
        "clouds_x100ft": getattr(obs, "sky_condition", None),
        "text_description": getattr(obs, "weather_condition", None),
        "raw_message": getattr(obs, "raw_metar", None),
        "source": "weather.gov_obhistory",
    }


def _rows_from_api_features(features: List[Dict[str, Any]], warnings: List[str]) -> List[Dict[str, Any]]:
    rows = []
    for feature in features:
        try:
            row = _feature_to_row(feature)
            if row:
                rows.append(row)
        except Exception as exc:
            warnings.append(f"API observation row parse error: {exc}")
    return rows


def _rows_from_obhistory(reference_datetime: Optional[datetime], warnings: List[str]) -> List[Dict[str, Any]]:
    raw_html = fetch_kmia_obhistory_html()
    if not raw_html:
        warnings.append("Could not fetch NWS ObHistory fallback HTML.")
        return []

    observations, parse_warnings = parse_obhistory(raw_html, reference_datetime=reference_datetime)
    warnings.extend(parse_warnings)
    rows = []
    for obs in observations:
        try:
            row = _obhistory_obs_to_row(obs)
            if row:
                rows.append(row)
        except Exception as exc:
            warnings.append(f"ObHistory row parse error: {exc}")

    rows.sort(key=lambda r: r["timestamp_utc"], reverse=True)
    return rows


def _update_summary_from_rows(snapshot: Dict[str, Any], table_rows: List[Dict[str, Any]]) -> None:
    snapshot["recent_observations_table"] = table_rows
    snapshot["recent_observations_count"] = len(table_rows)

    et_today = get_et_now().date()
    temps_et_today = []
    for row in table_rows:
        try:
            dt_et = to_et(row["timestamp_utc"])
            if dt_et.date() == et_today and row.get("temperature_f") is not None:
                temps_et_today.append(row["temperature_f"])
        except Exception:
            continue

    if temps_et_today:
        snapshot["observed_max_so_far_f"] = max(temps_et_today)

    if not table_rows:
        return

    latest = table_rows[0]
    snapshot["latest_observation_time"] = latest.get("timestamp_utc")
    snapshot["current_temp_f"] = latest.get("temperature_f")
    snapshot["dewpoint_f"] = latest.get("dewpoint_f")
    snapshot["wind_speed_mph"] = latest.get("wind_speed_mph")
    snapshot["wind_gust_mph"] = latest.get("wind_gust_mph")
    snapshot["wind_direction_degrees"] = latest.get("wind_direction_degrees")
    snapshot["wind_direction_compass"] = latest.get("wind_direction_compass")
    snapshot["clouds_x100ft"] = latest.get("clouds_x100ft")

    try:
        obs_time = datetime.fromisoformat(latest["timestamp_utc"].replace("Z", "+00:00"))
        snapshot["stale_data"] = (datetime.now(timezone.utc) - obs_time) > timedelta(minutes=90)
    except Exception:
        snapshot["warnings"].append("Failed to parse latest observation timestamp.")


def build_live_nws_snapshot() -> Dict[str, Any]:
    snapshot = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "station": "KMIA",
        "source": "api.weather.gov",
        "observation_source": None,
        "timeseries_source_url": "https://www.weather.gov/wrh/timeseries?site=kmia",
        "api_observations_url": "https://api.weather.gov/stations/KMIA/observations",
        "obhistory_source_url": OBHISTORY_URL,
        "latest_observation_time": None,
        "current_temp_f": None,
        "dewpoint_f": None,
        "wind_speed_mph": None,
        "wind_gust_mph": None,
        "wind_direction_degrees": None,
        "wind_direction_compass": None,
        "clouds_x100ft": None,
        "observed_max_so_far_f": None,
        "forecast_high_f": None,
        "hourly_forecast_summary": None,
        "recent_observations_table": [],
        "recent_observations_count": 0,
        "stale_data": True,
        "endpoint_status": "OK",
        "warnings": [],
        "safety": {"no_real_trading": True},
    }

    meta = fetch_kmia_point_metadata()
    if not meta:
        snapshot["warnings"].append("Could not fetch point metadata.")

    props = meta.get("properties", {})
    forecast_url = props.get("forecast")
    hourly_url = props.get("forecastHourly")

    recent_features = fetch_recent_kmia_observations(limit=100)
    table_rows = _rows_from_api_features(recent_features, snapshot["warnings"])
    if table_rows:
        snapshot["observation_source"] = "api.weather.gov"
    else:
        snapshot["warnings"].append("No parsed API observation rows found; trying NWS ObHistory fallback.")
        table_rows = _rows_from_obhistory(get_et_now(), snapshot["warnings"])
        if table_rows:
            snapshot["observation_source"] = "weather.gov_obhistory"
            snapshot["source"] = "weather.gov_obhistory_fallback"

    _update_summary_from_rows(snapshot, table_rows)

    if not table_rows:
        snapshot["endpoint_status"] = "ERROR"
        snapshot["warnings"].append("No live observation rows found via API or ObHistory fallback.")
    elif not meta:
        snapshot["endpoint_status"] = "PARTIAL"
        snapshot["warnings"].append("Forecast metadata unavailable; live observations came from fallback/API observations path.")

    if forecast_url:
        f_data = fetch_kmia_forecast(forecast_url)
        periods = f_data.get("properties", {}).get("periods", [])
        for period in periods:
            if period.get("isDaytime"):
                snapshot["forecast_high_f"] = period.get("temperature")
                break

    if hourly_url:
        h_data = fetch_kmia_hourly_forecast(hourly_url)
        h_periods = h_data.get("properties", {}).get("periods", [])
        if h_periods:
            next_3 = h_periods[:3]
            summaries = [f"{p.get('startTime')[11:16]}: {p.get('temperature')}F {p.get('shortForecast')}" for p in next_3]
            snapshot["hourly_forecast_summary"] = " | ".join(summaries)

    return snapshot


if __name__ == "__main__":
    snap = build_live_nws_snapshot()
    print(json.dumps(snap, indent=2))

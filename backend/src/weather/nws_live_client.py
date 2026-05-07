import json
import requests
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from dateutil import tz

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

USER_AGENT = "KMIA-Kalshi-Bot/1.0 (https://github.com/PeterJFrancoIII/Kalshi_Temp_Trader)"

def c_to_f(c: Optional[float]) -> Optional[float]:
    if c is None:
        return None
    return round((c * 9/5) + 32, 1)

def pa_to_mb(pa: Optional[float]) -> Optional[float]:
    if pa is None:
        return None
    return round(pa * 0.01, 2)

def m_to_in(m: Optional[float]) -> Optional[float]:
    if m is None:
        return None
    return round(m * 39.3701, 2)

def get_et_now() -> datetime:
    return datetime.now(tz.gettz('America/New_York'))

def to_et(ts_str: str) -> datetime:
    if ts_str.endswith("Z"):
        ts_str = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_str)
    return dt.astimezone(tz.gettz('America/New_York'))

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

def parse_forecast_wind_speed_mph(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    # NWS often returns strings such as "10 mph", "5 to 10 mph", or "10 mph with gusts as high as 20 mph".
    import re
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", value)]
    if not nums:
        return None
    return round(sum(nums[:2]) / min(len(nums), 2), 1)

def parse_probability_percent(value_obj: Any) -> Optional[float]:
    if isinstance(value_obj, dict):
        val = value_obj.get("value")
        return round(val, 1) if isinstance(val, (int, float)) else None
    if isinstance(value_obj, (int, float)):
        return round(value_obj, 1)
    return None

def normalize_nws_hourly_period(period: Dict[str, Any]) -> Dict[str, Any]:
    start = period.get("startTime")
    end = period.get("endTime")
    try:
        dt_et = to_et(start) if start else None
        date_et = dt_et.strftime("%Y-%m-%d") if dt_et else None
        time_et = dt_et.strftime("%I:%M %p ET").lstrip("0") if dt_et else None
    except Exception:
        date_et = None
        time_et = None
    wind_dir = period.get("windDirection")
    return {
        "timestamp_utc": start,
        "valid_time_utc": start,
        "end_time_utc": end,
        "date_et": date_et,
        "time_et": time_et,
        "temperature_f": period.get("temperature"),
        "dewpoint_f": c_to_f((period.get("dewpoint") or {}).get("value")) if isinstance(period.get("dewpoint"), dict) else None,
        "relative_humidity_pct": parse_probability_percent(period.get("relativeHumidity")),
        "wind_direction_degrees": None,
        "wind_direction_compass": wind_dir,
        "wind_speed_mph": parse_forecast_wind_speed_mph(period.get("windSpeed")),
        "wind_gust_mph": None,
        "precip_probability_pct": parse_probability_percent(period.get("probabilityOfPrecipitation")),
        "shortForecast": period.get("shortForecast"),
        "detailedForecast": period.get("detailedForecast"),
        "raw_message": period.get("shortForecast"),
        "isDaytime": period.get("isDaytime"),
        "period_number": period.get("number"),
    }

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

def build_live_nws_snapshot() -> Dict[str, Any]:
    snapshot = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "station": "KMIA",
        "source": "api.weather.gov",
        "timeseries_source_url": "https://www.weather.gov/wrh/timeseries?site=kmia",
        "api_observations_url": "https://api.weather.gov/stations/KMIA/observations",
        "api_hourly_forecast_url": None,
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
        "hourly_forecast": [],
        "hourly_forecast_count": 0,
        "recent_observations_table": [],
        "recent_observations_count": 0,
        "stale_data": True,
        "endpoint_status": "OK",
        "warnings": [],
        "safety": {"no_real_trading": True}
    }

    meta = fetch_kmia_point_metadata()
    if not meta:
        snapshot["endpoint_status"] = "ERROR"
        snapshot["warnings"].append("Could not fetch point metadata.")

    props = meta.get("properties", {})
    forecast_url = props.get("forecast")
    hourly_url = props.get("forecastHourly")
    snapshot["api_hourly_forecast_url"] = hourly_url

    recent_feats = fetch_recent_kmia_observations(limit=100)
    snapshot["recent_observations_count"] = len(recent_feats)
    table_rows = []
    et_today = get_et_now().date()
    temps_et_today = []

    for feat in recent_feats:
        p = feat.get("properties", {})
        ts_utc = p.get("timestamp")
        if not ts_utc:
            continue
        try:
            dt_et = to_et(ts_utc)
            row = {
                "timestamp_utc": ts_utc,
                "date_et": dt_et.strftime("%Y-%m-%d"),
                "time_et": dt_et.strftime("%I:%M %p ET").lstrip("0"),
                "temperature_f": c_to_f(p.get("temperature", {}).get("value")),
                "dewpoint_f": c_to_f(p.get("dewpoint", {}).get("value")),
                "relative_humidity_pct": round(p.get("relativeHumidity", {}).get("value"), 1) if p.get("relativeHumidity", {}).get("value") is not None else None,
                "wind_direction_degrees": p.get("windDirection", {}).get("value"),
                "wind_direction_compass": degrees_to_compass(p.get("windDirection", {}).get("value")),
                "wind_speed_mph": convert_nws_wind_to_mph(p.get("windSpeed", {})),
                "wind_gust_mph": convert_nws_wind_to_mph(p.get("windGust", {})),
                "sea_level_pressure_mb": pa_to_mb(p.get("seaLevelPressure", {}).get("value")),
                "barometric_pressure_mb": pa_to_mb(p.get("barometricPressure", {}).get("value")),
                "precipitation_last_hour_in": m_to_in(p.get("precipitationLastHour", {}).get("value")),
                "clouds_x100ft": parse_nws_cloud_layers(p.get("cloudLayers")),
                "text_description": p.get("textDescription"),
                "raw_message": p.get("rawMessage")
            }
            table_rows.append(row)
            if dt_et.date() == et_today and row["temperature_f"] is not None:
                temps_et_today.append(row["temperature_f"])
        except Exception as e:
            snapshot["warnings"].append(f"Row parse error: {str(e)}")

    snapshot["recent_observations_table"] = table_rows
    if temps_et_today:
        snapshot["observed_max_so_far_f"] = max(temps_et_today)

    if table_rows:
        latest = table_rows[0]
        snapshot["latest_observation_time"] = latest["timestamp_utc"]
        snapshot["current_temp_f"] = latest["temperature_f"]
        snapshot["dewpoint_f"] = latest["dewpoint_f"]
        snapshot["wind_speed_mph"] = latest["wind_speed_mph"]
        snapshot["wind_gust_mph"] = latest["wind_gust_mph"]
        snapshot["wind_direction_degrees"] = latest["wind_direction_degrees"]
        snapshot["wind_direction_compass"] = latest["wind_direction_compass"]
        snapshot["clouds_x100ft"] = latest["clouds_x100ft"]
        try:
            obs_time = datetime.fromisoformat(latest["timestamp_utc"].replace("Z", "+00:00"))
            snapshot["stale_data"] = (datetime.now(timezone.utc) - obs_time) > timedelta(minutes=90)
        except Exception:
            snapshot["warnings"].append("Failed to parse latest observation timestamp.")

    if forecast_url:
        f_data = fetch_kmia_forecast(forecast_url)
        periods = f_data.get("properties", {}).get("periods", [])
        for p in periods:
            if p.get("isDaytime"):
                snapshot["forecast_high_f"] = p.get("temperature")
                break

    if hourly_url:
        h_data = fetch_kmia_hourly_forecast(hourly_url)
        h_periods = h_data.get("properties", {}).get("periods", [])
        snapshot["hourly_forecast"] = [normalize_nws_hourly_period(p) for p in h_periods]
        snapshot["hourly_forecast_count"] = len(snapshot["hourly_forecast"])
        if h_periods:
            next_3 = h_periods[:3]
            summaries = [f"{p.get('startTime')[11:16]}: {p.get('temperature')}F {p.get('shortForecast')}" for p in next_3 if p.get("startTime")]
            snapshot["hourly_forecast_summary"] = " | ".join(summaries)
        else:
            snapshot["warnings"].append("No NWS hourly forecast periods returned.")

    return snapshot

if __name__ == "__main__":
    snap = build_live_nws_snapshot()
    print(json.dumps(snap, indent=2))

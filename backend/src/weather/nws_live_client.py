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
    # Handle Z or +00:00
    if ts_str.endswith("Z"):
        ts_str = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_str)
    return dt.astimezone(tz.gettz('America/New_York'))

def degrees_to_compass(degrees: Optional[float]) -> str:
    if degrees is None:
        return ""
    # 16-point compass
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
    elif "km_h-1" in unit:
        return round(val * 0.621371, 1)
    elif "mi_h-1" in unit:
        return round(val, 1)
    
    # Default to mph if unknown but likely mi/h, or just return as is
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
            
        # Convert to feet
        feet = val
        if "wmoUnit:m" in unit:
            feet = val * 3.28084
            
        x100ft = int(round(feet / 100))
        # Format: FEW025 (amount + 3-digit x100ft)
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

def build_live_nws_snapshot() -> Dict[str, Any]:
    snapshot = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "station": "KMIA",
        "source": "api.weather.gov",
        "timeseries_source_url": "https://www.weather.gov/wrh/timeseries?site=kmia",
        "api_observations_url": "https://api.weather.gov/stations/KMIA/observations",
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
        "safety": {
            "no_real_trading": True
        }
    }

    # 1. Metadata
    meta = fetch_kmia_point_metadata()
    if not meta:
        snapshot["endpoint_status"] = "ERROR"
        snapshot["warnings"].append("Could not fetch point metadata.")
    
    props = meta.get("properties", {})
    forecast_url = props.get("forecast")
    hourly_url = props.get("forecastHourly")

    # 2. Recent Observations & Table
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
            date_et_str = dt_et.strftime("%Y-%m-%d")
            # 7:53 PM ET format
            time_et_str = dt_et.strftime("%I:%M %p ET").lstrip("0")
            
            row = {
                "timestamp_utc": ts_utc,
                "date_et": date_et_str,
                "time_et": time_et_str,
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

            # Max Temp Tracking for ET Today
            if dt_et.date() == et_today:
                if row["temperature_f"] is not None:
                    temps_et_today.append(row["temperature_f"])
        except Exception as e:
            snapshot["warnings"].append(f"Row parse error: {str(e)}")

    snapshot["recent_observations_table"] = table_rows
    
    if temps_et_today:
        snapshot["observed_max_so_far_f"] = max(temps_et_today)

    # 3. Latest Observation Summary (from table)
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

        # Staleness Check
        try:
            obs_time = datetime.fromisoformat(latest["timestamp_utc"].replace("Z", "+00:00"))
            time_diff = datetime.now(timezone.utc) - obs_time
            snapshot["stale_data"] = time_diff > timedelta(minutes=90)
        except:
            snapshot["warnings"].append("Failed to parse latest observation timestamp.")

    # 4. Forecast
    if forecast_url:
        f_data = fetch_kmia_forecast(forecast_url)
        periods = f_data.get("properties", {}).get("periods", [])
        for p in periods:
            if p.get("isDaytime"):
                snapshot["forecast_high_f"] = p.get("temperature")
                break
    
    # 5. Hourly Summary
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

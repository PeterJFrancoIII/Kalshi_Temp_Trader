import json
import requests
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

USER_AGENT = "KMIA-Kalshi-Bot/1.0 (https://github.com/PeterJFrancoIII/Kalshi_Temp_Trader)"

def c_to_f(c: Optional[float]) -> Optional[float]:
    if c is None:
        return None
    return round((c * 9/5) + 32, 1)

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

def fetch_recent_kmia_observations_today() -> List[Dict[str, Any]]:
    url = "https://api.weather.gov/stations/KMIA/observations"
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
        "latest_observation_time": None,
        "current_temp_f": None,
        "dewpoint_f": None,
        "wind_speed_mph": None,
        "wind_direction_degrees": None,
        "observed_max_so_far_f": None,
        "forecast_high_f": None,
        "hourly_forecast_summary": None,
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

    # 2. Latest Observation
    obs = fetch_latest_kmia_observation()
    if obs:
        o_props = obs.get("properties", {})
        ts_str = o_props.get("timestamp")
        snapshot["latest_observation_time"] = ts_str
        snapshot["current_temp_f"] = c_to_f(o_props.get("temperature", {}).get("value"))
        snapshot["dewpoint_f"] = c_to_f(o_props.get("dewpoint", {}).get("value"))
        
        # Wind
        ws = o_props.get("windSpeed", {}).get("value")
        if ws is not None:
            snapshot["wind_speed_mph"] = round(ws * 0.621371, 1) # km/h to mph
        snapshot["wind_direction_degrees"] = o_props.get("windDirection", {}).get("value")

        if ts_str:
            try:
                obs_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                time_diff = datetime.now(timezone.utc) - obs_time
                snapshot["stale_data"] = time_diff > timedelta(minutes=90)
            except:
                snapshot["warnings"].append("Failed to parse observation timestamp.")

    # 3. Observed Max So Far Today
    recent = fetch_recent_kmia_observations_today()
    if recent:
        today = datetime.now(timezone.utc).date()
        temps_today = []
        for feat in recent:
            f_props = feat.get("properties", {})
            f_ts_str = f_props.get("timestamp")
            if f_ts_str:
                f_ts = datetime.fromisoformat(f_ts_str.replace("Z", "+00:00"))
                if f_ts.date() == today:
                    val = f_props.get("temperature", {}).get("value")
                    if val is not None:
                        temps_today.append(c_to_f(val))
        if temps_today:
            snapshot["observed_max_so_far_f"] = max(temps_today)

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

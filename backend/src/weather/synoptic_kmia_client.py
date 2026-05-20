"""Read-only Synoptic API ingestion for KMIA weather observations.

KMIA remains the settlement/verification target. This client pulls Synoptic
point observations data into a normalized local snapshot.
"""

import json
import os
import sys
import time
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
from dateutil import tz


# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

STATION = "KMIA"
LATITUDE = 25.79586
LONGITUDE = -80.29011


def get_synoptic_token() -> Optional[str]:
    """Retrieve API token from environment variables."""
    return os.getenv("SYNOPTIC_TOKEN") or os.getenv("SYNOPTIC_API_TOKEN")


def build_unavailable_snapshot(status: str, warning_msg: str) -> Dict[str, Any]:
    """Construct a structured unavailable snapshot payload."""
    warnings = [warning_msg] if warning_msg else []
    return {
        "provider": "synoptic",
        "station": STATION,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest_observation_time": None,
        "observation_time_utc": None,
        "current_temp_f": None,
        "dew_point_f": None,
        "raw_temp_c": None,
        "raw_dewpoint_c": None,
        "observed_max_so_far_f": None,
        "recent_window_max_temp_f": None,
        "recent_observations_table": [],
        "endpoint_status": status,
        "stale_data": True,
        "warnings": warnings,
        "raw_response_path": None,
        "source_product": "synoptic_timeseries",
        "underlying_feed": "ASOS/METAR-derived station timeseries",
        "raw_sensor_feed": False,
        "thirty_second_temperature_feed": False,
        "feed_label": "synoptic_kmia_feed",
        "cadence_observed_minutes": None,
        "latency_minutes": None,
        "temporal_resolution_claim": "1-minute/HF-ASOS",
        "endpoint_metadata": {
            "station_id": STATION,
            "mnet_id": None,
            "network_name": "ASOS/AWOS",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "elevation_ft": 10.0
        },
        "qc_summary": None,
        "safety": {
            "no_real_trading": True,
            "no_order_execution": True
        }
    }


def format_et(ts_utc_str: str) -> str:
    """Format UTC ISO string to America/New_York local time string."""
    try:
        dt = datetime.fromisoformat(ts_utc_str.replace("Z", "+00:00"))
        tz_et = tz.gettz("America/New_York")
        dt_et = dt.astimezone(tz_et)
        return dt_et.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "N/A"



def format_iso_utc(ts_str: str) -> str:
    """Format and return a canonical UTC ISO string from the API timestamp."""
    cleaned = ts_str
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return ts_str


def fetch_synoptic_observations(recent_minutes: int = 1440, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Fetch recent observations from Synoptic API and normalize."""
    from shared.artifact_paths import WEATHER_SYNOPTIC_DIR
    output_dir = output_dir or WEATHER_SYNOPTIC_DIR

    api_token = get_synoptic_token()
    if not api_token:
        return build_unavailable_snapshot("MISSING_CREDENTIALS", "Synoptic API token not set in environment (SYNOPTIC_TOKEN or SYNOPTIC_API_TOKEN).")

    url = "https://api.synopticdata.com/v2/stations/timeseries"
    params = {
        "token": api_token,
        "stid": STATION,
        "recent": recent_minutes,
        "units": "english",
        "qc": "on",
        "qc_flags": "on",
        "vars": "air_temp,wind_speed,wind_direction,relative_humidity,pressure,altimeter,dew_point_temperature"
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 401:
            return build_unavailable_snapshot("ERROR", f"Synoptic API returned 401: {resp.text}")
        resp.raise_for_status()
        raw_data = resp.json()

        # Check for response status in SUMMARY
        summary = raw_data.get("SUMMARY", {})
        response_code = summary.get("RESPONSE_CODE")
        if response_code != 1:
            msg = summary.get("RESPONSE_MESSAGE", "Unknown API error")
            return build_unavailable_snapshot("ERROR", f"Synoptic API error response (code {response_code}): {msg}")

        # Archive raw response
        ts = int(time.time())
        archive_dir = output_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"raw_synoptic_kmia_{ts}.json"
        with open(archive_path, "w") as f:
            json.dump(raw_data, f, indent=2)

        # Parse response
        parsed = parse_synoptic_response(raw_data)
        parsed["raw_response_path"] = str(archive_path)
        return parsed

    except requests.exceptions.Timeout:
        return build_unavailable_snapshot("ERROR", "Synoptic API request timed out.")
    except requests.exceptions.RequestException as e:
        return build_unavailable_snapshot("ERROR", f"Synoptic API request failed: {str(e)}")
    except json.JSONDecodeError:
        return build_unavailable_snapshot("ERROR", "Synoptic API returned invalid JSON.")


def parse_synoptic_response(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse raw Synoptic API JSON to normalized structure."""
    station_list = raw_data.get("STATION") or raw_data.get("STATIONS")
    if not station_list:
        return build_unavailable_snapshot("NO_DATA", "Synoptic API response contained no station data.")

    station = station_list[0]
    obs = station.get("OBSERVATIONS", {})
    date_time_list = obs.get("date_time", [])
    if not date_time_list:
        return build_unavailable_snapshot("NO_DATA", "Synoptic API response contained no observation data.")

    # Identify sets of sensors
    def find_set(prefix: str) -> Optional[List[Any]]:
        for k, v in obs.items():
            if k.startswith(prefix) and isinstance(v, list):
                return v
        return None

    air_temp_list = find_set("air_temp_set_")
    dew_point_list = find_set("dew_point_temperature_set_")
    wind_speed_list = find_set("wind_speed_set_")
    wind_direction_list = find_set("wind_direction_set_")
    relative_humidity_list = find_set("relative_humidity_set_")
    pressure_list = find_set("pressure_set_") or find_set("altimeter_set_")

    qc_data = station.get("QC", {})

    recent_observations_table = []
    for i in range(len(date_time_list)):
        t_utc = format_iso_utc(date_time_list[i])

        # Extract QC for this observation row
        qc_row = {}
        if qc_data:
            for var_key, qc_list in qc_data.items():
                if isinstance(qc_list, list) and i < len(qc_list):
                    val = qc_list[i]
                    if val is not None:
                        qc_row[var_key] = val

        temp_f = air_temp_list[i] if air_temp_list and i < len(air_temp_list) else None
        dp_f = dew_point_list[i] if dew_point_list and i < len(dew_point_list) else None

        temp_c = round((temp_f - 32) * 5.0 / 9.0, 2) if temp_f is not None else None
        dp_c = round((dp_f - 32) * 5.0 / 9.0, 2) if dp_f is not None else None

        row = {
            "time_utc": t_utc,
            "time_et": format_et(t_utc) if t_utc else "N/A",
            "air_temp_f": temp_f,
            "dew_point_f": dp_f,
            "raw_temp_c": temp_c,
            "raw_dewpoint_c": dp_c,
            "wind_speed_mph": wind_speed_list[i] if wind_speed_list and i < len(wind_speed_list) else None,
            "wind_direction_deg": wind_direction_list[i] if wind_direction_list and i < len(wind_direction_list) else None,
            "relative_humidity_pct": relative_humidity_list[i] if relative_humidity_list and i < len(relative_humidity_list) else None,
            "pressure": pressure_list[i] if pressure_list and i < len(pressure_list) else None,
            "qc_flags": qc_row if qc_row else None
        }
        recent_observations_table.append(row)

    # Calculate latest observation details
    latest_obs_time = recent_observations_table[-1]["time_utc"] if recent_observations_table else None
    current_temp = recent_observations_table[-1]["air_temp_f"] if recent_observations_table else None

    # Calculate observed max so far today in ET
    tz_et = tz.gettz("America/New_York")
    today_et = datetime.now(tz_et).date()

    today_temps = []
    recent_window_temps = []

    for row in recent_observations_table:
        temp = row["air_temp_f"]
        if temp is None:
            continue
        recent_window_temps.append(temp)
        try:
            dt_utc = datetime.fromisoformat(row["time_utc"].replace("Z", "+00:00"))
            dt_et = dt_utc.astimezone(tz_et)
            if dt_et.date() == today_et:
                today_temps.append(temp)
        except Exception:
            pass

    observed_max = max(today_temps) if today_temps else None
    recent_window_max = max(recent_window_temps) if recent_window_temps else None

    fetched_time_str = datetime.now(timezone.utc).isoformat()
    stale_data = True
    if latest_obs_time:
        try:
            dt_fetched = datetime.fromisoformat(fetched_time_str.replace("Z", "+00:00"))
            dt_latest = datetime.fromisoformat(latest_obs_time.replace("Z", "+00:00"))
            # Stale if older than 30 minutes (1800 seconds)
            if (dt_fetched - dt_latest).total_seconds() <= 1800:
                stale_data = False
        except Exception:
            pass

    # Calculate cadence_observed_minutes
    cadence = None
    if recent_observations_table:
        try:
            # Sort unique observation times ascending
            obs_times = sorted(list(set(
                datetime.fromisoformat(row["time_utc"].replace("Z", "+00:00"))
                for row in recent_observations_table if row.get("time_utc")
            )))
            if len(obs_times) > 1:
                deltas = [(obs_times[j] - obs_times[j-1]).total_seconds() / 60.0 for j in range(1, len(obs_times))]
                if deltas:
                    cadence = round(statistics.median(deltas), 1)
        except Exception:
            pass

    # Calculate latency_minutes
    latency = None
    if latest_obs_time:
        try:
            dt_latest = datetime.fromisoformat(latest_obs_time.replace("Z", "+00:00"))
            dt_fetched = datetime.fromisoformat(fetched_time_str.replace("Z", "+00:00"))
            latency = round((dt_fetched - dt_latest).total_seconds() / 60.0, 1)
        except Exception:
            pass

    # Build QC Summary
    qc_summary = None
    if "QC_SUMMARY" in raw_data:
        qcs = raw_data["QC_SUMMARY"]
        qc_summary = {
            "qc_checks_applied": qcs.get("QC_CHECKS_APPLIED", []),
            "total_observations_flagged": qcs.get("TOTAL_OBSERVATIONS_FLAGGED", 0),
            "percent_of_total_observations_flagged": qcs.get("PERCENT_OF_TOTAL_OBSERVATIONS_FLAGGED", 0.0),
        }

    # Build Endpoint Metadata
    endpoint_metadata = {
        "station_id": STATION,
        "mnet_id": station.get("MNET_ID"),
        "network_name": "ASOS/AWOS" if station.get("MNET_ID") == "1" else "Unknown",
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "elevation_ft": float(station.get("ELEVATION", 10.0)) if station.get("ELEVATION") else 10.0,
    }

    # Store newest-first per Objective 7
    recent_observations_table.reverse()

    return {
        "provider": "synoptic",
        "station": STATION,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "fetched_at_utc": fetched_time_str,
        "latest_observation_time": latest_obs_time,
        "observation_time_utc": latest_obs_time,
        "current_temp_f": current_temp,
        "dew_point_f": recent_observations_table[0]["dew_point_f"] if recent_observations_table else None,
        "raw_temp_c": recent_observations_table[0]["raw_temp_c"] if recent_observations_table else None,
        "raw_dewpoint_c": recent_observations_table[0]["raw_dewpoint_c"] if recent_observations_table else None,
        "observed_max_so_far_f": observed_max,
        "recent_window_max_temp_f": recent_window_max,
        "recent_observations_table": recent_observations_table,
        "endpoint_status": "OK",
        "stale_data": stale_data,
        "warnings": [],
        "raw_response_path": None,
        "source_product": "synoptic_timeseries",
        "underlying_feed": "ASOS/METAR-derived station timeseries",
        "raw_sensor_feed": False,
        "thirty_second_temperature_feed": False,
        "feed_label": "synoptic_kmia_feed",
        "cadence_observed_minutes": cadence,
        "latency_minutes": latency,
        "temporal_resolution_claim": "1-minute/HF-ASOS",
        "endpoint_metadata": endpoint_metadata,
        "qc_summary": qc_summary,
        "safety": {
            "no_real_trading": True,
            "no_order_execution": True
        }
    }



def save_snapshots(snapshot: Dict[str, Any], output_dir: Optional[Path] = None):
    """Save normalized snapshot to latest and timestamped files."""
    from shared.artifact_paths import WEATHER_SYNOPTIC_DIR, LATEST_SYNOPTIC_KMIA_SNAPSHOT
    output_dir = output_dir or WEATHER_SYNOPTIC_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    status = snapshot.get("endpoint_status")
    if status in ("MISSING_CREDENTIALS", "ERROR"):
        unavail_path = output_dir / "unavailable_synoptic_kmia_snapshot.json"
        with open(unavail_path, "w") as f:
            json.dump(snapshot, f, indent=2)
        return


    # Save latest
    latest_path = LATEST_SYNOPTIC_KMIA_SNAPSHOT
    with open(latest_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    # Save timestamped
    ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    ts_path = output_dir / f"synoptic_kmia_snapshot_{ts_str}.json"
    with open(ts_path, "w") as f:
        json.dump(snapshot, f, indent=2)


def run():
    """Main execution entry point."""
    print("Running Synoptic KMIA Observation Ingestion...")
    recent_env = os.getenv("SYNOPTIC_RECENT_MINUTES")
    recent = int(recent_env) if recent_env else 1440

    snapshot = fetch_synoptic_observations(recent)
    save_snapshots(snapshot)

    print(f"Status: {snapshot.get('endpoint_status')}")
    if snapshot.get("endpoint_status") == "MISSING_CREDENTIALS":
        print("Warning: Missing credentials. Written to unavailable snapshot.")
        sys.exit(2)
    elif snapshot.get("endpoint_status") == "ERROR":
        print(f"Error: {snapshot.get('warnings')}")
        sys.exit(1)
    else:
        print("Successfully updated Synoptic KMIA observation.")
        sys.exit(0)


if __name__ == "__main__":
    run()

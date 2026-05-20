import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
import requests

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

from shared.artifact_paths import WEATHER_TWC_DIR

STATION = "KMIA"
LATITUDE = 25.79540
LONGITUDE = -80.29010

# Anchored to the project root via shared.artifact_paths — never CWD-relative.
DEFAULT_PROCESSED_DIR = WEATHER_TWC_DIR
# Alias exposed for test monkeypatching: tests set twc_probabilistic_client.PROCESSED_DIR = tmpdir.
PROCESSED_DIR = DEFAULT_PROCESSED_DIR

def get_twc_api_key() -> Optional[str]:
    return os.environ.get("TWC_API_KEY") or os.environ.get("WEATHER_COMPANY_API_KEY")

def build_unavailable_snapshot(api_status: str, warnings: str) -> Dict[str, Any]:
    return {
        "station": STATION,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_at_utc": None,
        "observation_time_utc": None,
        "provider": "TWC",
        "api_status": api_status,
        "request_parameters": {
            "latitude": LATITUDE,
            "longitude": LONGITUDE
        },
        "warnings": warnings,
        "raw_response_archive_path": None,
        "parsed_percentiles": None,
        "parsed_pdf_or_probability_fields": None
    }

def fetch_twc_probabilistic_forecast(lat: float, lon: float, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    output_dir = output_dir or PROCESSED_DIR
    api_key = get_twc_api_key()
    if not api_key:
        return build_unavailable_snapshot("missing_credentials", "TWC_API_KEY environment variable is not set.")
        
    # Example TWC Probabilistic API URL
    url = "https://api.weather.com/v3/wx/forecast/hourly/probabilistic" 
    params = {
        "geocode": f"{lat},{lon}",
        "format": "json",
        "apiKey": api_key
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 401:
            return build_unavailable_snapshot("unauthorized", f"TWC API returned 401: {resp.text}")
        resp.raise_for_status()
        raw_data = resp.json()
        
        # Archive raw response
        ts = int(time.time())
        archive_dir = output_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"raw_twc_probabilistic_kmia_{ts}.json"
        with open(archive_path, "w") as f:
            json.dump(raw_data, f, indent=2)
            
        # Parse response
        parsed = parse_twc_response(raw_data)
        parsed["raw_response_archive_path"] = str(archive_path)
        return parsed
        
    except requests.exceptions.Timeout:
        return build_unavailable_snapshot("timeout", "TWC API request timed out.")
    except requests.exceptions.RequestException as e:
        return build_unavailable_snapshot("api_error", f"TWC API request failed: {str(e)}")
    except json.JSONDecodeError:
        return build_unavailable_snapshot("malformed_json", "TWC API returned invalid JSON.")

def parse_twc_response(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    # Placeholder for actual parsing logic.
    # Should extract percentiles or probability fields based on actual TWC schema.
    # Since we don't have the real schema, we extract what is available or return None.
    # TWC probabilistic often has validTimeUtc for each period or for the whole payload.
    # For now, we use fetched_at as best estimate if not provided.
    return {
        "station": STATION,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_at_utc": None, # Should be extracted from raw_data if available
        "observation_time_utc": None,
        "provider": "TWC",
        "api_status": "success",
        "request_parameters": {
            "latitude": LATITUDE,
            "longitude": LONGITUDE
        },
        "warnings": "",
        "parsed_percentiles": raw_data.get("percentiles"),
        "parsed_pdf_or_probability_fields": raw_data.get("pdf") or raw_data.get("probabilities")
    }

def save_snapshots(snapshot: Dict[str, Any], output_dir: Optional[Path] = None):
    output_dir = output_dir or PROCESSED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if snapshot.get("api_status") == "missing_credentials":
        # Save ONLY to a clearly separate unavailable artifact
        unavailable_path = output_dir / "unavailable_twc_probabilistic_kmia_snapshot.json"
        with open(unavailable_path, "w") as f:
            json.dump(snapshot, f, indent=2)
        return
        
    # Save latest
    latest_path = output_dir / "latest_twc_probabilistic_kmia_snapshot.json"
    with open(latest_path, "w") as f:
        json.dump(snapshot, f, indent=2)
        
    # Save timestamped
    ts = int(time.time())
    ts_path = output_dir / f"twc_probabilistic_kmia_snapshot_{ts}.json"
    with open(ts_path, "w") as f:
        json.dump(snapshot, f, indent=2)

def run():
    print("Running TWC Probabilistic Forecast Ingestion...")
    snapshot = fetch_twc_probabilistic_forecast(LATITUDE, LONGITUDE)
    save_snapshots(snapshot)
    print(f"Snapshots saved to {PROCESSED_DIR}")
    print(f"Status: {snapshot['api_status']}")
    if snapshot.get("api_status") == "missing_credentials":
        import sys
        sys.exit(2)

if __name__ == "__main__":
    run()

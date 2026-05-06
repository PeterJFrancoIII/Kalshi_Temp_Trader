import logging
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

try:
    from src.ingestion.kmia_live_fetcher import fetch_wrh_timeseries, fetch_obhistory
    from src.ingestion.kmia_obhistory_parser import parse_wrh_timeseries, parse_obhistory
    from src.ingestion.nws_forecast_fetcher import fetch_nws_forecast
except ImportError:
    # Mocks for testing if imports fail
    def fetch_wrh_timeseries(station="KMIA"): return None
    def fetch_obhistory(station="KMIA"): return None
    def parse_wrh_timeseries(data): return []
    def parse_obhistory(html, ref=None): return [], []
    def fetch_nws_forecast(grid_id="MFL", x=109, y=96): return None

logger = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "backend" / "data" / "processed" / "weather_ingestion"
STATUS_FILE = DATA_DIR / "latest_weather_ingestion_status.json"
HISTORY_FILE = ROOT / "backend" / "data" / "processed" / "history" / "kmia_daily_history.jsonl"

class NWSKMIAClient:
    def __init__(self, station: str = "KMIA"):
        self.station = station
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_live_status(self) -> Dict[str, Any]:
        """
        Fetches and summarizes the latest KMIA weather data.
        """
        status = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "station": self.station,
            "source": "NWS/public",
            "current_temp_f": None,
            "observed_max_so_far_f": None,
            "forecast_high_f": None,
            "latest_observation_time": None,
            "stale_data": True,
            "history_record_count": 0,
            "climatology_active": False,
            "warnings": [],
            "safety": {
                "no_real_trading": True
            }
        }

        # 1. Fetch Observations (JSON API)
        raw_json = fetch_wrh_timeseries(self.station)
        observations = []
        if raw_json:
            observations = parse_wrh_timeseries(raw_json)
        
        # 2. Fallback to HTML ObHistory if JSON fails or is empty
        if not observations:
            raw_html = fetch_obhistory(self.station)
            if raw_html:
                observations, parse_warns = parse_obhistory(raw_html)
                status["warnings"].extend(parse_warns)

        if observations:
            latest = observations[-1]
            status["current_temp_f"] = latest.temperature_f
            status["latest_observation_time"] = latest.timestamp.isoformat()
            
            # Check for staleness (1 hour)
            time_diff = datetime.now(timezone.utc) - latest.timestamp.replace(tzinfo=timezone.utc)
            status["stale_data"] = time_diff > timedelta(hours=1)

            # Compute observed max for TODAY (local time)
            # Assuming observations are already sorted by time
            today_local = datetime.now().date()
            today_obs = [o for o in observations if o.timestamp.date() == today_local and o.temperature_f is not None]
            if today_obs:
                status["observed_max_so_far_f"] = max(o.temperature_f for o in today_obs)
        else:
            status["warnings"].append("No observations found via JSON or HTML.")

        # 3. Fetch NWS Forecast High
        forecast_data = fetch_nws_forecast()
        if forecast_data:
            periods = forecast_data.get("properties", {}).get("periods", [])
            if periods:
                # First period is usually today's high or tonight's low
                today_period = periods[0]
                if today_period.get("isDaytime"):
                    status["forecast_high_f"] = today_period.get("temperature")
                elif len(periods) > 1 and periods[1].get("isDaytime"):
                    status["forecast_high_f"] = periods[1].get("temperature")

        # 4. History Count
        if HISTORY_FILE.exists():
            try:
                count = 0
                with open(HISTORY_FILE, "r") as f:
                    for line in f:
                        if line.strip():
                            count += 1
                status["history_record_count"] = count
                status["climatology_active"] = count > 0
            except Exception as e:
                status["warnings"].append(f"Error reading history: {e}")

        return status

    def save_status(self, status: Dict[str, Any]):
        """Saves status to JSON file."""
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f, indent=2)
            logger.info(f"Saved weather ingestion status to {STATUS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save weather status: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = NWSKMIAClient()
    status = client.get_live_status()
    client.save_status(status)
    print(json.dumps(status, indent=2))

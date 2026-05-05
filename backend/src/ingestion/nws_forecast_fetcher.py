import os
import json
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# KMIA Gridpoint MFL/109,96
DEFAULT_GRID_ID = "MFL"
DEFAULT_GRID_X = 109
DEFAULT_GRID_Y = 96

# NWS API requires a User-Agent
HEADERS = {
    "User-Agent": "KalshiWeatherPredictor/1.0 (computer@example.com)"
}

def _save_raw_response(data: Dict[str, Any], prefix: str) -> None:
    """Saves raw JSON response for debugging and audit."""
    try:
        # Determine paths relative to this file
        # backend/src/ingestion/nws_forecast_fetcher.py -> backend/data/raw/forecast/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        raw_dir = os.path.join(base_dir, "data", "raw", "forecast")
        os.makedirs(raw_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.json"
        filepath = os.path.join(raw_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved raw forecast to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save raw response: {e}")

def fetch_nws_forecast(grid_id: str = DEFAULT_GRID_ID, x: int = DEFAULT_GRID_X, y: int = DEFAULT_GRID_Y) -> Optional[Dict[str, Any]]:
    """
    Fetches the textual daily forecast from NWS.
    Endpoint: https://api.weather.gov/gridpoints/{office}/{gridX},{gridY}/forecast
    """
    url = f"https://api.weather.gov/gridpoints/{grid_id}/{x},{y}/forecast"
    try:
        logger.info(f"Fetching NWS daily forecast from {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        _save_raw_response(data, "daily_forecast")
        return data
    except requests.RequestException as e:
        logger.error(f"Error fetching NWS daily forecast: {e}")
        return None

def fetch_nws_hourly_forecast(grid_id: str = DEFAULT_GRID_ID, x: int = DEFAULT_GRID_X, y: int = DEFAULT_GRID_Y) -> Optional[Dict[str, Any]]:
    """
    Fetches the hourly forecast from NWS.
    Endpoint: https://api.weather.gov/gridpoints/{office}/{gridX},{gridY}/forecast/hourly
    """
    url = f"https://api.weather.gov/gridpoints/{grid_id}/{x},{y}/forecast/hourly"
    try:
        logger.info(f"Fetching NWS hourly forecast from {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        _save_raw_response(data, "hourly_forecast")
        return data
    except requests.RequestException as e:
        logger.error(f"Error fetching NWS hourly forecast: {e}")
        return None

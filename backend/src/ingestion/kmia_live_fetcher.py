import requests
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def fetch_wrh_timeseries(station: str = "KMIA") -> Optional[dict]:
    """
    Fetches the NWS API JSON for the station. This powers the WRH time series viewer.
    """
    url = f"https://api.weather.gov/stations/{station}/observations"
    headers = {"User-Agent": "KalshiWeatherPredictor/1.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching WRH timeseries for {station}: {e}")
        return None

def fetch_obhistory(station: str = "KMIA") -> Optional[str]:
    """
    Fetches the NWS ObHistory HTML page for the station.
    """
    url = f"https://www.weather.gov/data/obhistory/{station}.html"
    headers = {"User-Agent": "KalshiWeatherPredictor/1.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error fetching obhistory for {station}: {e}")
        return None

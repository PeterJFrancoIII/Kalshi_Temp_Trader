import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from weather.nws_live_client import (
    c_to_f, 
    build_live_nws_snapshot, 
    fetch_kmia_point_metadata,
    fetch_latest_kmia_observation,
    fetch_recent_kmia_observations_today
)

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

MOCK_POINT_META = {
    "properties": {
        "forecast": "https://api.weather.gov/gridpoints/MFL/109,96/forecast",
        "forecastHourly": "https://api.weather.gov/gridpoints/MFL/109,96/forecast/hourly"
    }
}

MOCK_LATEST_OBS = {
    "properties": {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": {"value": 25.0}, # 77F
        "dewpoint": {"value": 20.0},
        "windSpeed": {"value": 10.0},
        "windDirection": {"value": 90}
    }
}

MOCK_RECENT_OBS = {
    "features": [
        {
            "properties": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "temperature": {"value": 30.0} # 86F
            }
        },
        {
            "properties": {
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                "temperature": {"value": 25.0} # 77F
            }
        }
    ]
}

def test_c_to_f():
    assert c_to_f(0) == 32.0
    assert c_to_f(100) == 212.0
    assert c_to_f(25) == 77.0
    assert c_to_f(None) is None

@patch("requests.get")
def test_fetch_kmia_point_metadata(mock_get):
    mock_get.return_value.json.return_value = MOCK_POINT_META
    mock_get.return_value.status_code = 200
    res = fetch_kmia_point_metadata()
    assert res["properties"]["forecast"] == MOCK_POINT_META["properties"]["forecast"]

@patch("requests.get")
def test_build_live_nws_snapshot(mock_get):
    # Setup mocks for multiple calls
    m1 = MagicMock()
    m1.json.return_value = MOCK_POINT_META
    m1.status_code = 200
    
    m2 = MagicMock()
    m2.json.return_value = MOCK_LATEST_OBS
    m2.status_code = 200
    
    m3 = MagicMock()
    m3.json.return_value = MOCK_RECENT_OBS
    m3.status_code = 200

    # For forecast and hourly
    m4 = MagicMock()
    m4.json.return_value = {"properties": {"periods": [{"isDaytime": True, "temperature": 88}]}}
    m4.status_code = 200

    m5 = MagicMock()
    m5.json.return_value = {"properties": {"periods": [{"startTime": "2026-05-06T12:00:00-04:00", "temperature": 80, "shortForecast": "Sunny"}]}}
    m5.status_code = 200

    mock_get.side_effect = [m1, m2, m3, m4, m5]

    snap = build_live_nws_snapshot()
    
    assert snap["station"] == "KMIA"
    assert snap["current_temp_f"] == 77.0
    assert snap["observed_max_so_far_f"] == 86.0
    assert snap["forecast_high_f"] == 88
    assert snap["stale_data"] is False
    assert snap["safety"]["no_real_trading"] is True

def test_stale_data_detection():
    # Mock observation from 2 hours ago
    stale_obs = {
        "properties": {
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=120)).isoformat(),
            "temperature": {"value": 25.0}
        }
    }
    
    with patch("weather.nws_live_client.fetch_kmia_point_metadata", return_value=MOCK_POINT_META):
        with patch("weather.nws_live_client.fetch_latest_kmia_observation", return_value=stale_obs):
            with patch("weather.nws_live_client.fetch_recent_kmia_observations_today", return_value=[]):
                with patch("weather.nws_live_client.fetch_kmia_forecast", return_value={}):
                    with patch("weather.nws_live_client.fetch_kmia_hourly_forecast", return_value={}):
                        snap = build_live_nws_snapshot()
                        assert snap["stale_data"] is True

def test_missing_fields_no_crash():
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {}
        mock_get.return_value.status_code = 200
        snap = build_live_nws_snapshot()
        assert snap["station"] == "KMIA"
        assert snap["current_temp_f"] is None

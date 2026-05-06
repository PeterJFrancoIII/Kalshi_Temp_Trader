import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from dateutil import tz
from weather.nws_live_client import (
    c_to_f, 
    ms_to_mph,
    pa_to_mb,
    m_to_in,
    to_et,
    get_et_now,
    build_live_nws_snapshot, 
    fetch_kmia_point_metadata,
    fetch_latest_kmia_observation,
    fetch_recent_kmia_observations
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
        "windSpeed": {"value": 5.0}, # m/s -> 11.2 mph
        "windDirection": {"value": 90}
    }
}

# Use a fixed time for ET date testing
FIXED_NOW_UTC = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
ET_DATE_STR = "2026-05-06"

MOCK_RECENT_OBS = {
    "features": [
        {
            "properties": {
                "timestamp": FIXED_NOW_UTC.isoformat(),
                "temperature": {"value": 30.0}, # 86F
                "dewpoint": {"value": 20.0},
                "relativeHumidity": {"value": 60.5},
                "windDirection": {"value": 100},
                "windSpeed": {"value": 5.0},
                "windGust": {"value": 10.0},
                "seaLevelPressure": {"value": 101325}, # 1013.25 mb
                "barometricPressure": {"value": 101300},
                "precipitationLastHour": {"value": 0.01}, # 0.01 m -> 0.39 in
                "textDescription": "Mostly Sunny",
                "rawMessage": "METAR KMIA 061200Z..."
            }
        },
        {
            "properties": {
                "timestamp": (FIXED_NOW_UTC - timedelta(hours=1)).isoformat(),
                "temperature": {"value": 32.0} # 89.6F
            }
        }
    ]
}

def test_conversions():
    assert c_to_f(0) == 32.0
    assert c_to_f(25) == 77.0
    assert ms_to_mph(5) == 11.2
    assert pa_to_mb(101325) == 1013.25
    assert m_to_in(0.01) == 0.39

def test_timezone_conversion():
    ts = "2026-05-06T12:00:00Z"
    et_dt = to_et(ts)
    assert et_dt.strftime("%H:%M") == "08:00" # UTC-4 (May is EDT)

@patch("requests.get")
def test_fetch_kmia_point_metadata(mock_get):
    mock_get.return_value.json.return_value = MOCK_POINT_META
    mock_get.return_value.status_code = 200
    res = fetch_kmia_point_metadata()
    assert res["properties"]["forecast"] == MOCK_POINT_META["properties"]["forecast"]

@patch("requests.get")
@patch("weather.nws_live_client.get_et_now")
def test_build_live_nws_snapshot(mock_et_now, mock_get):
    # Fix ET now to match mock data
    mock_et_now.return_value = datetime(2026, 5, 6, 8, 0, 0, tzinfo=tz.gettz('America/New_York'))
    
    # Setup mocks for multiple calls
    m1 = MagicMock()
    m1.json.return_value = MOCK_POINT_META
    m1.status_code = 200
    
    m2 = MagicMock()
    m2.json.return_value = MOCK_RECENT_OBS
    m2.status_code = 200
    
    # For forecast and hourly
    m3 = MagicMock()
    m3.json.return_value = {"properties": {"periods": [{"isDaytime": True, "temperature": 88}]}}
    m3.status_code = 200

    m4 = MagicMock()
    m4.json.return_value = {"properties": {"periods": [{"startTime": "2026-05-06T12:00:00-04:00", "temperature": 80, "shortForecast": "Sunny"}]}}
    m4.status_code = 200

    mock_get.side_effect = [m1, m2, m3, m4]

    snap = build_live_nws_snapshot()
    
    assert snap["station"] == "KMIA"
    assert snap["current_temp_f"] == 86.0 # Latest from recent_feats
    assert snap["observed_max_so_far_f"] == 89.6 # Max of 86 and 89.6
    assert len(snap["recent_observations_table"]) == 2
    
    row = snap["recent_observations_table"][0]
    assert row["temperature_f"] == 86.0
    assert row["precipitation_last_hour_in"] == 0.39
    assert row["sea_level_pressure_mb"] == 1013.25

def test_stale_data_detection():
    # Mock observation from 2 hours ago
    stale_feats = [
        {
            "properties": {
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=120)).isoformat(),
                "temperature": {"value": 25.0}
            }
        }
    ]
    
    with patch("weather.nws_live_client.fetch_kmia_point_metadata", return_value=MOCK_POINT_META):
        with patch("weather.nws_live_client.fetch_recent_kmia_observations", return_value=stale_feats):
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

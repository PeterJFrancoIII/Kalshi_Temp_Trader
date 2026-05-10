import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from dateutil import tz
from weather import nws_live_client
from weather.nws_live_client import (
    c_to_f, 
    pa_to_mb,
    m_to_in,
    to_et,
    get_et_now,
    degrees_to_compass,
    convert_nws_wind_to_mph,
    parse_nws_cloud_layers,
    build_live_nws_snapshot, 
    fetch_kmia_point_metadata,
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
                "windDirection": {"value": 100}, # ESE
                "windSpeed": {"value": 5.0, "unitCode": "wmoUnit:m_s-1"}, # 11.2 mph
                "windGust": {"value": 10.0, "unitCode": "wmoUnit:m_s-1"}, # 22.4 mph
                "seaLevelPressure": {"value": 101325}, 
                "barometricPressure": {"value": 101300},
                "precipitationLastHour": {"value": 0.01}, 
                "cloudLayers": [
                    {"amount": "FEW", "base": {"value": 762, "unitCode": "wmoUnit:m"}}, # 2500ft -> 025
                    {"amount": "SCT", "base": {"value": 1372, "unitCode": "wmoUnit:m"}} # 4500ft -> 045
                ],
                "textDescription": "Mostly Sunny",
                "rawMessage": "METAR KMIA 061200Z..."
            }
        }
    ]
}

def test_conversions():
    assert c_to_f(0) == 32.0
    assert pa_to_mb(101325) == 1013.25
    assert m_to_in(0.01) == 0.39

def test_wind_conversions():
    # m/s to mph
    assert convert_nws_wind_to_mph({"value": 5.0, "unitCode": "wmoUnit:m_s-1"}) == 11.2
    # km/h to mph
    assert convert_nws_wind_to_mph({"value": 10.0, "unitCode": "wmoUnit:km_h-1"}) == 6.2
    # mph to mph
    assert convert_nws_wind_to_mph({"value": 15.0, "unitCode": "wmoUnit:mi_h-1"}) == 15.0
    # Null handling
    assert convert_nws_wind_to_mph({"value": None}) is None

def test_compass_conversion():
    assert degrees_to_compass(0) == "N"
    assert degrees_to_compass(22.5) == "NNE"
    assert degrees_to_compass(45) == "NE"
    assert degrees_to_compass(90) == "E"
    assert degrees_to_compass(135) == "SE"
    assert degrees_to_compass(180) == "S"
    assert degrees_to_compass(225) == "SW"
    assert degrees_to_compass(270) == "W"
    assert degrees_to_compass(315) == "NW"
    assert degrees_to_compass(360) == "N"
    assert degrees_to_compass(None) == ""

def test_cloud_parsing():
    layers = [
        {"amount": "FEW", "base": {"value": 762, "unitCode": "wmoUnit:m"}},
        {"amount": "SCT", "base": {"value": 1372, "unitCode": "wmoUnit:m"}}
    ]
    assert parse_nws_cloud_layers(layers) == "FEW025 SCT045"
    assert parse_nws_cloud_layers([]) == ""
    assert parse_nws_cloud_layers(None) == ""
    # Null base value but amount present
    assert parse_nws_cloud_layers([{"amount": "CLR", "base": {"value": None}}]) == "CLR"

def test_date_time_formatting():
    ts = "2026-05-06T12:53:00Z"
    dt_et = to_et(ts)
    # 12:53 UTC -> 08:53 AM EDT
    assert dt_et.strftime("%Y-%m-%d") == "2026-05-06"
    assert dt_et.strftime("%I:%M %p ET").lstrip("0") == "8:53 AM ET"

@patch("requests.get")
@patch("weather.nws_live_client.get_et_now")
def test_build_live_nws_snapshot_enhanced(mock_et_now, mock_get):
    mock_et_now.return_value = datetime(2026, 5, 6, 8, 0, 0, tzinfo=tz.gettz('America/New_York'))
    
    m1 = MagicMock()
    m1.json.return_value = MOCK_POINT_META
    m1.status_code = 200
    m2 = MagicMock()
    m2.json.return_value = MOCK_RECENT_OBS
    m2.status_code = 200
    m3 = MagicMock()
    m3.json.return_value = {"properties": {"periods": []}}
    m3.status_code = 200
    m4 = MagicMock()
    m4.json.return_value = {"properties": {"periods": []}}
    m4.status_code = 200
    
    mock_get.side_effect = [m1, m2, m3, m4] # Point, Obs, Forecast, Hourly

    snap = build_live_nws_snapshot()
    
    row = snap["recent_observations_table"][0]
    assert row["date_et"] == "2026-05-06"
    assert row["time_et"] == "8:00 AM ET"
    assert row["wind_direction_compass"] == "E"
    assert row["wind_speed_mph"] == 11.2
    assert row["wind_gust_mph"] == 22.4
    assert row["clouds_x100ft"] == "FEW025 SCT045"
    assert row["source"] == "api.weather.gov"
    
    assert snap["observation_source"] == "api.weather.gov"
    assert snap["wind_direction_compass"] == "E"
    assert snap["clouds_x100ft"] == "FEW025 SCT045"

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
    with patch("weather.nws_live_client.fetch_kmia_point_metadata", return_value={}):
        with patch(
            "weather.nws_live_client.fetch_recent_kmia_observations",
            return_value=[{"properties": {"timestamp": datetime.now(timezone.utc).isoformat()}}],
        ):
            with patch("weather.nws_live_client.fetch_kmia_obhistory_html", return_value=None):
                snap = build_live_nws_snapshot()

    assert snap["station"] == "KMIA"
    assert snap["current_temp_f"] is None
    assert snap["recent_observations_count"] == 1


class DummyObservation:
    def __init__(self, timestamp, temperature_f, dewpoint_f=None):
        self.timestamp = timestamp
        self.temperature_f = temperature_f
        self.dewpoint_f = dewpoint_f
        self.humidity = 55.0
        self.wind_direction = 90.0
        self.wind_speed_mph = 8.0
        self.wind_gust_mph = None
        self.pressure_in = 29.92
        self.precipitation_in = 0.0
        self.weather_condition = "Fair"
        self.sky_condition = "CLR"
        self.raw_metar = "KMIA TEST"


def test_build_live_snapshot_uses_obhistory_fallback():
    now_utc = datetime.now(timezone.utc)
    obs_time = now_utc - timedelta(minutes=20)

    with patch("weather.nws_live_client.fetch_kmia_point_metadata", return_value={}):
        with patch("weather.nws_live_client.fetch_recent_kmia_observations", return_value=[]):
            with patch("weather.nws_live_client.fetch_kmia_obhistory_html", return_value="<html>fallback</html>"):
                with patch(
                    "weather.nws_live_client.parse_obhistory",
                    return_value=([DummyObservation(obs_time, 84.0, 73.0)], []),
                ):
                    snapshot = nws_live_client.build_live_nws_snapshot()

    assert snapshot["station"] == "KMIA"
    assert snapshot["endpoint_status"] == "PARTIAL"
    assert snapshot["observation_source"] == "weather.gov_obhistory"
    assert snapshot["recent_observations_count"] == 1
    assert snapshot["current_temp_f"] == 84.0
    assert snapshot["observed_max_so_far_f"] == 84.0
    assert snapshot["stale_data"] is False
    assert snapshot["recent_observations_table"][0]["source"] == "weather.gov_obhistory"


def test_build_live_snapshot_errors_when_api_and_fallback_empty():
    with patch("weather.nws_live_client.fetch_kmia_point_metadata", return_value={}):
        with patch("weather.nws_live_client.fetch_recent_kmia_observations", return_value=[]):
            with patch("weather.nws_live_client.fetch_kmia_obhistory_html", return_value=None):
                snapshot = nws_live_client.build_live_nws_snapshot()

    assert snapshot["endpoint_status"] == "ERROR"
    assert snapshot["recent_observations_table"] == []
    assert snapshot["recent_observations_count"] == 0
    assert snapshot["stale_data"] is True
    assert any("No live observation rows" in warning for warning in snapshot["warnings"])

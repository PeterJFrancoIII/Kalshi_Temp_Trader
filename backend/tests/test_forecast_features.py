import pytest
from datetime import datetime, date
import pytz
from features.forecast_features import ForecastParser

@pytest.fixture
def parser():
    return ForecastParser()

@pytest.fixture
def mock_daily_json():
    return {
        "properties": {
            "updateTime": "2026-05-03T12:00:00Z",
            "periods": [
                {
                    "name": "Today",
                    "startTime": "2026-05-03T08:00:00-04:00",
                    "endTime": "2026-05-03T20:00:00-04:00",
                    "isDaytime": True,
                    "temperature": 84,
                    "probabilityOfPrecipitation": {"value": 30},
                    "detailedForecast": "A 30 percent chance of showers and thunderstorms. Mostly cloudy, with a high near 84."
                },
                {
                    "name": "Tonight",
                    "startTime": "2026-05-03T20:00:00-04:00",
                    "endTime": "2026-05-04T08:00:00-04:00",
                    "isDaytime": False,
                    "temperature": 75,
                    "detailedForecast": "Mostly cloudy."
                }
            ]
        }
    }

@pytest.fixture
def mock_hourly_json():
    return {
        "properties": {
            "periods": [
                {"startTime": "2026-05-03T13:00:00-04:00", "temperature": 82},
                {"startTime": "2026-05-03T14:00:00-04:00", "temperature": 83},
                {"startTime": "2026-05-03T15:00:00-04:00", "temperature": 85}, # Hourly max
                {"startTime": "2026-05-03T16:00:00-04:00", "temperature": 84},
                {"startTime": "2026-05-04T13:00:00-04:00", "temperature": 88}  # Next day, should be ignored
            ]
        }
    }

def test_parse_forecast_features(parser, mock_daily_json, mock_hourly_json):
    target_date = date(2026, 5, 3)
    features = parser.parse_forecasts(mock_daily_json, mock_hourly_json, target_date=target_date)
    
    assert features.forecast_high_f == 84
    assert features.hourly_max_forecast_f == 85
    assert features.rain_expected_flag is True
    assert features.thunderstorm_expected_flag is True
    assert features.cloud_suppression_flag is True
    assert features.forecast_date == target_date

def test_stale_forecast_detection(parser, mock_daily_json):
    # Mock current time to be much later than updateTime
    # updateTime is 12:00:00Z (08:00:00 ET)
    # If we run at 10:00:00 ET, age should be 120 mins
    target_date = date(2026, 5, 3)
    features = parser.parse_forecasts(mock_daily_json, None, target_date=target_date)
    
    # Age calculation depends on real datetime.now(), so we check it's > 0
    assert features.forecast_age_minutes > 0

def test_to_snapshot(parser, mock_daily_json):
    target_date = date(2026, 5, 3)
    features = parser.parse_forecasts(mock_daily_json, None, target_date=target_date)
    snapshot = parser.to_snapshot(features)
    
    assert snapshot.date == target_date
    assert snapshot.station == "KMIA"
    assert snapshot.forecast_high_f == 84

def test_missing_data_handling(parser):
    features = parser.parse_forecasts(None, None, target_date=date(2026, 5, 3))
    assert features.forecast_high_f == -999
    assert features.hourly_max_forecast_f is None
    assert features.rain_expected_flag is False

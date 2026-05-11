# import pytest
from datetime import datetime, timezone, timedelta
from dateutil.tz import gettz
from unittest.mock import patch

from ingestion.kmia_obhistory_parser import parse_wrh_timeseries, parse_obhistory, ParsedObservation
from features.live_features import compute_live_features

def test_parse_wrh_timeseries_empty():
    obs = parse_wrh_timeseries({})
    assert len(obs) == 0

def test_parse_wrh_timeseries_valid():
    raw_json = {
        "features": [
            {
                "properties": {
                    "timestamp": "2026-05-03T18:00:00+00:00",
                    "temperature": {"value": 25.0}, # 77.0 F
                    "dewpoint": {"value": 20.0},
                    "relativeHumidity": {"value": 75.0},
                    "textDescription": "Mostly Cloudy",
                    "rawMessage": "METAR KMIA ..."
                }
            }
        ]
    }
    obs = parse_wrh_timeseries(raw_json)
    assert len(obs) == 1
    assert obs[0].temperature_f == 77.0
    assert obs[0].dewpoint_f == 68.0
    assert obs[0].humidity == 75.0
    assert obs[0].weather_condition == "Mostly Cloudy"
    assert obs[0].is_preliminary is True

def test_parse_obhistory_html():
    html = """
    <html><body>
    <table></table><table></table><table></table>
    <table>
        <tr><th>Date</th><th>Time</th><th>Temp</th><th>Dew Point</th><th>Humidity</th></tr>
        <tr>
            <td>03</td><td>14:53</td><td>E 10</td><td>10.00</td><td>Fair</td>
            <td>CLR</td><td>82</td><td>65</td><td></td><td></td>
            <td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
    </table>
    </body></html>
    """
    obs, warnings = parse_obhistory(html)
    assert len(obs) == 1
    assert obs[0].temperature_f == 82.0
    assert obs[0].weather_condition == "Fair"
    assert obs[0].sky_condition == "CLR"
    assert len(warnings) == 0

def test_parse_obhistory_discovery():
    # Table is at index 0 now, should still find it
    html = """
    <html><body>
    <table>
        <tr><th>Date</th><th>Time (et)</th><th>Temperature</th><th>Dew Point</th><th>Humidity</th></tr>
        <tr><td>03</td><td>12:53</td><td>W 5</td><td>10.00</td><td>Sunny</td><td>CLR</td><td>85</td><td>60</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
    </table>
    </body></html>
    """
    obs, warnings = parse_obhistory(html)
    assert len(obs) == 1
    assert obs[0].temperature_f == 85.0
    assert len(warnings) == 0

def test_parse_obhistory_missing_table():
    html = "<html><body><table><tr><td>No data here</td></tr></table></body></html>"
    obs, warnings = parse_obhistory(html)
    assert len(obs) == 0
    assert "no matching observation table found" in warnings

def test_parse_obhistory_malformed_temp():
    html = """
    <html><body>
    <table>
        <tr><th>Date</th><th>Time</th><th>Temp</th><th>Dew Point</th><th>Humidity</th></tr>
        <tr><td>03</td><td>14:53</td><td>E 10</td><td>10.00</td><td>Fair</td><td>CLR</td><td>XX</td><td>65</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
        <tr><td>03</td><td>13:53</td><td>E 10</td><td>10.00</td><td>Fair</td><td>CLR</td><td>80</td><td>65</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
    </table>
    </body></html>
    """
    obs, warnings = parse_obhistory(html)
    assert len(obs) == 1
    assert obs[0].temperature_f == 80.0
    assert any("rows skipped" in w for w in warnings)

def test_parse_obhistory_month_rollover():
    # Ref is May 1st
    ref = datetime(2026, 5, 1, 12, 0)
    html = """
    <html><body>
    <table>
        <tr><th>Date</th><th>Time</th><th>Temp</th><th>Dew Point</th><th>Humidity</th></tr>
        <tr><td>30</td><td>23:53</td><td>E 10</td><td>10.00</td><td>Fair</td><td>CLR</td><td>75</td><td>65</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
    </table>
    </body></html>
    """
    obs, warnings = parse_obhistory(html, reference_datetime=ref)
    assert len(obs) == 1
    assert obs[0].timestamp.month == 4
    assert obs[0].timestamp.day == 30
    assert obs[0].timestamp.year == 2026

def test_parse_obhistory_year_rollover():
    # Ref is Jan 1st
    ref = datetime(2027, 1, 1, 12, 0)
    html = """
    <html><body>
    <table>
        <tr><th>Date</th><th>Time</th><th>Temp</th><th>Dew Point</th><th>Humidity</th></tr>
        <tr><td>31</td><td>23:53</td><td>E 10</td><td>10.00</td><td>Fair</td><td>CLR</td><td>70</td><td>65</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
    </table>
    </body></html>
    """
    obs, warnings = parse_obhistory(html, reference_datetime=ref)
    assert len(obs) == 1
    assert obs[0].timestamp.month == 12
    assert obs[0].timestamp.day == 31
    assert obs[0].timestamp.year == 2026

@patch('features.live_features.datetime')
def test_compute_live_features_max_so_far(mock_datetime):
    # Mock datetime.now to return a fixed time (12:00 UTC)
    fixed_now = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = fixed_now
    # Make sure datetime(...) calls work normally
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    
    t1 = fixed_now - timedelta(minutes=60)
    t2 = fixed_now - timedelta(minutes=30)
    
    obs = [
        ParsedObservation(timestamp=t1, temperature_f=85.0),
        ParsedObservation(timestamp=t2, temperature_f=82.0),
    ]
    
    snap, live, metrics = compute_live_features(obs)
    
    assert live.current_temp_f == 82
    assert live.observed_max_so_far_f == 85
    assert metrics.stale_data_flag is False

def test_stale_data_flag():
    actual_now = datetime.now(timezone.utc)
    
    # 3 hours ago -> stale
    t1 = actual_now - timedelta(hours=3)
    
    obs = [
        ParsedObservation(timestamp=t1, temperature_f=85.0),
    ]
    
    snap, live, metrics = compute_live_features(obs)
    assert metrics.stale_data_flag is True

def test_missing_temp():
    tz = gettz('US/Eastern')
    now = datetime.now(tz)
    
    obs = [
        ParsedObservation(timestamp=now, temperature_f=None, weather_condition="Rain"),
    ]
    
    snap, live, metrics = compute_live_features(obs)
    assert live.current_temp_f == 0
    assert live.observed_max_so_far_f == 0
    assert metrics.stale_data_flag is True
    assert snap.recent_rain_flag is True

def test_timezone_boundary():
    tz = gettz('US/Eastern')
    now = datetime.now(tz)
    
    # Yesterday 11 PM ET
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=tz)
    yesterday = start_of_today - timedelta(hours=1)
    
    obs = [
        ParsedObservation(timestamp=yesterday, temperature_f=90.0), # Should not count for today
        ParsedObservation(timestamp=now, temperature_f=80.0), # Today
    ]
    
    snap, live, metrics = compute_live_features(obs)
    assert live.observed_max_so_far_f == 80 # 90 is ignored

import pytest
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from weather.nws_kmia_client import NWSKMIAClient

# NO REAL TRADING EXECUTION

def test_weather_status_serialization():
    """Verify that weather status can be saved to JSON."""
    client = NWSKMIAClient()
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    status_file = temp_dir / "status.json"
    
    with patch("weather.nws_kmia_client.STATUS_FILE", status_file):
        status = {
            "fetched_at_utc": "2026-05-06T00:00:00Z",
            "station": "KMIA",
            "current_temp_f": 80.0,
            "safety": {"no_real_trading": True}
        }
        client.save_status(status)
        
        assert status_file.exists()
        with open(status_file, "r") as f:
            saved = json.load(f)
            assert saved["current_temp_f"] == 80.0

def test_stale_data_flag():
    """Verify the stale data logic."""
    client = NWSKMIAClient()
    
    # Mock observations
    obs_now = MagicMock()
    obs_now.timestamp = datetime.now(timezone.utc)
    obs_now.temperature_f = 80.0
    
    obs_old = MagicMock()
    obs_old.timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
    obs_old.temperature_f = 75.0
    
    # Test not stale
    with patch("weather.nws_kmia_client.fetch_wrh_timeseries", return_value={"mock": "data"}), \
         patch("weather.nws_kmia_client.parse_wrh_timeseries", return_value=[obs_now]), \
         patch("weather.nws_kmia_client.fetch_nws_forecast", return_value=None), \
         patch("os.path.exists", return_value=False):

        status = client.get_live_status()
        assert status["stale_data"] is False
        assert status["current_temp_f"] == 80.0

    # Test stale
    with patch("weather.nws_kmia_client.fetch_wrh_timeseries", return_value={"mock": "data"}), \
         patch("weather.nws_kmia_client.parse_wrh_timeseries", return_value=[obs_old]), \
         patch("weather.nws_kmia_client.fetch_nws_forecast", return_value=None), \
         patch("os.path.exists", return_value=False):
        
        status = client.get_live_status()
        assert status["stale_data"] is True
        assert status["current_temp_f"] == 75.0

def test_observed_max_so_far():
    """Verify max temperature computation for today."""
    client = NWSKMIAClient()
    
    today = datetime.now().date()
    o1 = MagicMock()
    o1.timestamp = datetime.combine(today, datetime.min.time())
    o1.temperature_f = 70.0
    
    o2 = MagicMock()
    o2.timestamp = datetime.combine(today, datetime.max.time())
    o2.temperature_f = 85.0
    
    with patch("weather.nws_kmia_client.fetch_wrh_timeseries", return_value={"mock": "data"}), \
         patch("weather.nws_kmia_client.parse_wrh_timeseries", return_value=[o1, o2]), \
         patch("weather.nws_kmia_client.fetch_nws_forecast", return_value=None), \
         patch("os.path.exists", return_value=False):
        
        status = client.get_live_status()
        assert status["observed_max_so_far_f"] == 85.0

def test_history_record_count():
    """Verify historical record counting."""
    client = NWSKMIAClient()
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    history_file = temp_dir / "history.jsonl"
    history_file.write_text('{"date": "2026-05-01"}\n{"date": "2026-05-02"}\n')
    
    # We need to patch Path.exists which is used in NWSKMIAClient
    with patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", MagicMock(return_value=open(history_file, "r"))), \
         patch("weather.nws_kmia_client.fetch_wrh_timeseries", return_value=None), \
         patch("weather.nws_kmia_client.fetch_obhistory", return_value=None), \
         patch("weather.nws_kmia_client.fetch_nws_forecast", return_value=None):
        
        status = client.get_live_status()
        assert status["history_record_count"] == 2
        assert status["climatology_active"] is True

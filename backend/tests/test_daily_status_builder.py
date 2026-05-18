import os
import json
import shutil
import tempfile
from status.daily_status import build_daily_status

def test_empty_directories():
    """Empty directories produce WARN and warnings, not crash."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        reports_dir = os.path.join(tmp_dir, "reports")
        agg_dir = os.path.join(tmp_dir, "agg")
        logs_dir = os.path.join(tmp_dir, "logs")
        os.makedirs(reports_dir)
        os.makedirs(agg_dir)
        os.makedirs(logs_dir)
        
        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=reports_dir,
            aggregate_dir=agg_dir,
            logs_dir=logs_dir
        )
        
        assert status["system_status"] == "WARN"
        assert len(status["warnings"]) > 0
        assert any("Missing V1 report" in w for w in status["warnings"])

def test_valid_aggregate_json():
    """Valid aggregate JSON populates summary fields."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agg_dir = os.path.join(tmp_dir, "agg")
        os.makedirs(agg_dir)
        agg_json = os.path.join(agg_dir, "aggregate_calibration.json")
        data = {
            "settled_days": 10,
            "v1_avg_brier": 0.5,
            "v2_avg_brier": 0.4,
            "v2_win_rate_by_brier": 0.7
        }
        with open(agg_json, 'w') as f:
            json.dump(data, f)
            
        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=tmp_dir,
            aggregate_dir=agg_dir,
            logs_dir=tmp_dir
        )
        
        agg = status["aggregate_calibration"]
        assert agg["settled_days"] == 10
        assert agg["v1_avg_brier"] == 0.5
        assert agg["v2_avg_brier"] == 0.4
        assert agg["v2_win_rate_by_brier"] == 0.7

def test_log_error_status():
    """Log with ERROR or Traceback sets system_status=ERROR."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        logs_dir = os.path.join(tmp_dir, "logs")
        os.makedirs(logs_dir)
        log_path = os.path.join(logs_dir, "kmia_daily_workflow_2026-05-03.log")
        with open(log_path, 'w') as f:
            f.write("2026-05-03 12:00:00 - ERROR - Something failed\n")
            
        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=tmp_dir,
            aggregate_dir=tmp_dir,
            logs_dir=logs_dir
        )
        
        assert status["system_status"] == "ERROR"
        assert status["workflow_log"]["contains_error"] is True

def test_log_warning_status():
    """Log with WARNING sets system_status=WARN."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        logs_dir = os.path.join(tmp_dir, "logs")
        os.makedirs(logs_dir)
        log_path = os.path.join(logs_dir, "kmia_daily_workflow_2026-05-03.log")
        with open(log_path, 'w') as f:
            f.write("2026-05-03 12:00:00 - WARNING - Data stale\n")
            
        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=tmp_dir,
            aggregate_dir=tmp_dir,
            logs_dir=logs_dir
        )
        
        # Note: missing reports also set WARN, so this is guaranteed WARN
        assert status["system_status"] == "WARN"
        assert status["workflow_log"]["contains_warning"] is True

def test_normal_ok_status():
    """Normal files and clean log produce system_status=OK."""
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    fetched_time = now.isoformat()
    obs_time = (now - datetime.timedelta(minutes=5)).isoformat()

    with tempfile.TemporaryDirectory() as tmp_dir:
        reports_dir = os.path.join(tmp_dir, "reports")
        logs_dir = os.path.join(tmp_dir, "logs")
        os.makedirs(reports_dir)
        os.makedirs(logs_dir)
        
        # Create reports (must have different names to be "latest")
        open(os.path.join(reports_dir, "kmia_forecast_2026-05-03_rules_v1_123.md"), 'w').close()
        open(os.path.join(reports_dir, "kmia_forecast_2026-05-03_rules_v2_climatology_123.md"), 'w').close()
        
        # Create log
        log_path = os.path.join(logs_dir, "kmia_daily_workflow_2026-05-03.log")
        with open(log_path, 'w') as f:
            f.write("2026-05-03 12:00:00 - INFO - All good\n")
            
        # Create valid NWS snapshot JSON
        valid_nws = {
            "station": "KMIA",
            "fetched_at_utc": fetched_time,
            "latest_observation_time": obs_time,
            "current_temp_f": 82.0,
            "observed_max_so_far_f": 85.0,
            "forecast_high_f": 87.0,
            "recent_observations_table": [
                {
                    "timestamp": obs_time,
                    "temperature_f": 82.0,
                    "dewpoint_f": 72.0,
                    "relative_humidity_pct": 71,
                    "wind_speed_mph": 10.0,
                    "wind_gust_mph": 15.0,
                    "sea_level_pressure_mb": 1015.0,
                    "barometric_pressure_mb": 1014.0,
                    "precipitation_last_hour_in": 0.0,
                    "wind_direction_compass": "E"
                }
            ],
            "safety": {
                "no_real_trading": True
            }
        }
        nws_path = os.path.join(tmp_dir, "nws_snapshot.json")
        with open(nws_path, 'w') as f:
            json.dump(valid_nws, f)
            
        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=reports_dir,
            aggregate_dir=tmp_dir,
            logs_dir=logs_dir,
            nws_snapshot_path=nws_path
        )
        
        assert status["system_status"] == "OK"
        # We don't check for 'warnings' being empty because comp report might be missing in this test setup
        # but let's add comp report to be sure
        open(os.path.join(reports_dir, "kmia_comparison_2026-05-03_123.md"), 'w').close()
        # And aggregate JSON
        os.makedirs(os.path.join(tmp_dir, "agg"))
        with open(os.path.join(tmp_dir, "agg", "aggregate_calibration.json"), 'w') as f:
            json.dump({"settled_days": 1}, f)

        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=reports_dir,
            aggregate_dir=os.path.join(tmp_dir, "agg"),
            logs_dir=logs_dir,
            nws_snapshot_path=nws_path
        )
        assert status["system_status"] == "OK"
        assert len(status["warnings"]) == 0

def test_safety_trading_disabled():
    """safety.real_trading_enabled is always false."""
    status = build_daily_status()
    assert status["safety"]["real_trading_enabled"] is False

def test_weather_gate_degrades_status_to_error():
    """Invalid station degrades status to ERROR."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # NWS snapshot with wrong station name (station != KMIA)
        invalid_nws = {
            "station": "KDFW",
            "fetched_at_utc": "2026-05-03T12:00:00Z",
            "latest_observation_time": "2026-05-03T11:53:00Z",
            "current_temp_f": 82.0,
            "observed_max_so_far_f": 85.0,
            "forecast_high_f": 87.0,
            "recent_observations_table": [{"timestamp": "2026-05-03T11:53:00Z"}],
            "safety": {"no_real_trading": True}
        }
        nws_path = os.path.join(tmp_dir, "nws_snapshot.json")
        with open(nws_path, 'w') as f:
            json.dump(invalid_nws, f)
            
        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=tmp_dir,
            aggregate_dir=tmp_dir,
            logs_dir=tmp_dir,
            nws_snapshot_path=nws_path
        )
        
        assert status["system_status"] == "ERROR"
        assert status["weather_gate"]["status"] == "ERROR"
        assert status["weather_gate"]["allow_paper_recommendations"] is False
        assert any("Station must be KMIA" in w for w in status["warnings"])

def test_weather_gate_degrades_status_to_warn_stale():
    """Stale observation (age > 90 minutes) degrades status to WARN."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # observation is 120 minutes old
        stale_nws = {
            "station": "KMIA",
            "fetched_at_utc": "2026-05-03T12:00:00Z",
            "latest_observation_time": "2026-05-03T10:00:00Z",
            "current_temp_f": 82.0,
            "observed_max_so_far_f": 85.0,
            "forecast_high_f": 87.0,
            "recent_observations_table": [
                {
                    "timestamp": "2026-05-03T10:00:00Z",
                    "temperature_f": 82.0,
                    "dewpoint_f": 72.0,
                    "relative_humidity_pct": 71,
                    "wind_speed_mph": 10.0,
                    "wind_gust_mph": 15.0,
                    "sea_level_pressure_mb": 1015.0,
                    "barometric_pressure_mb": 1014.0,
                    "precipitation_last_hour_in": 0.0,
                    "wind_direction_compass": "E"
                }
            ],
            "safety": {"no_real_trading": True}
        }
        nws_path = os.path.join(tmp_dir, "nws_snapshot.json")
        with open(nws_path, 'w') as f:
            json.dump(stale_nws, f)
            
        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=tmp_dir,
            aggregate_dir=tmp_dir,
            logs_dir=tmp_dir,
            nws_snapshot_path=nws_path
        )
        
        assert status["system_status"] == "WARN"
        assert status["weather_gate"]["status"] == "STALE"
        assert status["weather_gate"]["allow_paper_recommendations"] is False
        assert any("old" in w.lower() or "stale" in w.lower() for w in status["warnings"])

def test_weather_gate_degrades_status_to_warn_missing():
    """Missing NWS snapshot degrades status to WARN."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=tmp_dir,
            aggregate_dir=tmp_dir,
            logs_dir=tmp_dir,
            nws_snapshot_path=os.path.join(tmp_dir, "nonexistent.json")
        )
        
        assert status["system_status"] == "WARN"
        assert status["weather_gate"]["status"] == "MISSING"
        assert status["weather_gate"]["allow_paper_recommendations"] is False
        assert any("missing" in w.lower() for w in status["warnings"])

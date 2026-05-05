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
            
        status = build_daily_status(
            target_date="2026-05-03",
            reports_dir=reports_dir,
            aggregate_dir=tmp_dir,
            logs_dir=logs_dir
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
            logs_dir=logs_dir
        )
        assert status["system_status"] == "OK"
        assert len(status["warnings"]) == 0

def test_safety_trading_disabled():
    """safety.real_trading_enabled is always false."""
    status = build_daily_status()
    assert status["safety"]["real_trading_enabled"] is False

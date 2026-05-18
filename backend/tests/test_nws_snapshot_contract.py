import pytest
from datetime import datetime, timezone
from weather.nws_snapshot_contract import assess_nws_snapshot

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def get_base_valid_snapshot():
    """Returns a completely valid and fresh snapshot dict."""
    return {
        "station": "KMIA",
        "fetched_at_utc": "2026-05-15T20:28:09.890186+00:00",
        "latest_observation_time": "2026-05-15T20:00:00+00:00",
        "current_temp_f": 89.6,
        "observed_max_so_far_f": 93.2,
        "forecast_high_f": 89,
        "recent_observations_table": [
            {
                "timestamp_utc": "2026-05-15T20:00:00+00:00",
                "temperature_f": 89.6
            }
        ],
        "stale_data": False,
        "stale_fallback": False,
        "endpoint_status": "OK",
        "safety": {
            "no_real_trading": True
        }
    }

def get_test_reference_now():
    """Returns a valid UTC now reference (30 minutes after observation)."""
    return datetime(2026, 5, 15, 20, 30, 0, tzinfo=timezone.utc)

def test_fresh_valid_snapshot_allows_recommendations():
    """Scenario 1: Fresh valid snapshot allows paper recommendations."""
    snapshot = get_base_valid_snapshot()
    now_utc = get_test_reference_now()
    res = assess_nws_snapshot(snapshot, now_utc=now_utc)
    
    assert res["available"] is True
    assert res["allow_paper_recommendations"] is True
    assert res["status"] == "OK"
    assert res["required_fields_present"] is True
    assert res["observation_age_minutes"] == 30.0
    assert res["no_trade_reason"] is None
    assert len(res["warnings"]) == 0

def test_stale_data_flag_blocks_recommendations():
    """Scenario 2: stale_data=true blocks."""
    snapshot = get_base_valid_snapshot()
    snapshot["stale_data"] = True
    now_utc = get_test_reference_now()
    res = assess_nws_snapshot(snapshot, now_utc=now_utc)
    
    assert res["available"] is True
    assert res["allow_paper_recommendations"] is False
    assert res["status"] == "STALE"
    assert "stale_data flag is True" in res["no_trade_reason"]

def test_stale_fallback_flag_blocks_recommendations():
    """Scenario 3: stale_fallback=true blocks."""
    snapshot = get_base_valid_snapshot()
    snapshot["stale_fallback"] = True
    now_utc = get_test_reference_now()
    res = assess_nws_snapshot(snapshot, now_utc=now_utc)
    
    assert res["available"] is True
    assert res["allow_paper_recommendations"] is False
    assert res["status"] == "STALE"
    assert "stale_fallback flag is True" in res["no_trade_reason"]

def test_observation_older_than_90_minutes_blocks():
    """Scenario 4: Observation older than 90 minutes blocks."""
    snapshot = get_base_valid_snapshot()
    # 91 minutes later
    now_utc = datetime(2026, 5, 15, 21, 31, 0, tzinfo=timezone.utc)
    res = assess_nws_snapshot(snapshot, now_utc=now_utc)
    
    assert res["available"] is True
    assert res["allow_paper_recommendations"] is False
    assert res["status"] == "STALE"
    assert res["observation_age_minutes"] == 91.0
    assert "Weather observation is stale" in res["no_trade_reason"]

def test_missing_recent_observations_table_blocks():
    """Scenario 5: Missing recent_observations_table blocks."""
    snapshot = get_base_valid_snapshot()
    snapshot["recent_observations_table"] = []
    now_utc = get_test_reference_now()
    res = assess_nws_snapshot(snapshot, now_utc=now_utc)
    
    assert res["available"] is True
    assert res["allow_paper_recommendations"] is False
    assert res["status"] == "ERROR"
    assert res["required_fields_present"] is False
    assert "recent_observations_table" in res["no_trade_reason"]

def test_missing_snapshot_blocks():
    """Scenario 6: Missing snapshot blocks."""
    res = assess_nws_snapshot(None)
    
    assert res["available"] is False
    assert res["allow_paper_recommendations"] is False
    assert res["status"] == "MISSING"
    assert res["required_fields_present"] is False

def test_naive_timestamp_blocks():
    """Scenario 7: Naive timestamp blocks."""
    snapshot = get_base_valid_snapshot()
    snapshot["latest_observation_time"] = "2026-05-15T20:00:00"  # Naive
    now_utc = get_test_reference_now()
    res = assess_nws_snapshot(snapshot, now_utc=now_utc)
    
    assert res["available"] is True
    assert res["allow_paper_recommendations"] is False
    assert res["status"] == "ERROR"
    assert res["required_fields_present"] is False
    assert "naive" in res["no_trade_reason"]

def test_missing_safety_no_real_trading_blocks():
    """Scenario 8: Missing safety.no_real_trading blocks."""
    snapshot = get_base_valid_snapshot()
    # Missing completely
    snapshot.pop("safety")
    now_utc = get_test_reference_now()
    res = assess_nws_snapshot(snapshot, now_utc=now_utc)
    
    assert res["available"] is True
    assert res["allow_paper_recommendations"] is False
    assert res["status"] == "ERROR"
    assert res["required_fields_present"] is False
    
    # Or False
    snapshot2 = get_base_valid_snapshot()
    snapshot2["safety"] = {"no_real_trading": False}
    res2 = assess_nws_snapshot(snapshot2, now_utc=now_utc)
    assert res2["allow_paper_recommendations"] is False

def test_endpoint_status_error_blocks():
    """Scenario 9: endpoint_status=ERROR blocks."""
    snapshot = get_base_valid_snapshot()
    snapshot["endpoint_status"] = "ERROR"
    now_utc = get_test_reference_now()
    res = assess_nws_snapshot(snapshot, now_utc=now_utc)
    
    assert res["available"] is True
    assert res["allow_paper_recommendations"] is False
    assert res["status"] == "ERROR"
    assert "endpoint_status" in res["no_trade_reason"]

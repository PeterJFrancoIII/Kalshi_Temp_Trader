import json
import sys
from datetime import datetime, timezone
from backtesting.replay_manifest import build_replay_manifest, validate_replay_manifest

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def test_artifact_before_decision_time_eligible():
    decision_time = "2026-05-06T14:00:00+00:00"
    artifacts = [
        {
            "artifact_type": "forecast",
            "path": "forecast_1.json",
            "embedded_timestamp_utc": "2026-05-06T13:00:00+00:00",
            "as_of_time_utc": "2026-05-06T13:00:00+00:00",
            "source": "nws",
            "required_for_decision": True
        }
    ]
    manifest = build_replay_manifest(decision_time, artifacts)
    assert len(manifest["eligible_artifacts"]) == 1
    assert len(manifest["excluded_artifacts"]) == 0
    assert len(manifest["lookahead_errors"]) == 0
    
    errors = validate_replay_manifest(manifest)
    assert len(errors) == 0

def test_artifact_after_decision_time_excluded():
    decision_time = "2026-05-06T14:00:00+00:00"
    artifacts = [
        {
            "artifact_type": "forecast",
            "path": "forecast_2.json",
            "embedded_timestamp_utc": "2026-05-06T14:01:00+00:00",
            "as_of_time_utc": "2026-05-06T14:01:00+00:00",
            "source": "nws",
            "required_for_decision": False
        }
    ]
    manifest = build_replay_manifest(decision_time, artifacts)
    assert len(manifest["eligible_artifacts"]) == 0
    assert len(manifest["excluded_artifacts"]) == 1
    assert manifest["excluded_artifacts"][0]["exclusion_reason"] == "future_artifact_excluded"
    assert len(manifest["lookahead_errors"]) == 0
    assert len(manifest["warnings"]) == 1

def test_required_artifact_after_decision_time_creates_lookahead_error():
    decision_time = "2026-05-06T14:00:00+00:00"
    artifacts = [
        {
            "artifact_type": "forecast",
            "path": "forecast_3.json",
            "embedded_timestamp_utc": "2026-05-06T14:01:00+00:00",
            "as_of_time_utc": "2026-05-06T14:01:00+00:00",
            "source": "nws",
            "required_for_decision": True
        }
    ]
    manifest = build_replay_manifest(decision_time, artifacts)
    assert len(manifest["eligible_artifacts"]) == 0
    assert len(manifest["excluded_artifacts"]) == 1
    assert len(manifest["lookahead_errors"]) == 1
    assert "in the future" in manifest["lookahead_errors"][0]
    
    errors = validate_replay_manifest(manifest)
    assert len(errors) == 1
    assert "in the future" in errors[0]

def test_missing_timestamp_on_required_artifact_creates_lookahead_error():
    decision_time = "2026-05-06T14:00:00+00:00"
    artifacts = [
        {
            "artifact_type": "forecast",
            "path": "forecast_4.json",
            "embedded_timestamp_utc": None,
            "as_of_time_utc": None,
            "source": "nws",
            "required_for_decision": True
        }
    ]
    manifest = build_replay_manifest(decision_time, artifacts)
    assert len(manifest["eligible_artifacts"]) == 0
    assert len(manifest["excluded_artifacts"]) == 1
    assert len(manifest["lookahead_errors"]) == 1
    assert "missing both" in manifest["lookahead_errors"][0]
    
    errors = validate_replay_manifest(manifest)
    assert len(errors) == 1
    assert "missing both" in errors[0]

def test_naive_decision_time_fails_validation():
    decision_time = "2026-05-06T14:00:00"  # Naive
    artifacts = [
        {
            "artifact_type": "forecast",
            "path": "forecast_5.json",
            "embedded_timestamp_utc": "2026-05-06T13:00:00+00:00",
            "as_of_time_utc": "2026-05-06T13:00:00+00:00",
            "source": "nws",
            "required_for_decision": True
        }
    ]
    manifest = build_replay_manifest(decision_time, artifacts)
    assert len(manifest["lookahead_errors"]) >= 1
    assert "naive" in manifest["lookahead_errors"][0] or "lacks timezone" in manifest["lookahead_errors"][0]
    
    errors = validate_replay_manifest(manifest)
    assert len(errors) >= 1
    assert any("naive" in e or "lacks timezone" in e for e in errors)

def test_naive_artifact_timestamp_fails_validation():
    decision_time = "2026-05-06T14:00:00+00:00"
    artifacts = [
        {
            "artifact_type": "forecast",
            "path": "forecast_6.json",
            "embedded_timestamp_utc": "2026-05-06T13:00:00",  # Naive
            "as_of_time_utc": "2026-05-06T13:00:00",  # Naive
            "source": "nws",
            "required_for_decision": True
        }
    ]
    manifest = build_replay_manifest(decision_time, artifacts)
    assert len(manifest["lookahead_errors"]) >= 1
    assert "naive" in manifest["lookahead_errors"][0] or "lacks timezone" in manifest["lookahead_errors"][0]
    
    errors = validate_replay_manifest(manifest)
    assert len(errors) >= 1
    assert any("naive" in e or "lacks timezone" in e for e in errors)

def test_filesystem_mtime_not_required_or_consulted():
    decision_time = "2026-05-06T14:00:00+00:00"
    artifacts = [
        {
            "artifact_type": "forecast",
            "path": "forecast_7.json",
            "embedded_timestamp_utc": "2026-05-06T13:00:00+00:00",
            "as_of_time_utc": "2026-05-06T13:00:00+00:00",
            "source": "nws",
            "required_for_decision": True,
            "mtime": 123456789.0  # forbidden key
        }
    ]
    manifest = build_replay_manifest(decision_time, artifacts)
    errors = validate_replay_manifest(manifest)
    assert len(errors) >= 1
    assert any("Forbidden filesystem metadata key" in e for e in errors)

def test_settlement_artifact_before_settlement_as_of_time_excluded():
    decision_time = "2026-05-06T14:00:00+00:00"
    artifacts = [
        {
            "artifact_type": "settlement",
            "path": "settlement_data.json",
            "embedded_timestamp_utc": "2026-05-06T14:00:00+00:00",
            "as_of_time_utc": "2026-05-06T14:00:00+00:00",
            "settlement_as_of_time_utc": "2026-05-07T06:00:00+00:00",
            "source": "nws_settlement",
            "required_for_decision": True
        }
    ]
    manifest = build_replay_manifest(decision_time, artifacts)
    assert len(manifest["eligible_artifacts"]) == 0
    assert len(manifest["excluded_artifacts"]) == 1
    assert manifest["excluded_artifacts"][0]["exclusion_reason"] == "settlement_before_availability_time"
    assert len(manifest["lookahead_errors"]) == 1
    assert "not available at decision time" in manifest["lookahead_errors"][0]
    
    errors = validate_replay_manifest(manifest)
    assert len(errors) == 1
    assert "not available at decision time" in errors[0]

def test_manifest_is_json_serializable():
    decision_time = "2026-05-06T14:00:00+00:00"
    artifacts = [
        {
            "artifact_type": "forecast",
            "path": "forecast_8.json",
            "embedded_timestamp_utc": "2026-05-06T13:00:00+00:00",
            "as_of_time_utc": "2026-05-06T13:00:00+00:00",
            "source": "nws",
            "required_for_decision": True
        }
    ]
    manifest = build_replay_manifest(decision_time, artifacts)
    serialized = json.dumps(manifest)
    deserialized = json.loads(serialized)
    assert deserialized["decision_time_utc"] == decision_time

if __name__ == "__main__":
    tests = [
        test_artifact_before_decision_time_eligible,
        test_artifact_after_decision_time_excluded,
        test_required_artifact_after_decision_time_creates_lookahead_error,
        test_missing_timestamp_on_required_artifact_creates_lookahead_error,
        test_naive_decision_time_fails_validation,
        test_naive_artifact_timestamp_fails_validation,
        test_filesystem_mtime_not_required_or_consulted,
        test_settlement_artifact_before_settlement_as_of_time_excluded,
        test_manifest_is_json_serializable,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"FAIL: {t.__name__} — {e}")
            failed += 1
    print(f"\n{'ALL TESTS PASSED.' if not failed else f'{failed} TESTS FAILED.'}")
    sys.exit(failed)

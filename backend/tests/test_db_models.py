"""
Tests for backend/src/db/models.py
P0 Fix 1: Verify DailyPrediction has model_version column.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from db.models import DailyPredictionRecord, ValidationStatus


def test_daily_prediction_has_model_version():
    """DailyPredictionRecord must define a model_version column attribute."""
    assert hasattr(DailyPredictionRecord, "model_version"), (
        "DailyPredictionRecord is missing the model_version column. "
        "run_daily_prediction.py will crash on non-dry-run saves."
    )


def test_daily_prediction_model_version_default():
    """model_version column must have a default of 'rules_v1'."""
    col = DailyPredictionRecord.__table__.c.get("model_version")
    assert col is not None, "model_version column not found in DailyPredictionRecord table"
    # Check the SQLAlchemy column default
    assert col.default is not None, "model_version column has no default"
    # The default arg is stored as a ColumnDefault; .arg holds the value
    assert col.default.arg == "rules_v1", (
        f"Expected default 'rules_v1', got '{col.default.arg}'"
    )


def test_daily_prediction_model_version_v2():
    """DailyPredictionRecord can be constructed with model_version='rules_v2_climatology'."""
    pred = DailyPredictionRecord(
        run_id="test-run-v2",
        date="2026-05-03",
        station="KMIA",
        model_version="rules_v2_climatology",
        best_single_number_f=82.0,
        prob_le_78=0.05,
        prob_79_80=0.10,
        prob_81_82=0.50,
        prob_83_84=0.20,
        prob_85_86=0.10,
        prob_ge_87=0.05,
        confidence="medium",
        main_drivers=["NWS forecast high: 83F"],
        warnings=[],
        status=ValidationStatus.PENDING,
    )
    assert pred.model_version == "rules_v2_climatology"
    assert pred.run_id == "test-run-v2"
    assert pred.prob_81_82 == 0.50


if __name__ == "__main__":
    test_daily_prediction_has_model_version()
    print("PASS: test_daily_prediction_has_model_version")
    test_daily_prediction_model_version_default()
    print("PASS: test_daily_prediction_model_version_default")
    test_daily_prediction_model_version_v2()
    print("PASS: test_daily_prediction_model_version_v2")

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timezone
from backend.src.scheduler.jobs import refresh_live_observations
from backend.src.scheduler.run_daily_prediction import run_prediction_pipeline
from backend.src.scheduler.settlement_check import run_settlement_check
from backend.src.db.models import LiveObservation, DailyPrediction, ClimiaReport, WeatherSnapshot

@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

@patch('backend.src.scheduler.jobs.SessionLocal')
@patch('backend.src.scheduler.jobs.fetch_wrh_timeseries')
@patch('backend.src.scheduler.jobs.parse_wrh_timeseries')
def test_refresh_live_observations(mock_parse, mock_fetch, mock_session_local, mock_db):
    mock_session_local.return_value = mock_db
    
    # Setup mock data
    mock_fetch.return_value = {"fake": "json"}
    mock_obs = MagicMock()
    mock_obs.timestamp = datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc)
    mock_obs.temperature_f = 82
    mock_obs.dewpoint_f = 70
    mock_obs.wind_direction = 90
    mock_obs.wind_speed_mph = 10
    mock_obs.weather_condition = "Sunny"
    
    mock_parse.return_value = [mock_obs]
    
    # Mock DB query to return None (no existing observation)
    mock_db.query().filter().first.return_value = None
    
    refresh_live_observations()
    
    # Verify DB add was called
    assert mock_db.add.called
    added_obj = mock_db.add.call_args[0][0]
    assert isinstance(added_obj, LiveObservation)
    assert added_obj.temperature_f == 82

@patch('backend.src.scheduler.run_daily_prediction.SessionLocal')
@patch('backend.src.scheduler.run_daily_prediction.RulesBasedForecaster')
def test_run_prediction_pipeline(mock_forecaster_cls, mock_session_local, mock_db):
    mock_session_local.return_value = mock_db
    
    # Setup mock forecaster
    mock_forecaster = mock_forecaster_cls.return_value
    mock_pred_output = MagicMock()
    mock_pred_output.best_single_number_f = 85
    mock_pred_output.probability_bins = {"85-86": 0.6, "83-84": 0.3, "<=78": 0.0, "79-80": 0.0, "81-82": 0.0, ">=87": 0.1}
    mock_pred_output.confidence = "medium"
    mock_pred_output.main_drivers = ["Test driver"]
    mock_pred_output.warnings = []
    mock_forecaster.generate_daily_prediction.return_value = mock_pred_output
    
    # Setup mock data in DB
    mock_obs = MagicMock()
    mock_obs.id = 1
    mock_obs.timestamp = datetime.now()
    mock_obs.observed_max_so_far_f = 80
    mock_obs.temperature_f = 80
    mock_obs.rain_flag = False
    mock_obs.thunderstorm_flag = False
    mock_obs.overcast_flag = False
    
    # Mock query for live observation
    mock_db.query().filter().order_by().first.side_effect = [
        None, # Idempotency check: no recent prediction
        mock_obs, # Latest live observation
        None, # Latest forecast snapshot
        None  # Latest climia report
    ]
    
    run_prediction_pipeline(target_date=date(2026, 5, 3))
    
    # Verify prediction was saved
    assert mock_db.add.call_count >= 2 # WeatherSnapshot and DailyPrediction
    
@patch('backend.src.scheduler.settlement_check.SessionLocal')
@patch('backend.src.scheduler.settlement_check.fetch_climia_report')
@patch('backend.src.scheduler.settlement_check.parse_climia_report')
def test_run_settlement_check(mock_parse, mock_fetch, mock_session_local, mock_db):
    mock_session_local.return_value = mock_db
    
    # Setup mock report
    mock_report = MagicMock()
    mock_report.date = date(2026, 5, 3)
    mock_report.observed_max_f = 84
    mock_parse.return_value = mock_report
    
    # Mock DB queries
    mock_db.query().filter().first.return_value = None # No existing report
    
    mock_pred = MagicMock()
    mock_pred.id = 101
    mock_pred.run_id = "test_run"
    mock_pred.date = "2026-05-03"
    mock_pred.best_single_number_f = 83
    # Probabilities
    mock_pred.prob_le_78 = 0.0
    mock_pred.prob_79_80 = 0.0
    mock_pred.prob_81_82 = 0.1
    mock_pred.prob_83_84 = 0.7
    mock_pred.prob_85_86 = 0.2
    mock_pred.prob_ge_87 = 0.0
    
    mock_db.query().filter().all.return_value = [mock_pred] # One prediction found
    mock_db.query().filter().first.side_effect = [None, None] # No existing report, No existing settlement
    
    run_settlement_check(target_date=date(2026, 5, 3))
    
    # Verify settlement and metrics were added
    # 1. ClimiaReport
    # 2. Settlement
    # 3. CalibrationMetric
    assert mock_db.add.call_count >= 3

import pytest
import os
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import (
    Base,
    LiveObservation,
    ForecastSnapshot,
    DailyPredictionRecord,
    Settlement,
    ClimiaReportRecord,
)
from calibration.reports import process_settlements_for_date
from scheduler.run_daily_prediction import run_prediction_pipeline

# Setup Test DB
TEST_DB = "test_kalshi.db"
DATABASE_URL = f"sqlite:///{TEST_DB}"
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_full_pipeline_flow(db, monkeypatch):
    # 1. Setup Mock Data in DB
    # Live Obs
    obs = LiveObservation(
        timestamp=datetime(2026, 5, 3, 17, 5),
        station="KMIA",
        temperature_f=81.0,
        observed_max_so_far_f=82.0,
        weather_condition="Fair"
    )
    db.add(obs)
    
    # Forecast
    forecast = ForecastSnapshot(
        date="2026-05-03",
        station="KMIA",
        forecast_high_f=84.0
    )
    db.add(forecast)
    db.commit()

    # 2. Monkeypatch session to use our test db
    from db import session
    monkeypatch.setattr(session, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(session, "engine", engine)

    # 3. Run Prediction
    target_date = date(2026, 5, 3)
    run_prediction_pipeline(target_date=target_date, force=True)
    
    # Verify prediction saved
    pred = db.query(DailyPredictionRecord).filter(DailyPredictionRecord.date == "2026-05-03").first()
    assert pred is not None
    assert pred.best_single_number_f > 0
    # Check bin zeroing (observed max 82 should zero out <=78 and 79-80)
    assert pred.prob_le_78 == 0.0
    assert pred.prob_79_80 == 0.0

    # 4. Run Settlement
    # Mock CLIMIA Report in DB
    climia = ClimiaReportRecord(
        date="2026-05-03",
        station="KMIA",
        max_temp_f=82,
        normal_high_f=84,
    )
    db.add(climia)
    db.commit()
    
    process_settlements_for_date(db, "2026-05-03")
    
    # Verify settlement saved
    settlement = db.query(Settlement).filter(Settlement.prediction_id == pred.id).first()
    assert settlement is not None
    assert settlement.actual_high_f == 82
    assert settlement.actual_bin == "81-82"
    
    # Verify metrics
    metrics = settlement.metrics
    assert metrics is not None
    assert metrics.winning_bin == "81-82"
    assert metrics.brier_score >= 0

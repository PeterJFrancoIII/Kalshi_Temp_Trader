from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class ValidationStatus(str, enum.Enum):
    PENDING = "PENDING"
    VALID = "VALID"
    INVALID = "INVALID"

class RecommendationAction(str, enum.Enum):
    WATCH = "WATCH"
    TRADE_CANDIDATE = "TRADE_CANDIDATE"
    REJECT = "REJECT"

class ClimiaReportRecord(Base):
    """ORM row for the final ground-truth climatological data (CLIMIA).

    Renamed from ``ClimiaReport`` to disambiguate from the Pydantic model
    of the same name in :mod:`shared.types`. A backward-compat alias
    ``ClimiaReport`` is kept at module-end for older callers.
    """
    __tablename__ = 'climia_reports'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, index=True) # YYYY-MM-DD
    station = Column(String, default="KMIA")
    raw_text = Column(String)
    max_temp_f = Column(Integer, nullable=True)
    min_temp_f = Column(Integer, nullable=True)
    precipitation_inches = Column(Float, nullable=True)
    normal_high_f = Column(Integer, nullable=True)
    normal_low_f = Column(Integer, nullable=True)
    record_high_f = Column(Integer, nullable=True)
    record_low_f = Column(Integer, nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

class LiveObservation(Base):
    """
    Preliminary weather observations from KMIA sensors.
    Used for nowcasting and hard sensor constraints.
    """
    __tablename__ = 'live_observations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), index=True)
    station = Column(String, default="KMIA")
    temperature_f = Column(Float)
    observed_max_so_far_f = Column(Float)
    dewpoint_f = Column(Float, nullable=True)
    wind_direction = Column(String, nullable=True)
    wind_speed_mph = Column(Float, nullable=True)
    weather_condition = Column(String, nullable=True)
    rain_flag = Column(Boolean, default=False)
    thunderstorm_flag = Column(Boolean, default=False)
    overcast_flag = Column(Boolean, default=False)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

class ForecastSnapshot(Base):
    """
    Snapshot of NWS forecast guidance for KMIA on a specific date.
    """
    __tablename__ = 'forecast_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, index=True) # YYYY-MM-DD
    station = Column(String, default="KMIA")
    forecast_high_f = Column(Float)
    forecast_text = Column(String, nullable=True)
    raw_data = Column(JSON, nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

class KalshiMarket(Base):
    """
    Metadata for Kalshi KMIA temperature markets.
    """
    __tablename__ = 'kalshi_markets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, index=True, unique=True)
    date = Column(String, index=True) # YYYY-MM-DD target
    title = Column(String)
    bin_range_str = Column(String)
    open_time = Column(DateTime(timezone=True))
    close_time = Column(DateTime(timezone=True))
    status = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    
    orderbooks = relationship("KalshiOrderbook", back_populates="market", cascade="all, delete-orphan")

class KalshiOrderbook(Base):
    """
    Snapshot of Kalshi order book depth and implied probabilities.
    """
    __tablename__ = 'kalshi_orderbooks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(Integer, ForeignKey('kalshi_markets.id', ondelete="CASCADE"))
    yes_bid = Column(Float, nullable=True)
    yes_ask = Column(Float, nullable=True)
    no_bid = Column(Float, nullable=True)
    no_ask = Column(Float, nullable=True)
    implied_probability = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    
    market = relationship("KalshiMarket", back_populates="orderbooks")

class WeatherSnapshotRecord(Base):
    """ORM row aggregating live + forecast weather state.

    Renamed from ``WeatherSnapshot`` to disambiguate from the Pydantic
    model of the same name in :mod:`shared.types`. Backward-compat alias
    preserved at module end.
    """
    __tablename__ = 'weather_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, index=True) # YYYY-MM-DD
    station = Column(String, default="KMIA")
    latest_live_obs_id = Column(Integer, ForeignKey('live_observations.id'))
    latest_forecast_id = Column(Integer, ForeignKey('forecast_snapshots.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DailyPredictionRecord(Base):
    """ORM row for the daily probabilistic prediction.

    Renamed from ``DailyPrediction`` to disambiguate from the Pydantic
    model of the same name in :mod:`shared.types`. Backward-compat alias
    preserved at module end.
    """
    __tablename__ = 'daily_predictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, index=True, unique=True)
    date = Column(String, index=True) # YYYY-MM-DD target date
    station = Column(String, default="KMIA")
    model_version = Column(String, index=True, nullable=False, default="rules_v1")  # e.g. "rules_v1", "rules_v2_climatology"
    snapshot_id = Column(Integer, ForeignKey('weather_snapshots.id'))
    
    best_single_number_f = Column(Float)
    prob_le_78 = Column(Float)
    prob_79_80 = Column(Float)
    prob_81_82 = Column(Float)
    prob_83_84 = Column(Float)
    prob_85_86 = Column(Float)
    prob_ge_87 = Column(Float)
    
    confidence = Column(String)
    main_drivers = Column(JSON)
    warnings = Column(JSON)
    status = Column(Enum(ValidationStatus), default=ValidationStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    llm_review = relationship("LlmReview", back_populates="prediction", uselist=False, cascade="all, delete-orphan")
    recommendation = relationship("RecommendationRecord", back_populates="prediction", uselist=False, cascade="all, delete-orphan")
    settlement = relationship("Settlement", back_populates="prediction", uselist=False, cascade="all, delete-orphan")

class LlmReview(Base):
    """
    Audit log of LLM sanity checks and consensus results.
    """
    __tablename__ = 'llm_reviews'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey('daily_predictions.id', ondelete="CASCADE"))
    raw_prompt = Column(String)
    raw_response = Column(String)
    llm_confidence = Column(String, nullable=True)
    llm_warnings = Column(JSON, nullable=True)
    discrepancy_flag = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    prediction = relationship("DailyPredictionRecord", back_populates="llm_review")

class RecommendationRecord(Base):
    """ORM row for an automated trade recommendation.

    Renamed from ``Recommendation`` to disambiguate from the dataclass of
    the same name in :mod:`recommendation.types` and the Pydantic model in
    :mod:`shared.types`. Backward-compat alias preserved at module end.
    """
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey('daily_predictions.id', ondelete="CASCADE"))
    action = Column(Enum(RecommendationAction))
    reasoning = Column(String)
    target_bin = Column(String, nullable=True)
    expected_value = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    prediction = relationship("DailyPredictionRecord", back_populates="recommendation")

class Settlement(Base):
    """
    Links a prediction to its final ground-truth outcome and records basic results.
    """
    __tablename__ = 'settlements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey('daily_predictions.id', ondelete="CASCADE"))
    climia_report_id = Column(Integer, ForeignKey('climia_reports.id'))
    date = Column(String, index=True)
    actual_high_f = Column(Integer)
    actual_bin = Column(String)
    settled_at = Column(DateTime(timezone=True), server_default=func.now())
    
    prediction = relationship("DailyPredictionRecord", back_populates="settlement")
    metrics = relationship("CalibrationMetric", back_populates="settlement", uselist=False, cascade="all, delete-orphan")

class CalibrationMetric(Base):
    """
    Detailed statistical performance metrics for a specific settlement.
    """
    __tablename__ = 'calibration_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    settlement_id = Column(Integer, ForeignKey('settlements.id', ondelete="CASCADE"))
    brier_score = Column(Float)
    log_loss = Column(Float)
    absolute_error = Column(Float)
    top_predicted_bin = Column(String)
    winning_bin = Column(String)
    top_bin_hit = Column(Boolean)
    calibration_bin = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    settlement = relationship("Settlement", back_populates="metrics")


# --- Backward-compat aliases ---------------------------------------------
# These keep older imports working while callers migrate to the *Record
# names. The aliases share identity with the renamed classes — they are
# the SAME class, not subclasses — so SQLAlchemy sees one mapping and
# isinstance() checks behave identically.
#
# New code MUST use the *Record names. The invariant test
# `test_orm_models_use_record_suffix` enforces this for backend/src.
ClimiaReport = ClimiaReportRecord
WeatherSnapshot = WeatherSnapshotRecord
DailyPrediction = DailyPredictionRecord
Recommendation = RecommendationRecord

import math
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date, datetime

REQUIRED_BINS = ["<=78", "79-80", "81-82", "83-84", "85-86", ">=87"]


class TemperatureBins(BaseModel):
    bins: Dict[str, float]

    @field_validator("bins")
    @classmethod
    def validate_bins(cls, v: Dict[str, float]) -> Dict[str, float]:
        # Check that probabilities are between 0 and 1
        for b, prob in v.items():
            if not (0.0 <= prob <= 1.0):
                raise ValueError(f"Probability for bin {b} must be between 0 and 1, got {prob}")
        
        # Check that sum is approximately 1
        total_prob = sum(v.values())
        if not math.isclose(total_prob, 1.0, abs_tol=0.01):
            raise ValueError(f"Sum of probabilities must be approximately 1, got {total_prob}")
            
        return v

class WeatherSnapshot(BaseModel):
    station: str
    timestamp: datetime
    current_temp_f: Optional[int] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    dewpoint_f: Optional[float] = None
    overcast_flag: bool = False
    thunderstorm_flag: bool = False
    recent_rain_flag: bool = False

class DailyPrediction(BaseModel):
    station: str = "KMIA"
    date: date
    metric: str = "daily_max_temperature_f"
    best_single_number_f: int
    probability_bins: Dict[str, float]
    observed_max_so_far_f: int
    current_temp_f: int
    forecast_high_f: int
    confidence: Literal["low", "medium", "high"]
    main_drivers: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Lookahead safety timestamps
    prediction_timestamp: Optional[datetime] = None
    source_weather_timestamp: Optional[datetime] = None
    market_snapshot_timestamp: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_lookahead(self) -> "DailyPrediction":
        if self.source_weather_timestamp and self.prediction_timestamp:
            if self.source_weather_timestamp > self.prediction_timestamp:
                raise ValueError("Source weather timestamp cannot be after prediction timestamp")
        if self.market_snapshot_timestamp and self.prediction_timestamp:
            if self.market_snapshot_timestamp > self.prediction_timestamp:
                raise ValueError("Market snapshot timestamp cannot be after prediction timestamp")
        return self

    @field_validator("station")
    @classmethod
    def validate_station(cls, v: str) -> str:
        if v != "KMIA":
            raise ValueError("Station must be KMIA")
        return v

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str) -> str:
        if v != "daily_max_temperature_f":
            raise ValueError("Metric must be daily_max_temperature_f")
        return v

    @field_validator("probability_bins")
    @classmethod
    def validate_probability_bins(cls, v: Dict[str, float]) -> Dict[str, float]:
        TemperatureBins(bins=v)  # Reuse validation from TemperatureBins
        return v

class ClimiaReport(BaseModel):
    report_date: date
    issue_time: Optional[str] = None
    station_name: str = "KMIA"
    max_temp_f: Optional[int] = None
    max_temp_time: Optional[str] = None
    min_temp_f: Optional[int] = None
    min_temp_time: Optional[str] = None
    avg_temp_f: Optional[float] = None
    departure_from_normal_f: Optional[float] = None
    normal_high_f: Optional[int] = None
    normal_low_f: Optional[int] = None
    record_high_f: Optional[int] = None
    record_low_f: Optional[int] = None
    is_record_max: bool = False
    is_record_min: bool = False
    record_flags: List[str] = Field(default_factory=list)
    precipitation_in: Optional[float] = None
    trace_precip_flag: bool = False
    is_correction: bool = False
    raw_text: str = ""
    parse_warnings: List[str] = Field(default_factory=list)

class LiveObservation(BaseModel):
    timestamp: datetime
    station: str = "KMIA"
    observed_max_so_far_f: int
    current_temp_f: int
    remaining_daylight_hours: float

class ForecastSnapshot(BaseModel):
    date: date
    station: str = "KMIA"
    forecast_high_f: int

class KalshiMarketSnapshot(BaseModel):
    timestamp: datetime
    ticker: str
    bin_prices: Dict[str, float]  # e.g., {"81-82": 0.45}

class Recommendation(BaseModel):
    timestamp: datetime
    suggested_action: str
    rationale: str
    target_bins: List[str]
    expected_value: float

class HistoricalWeatherRecord(BaseModel):
    station: str = "KMIA"
    date: date
    max_temp_f: Optional[int] = None
    source: str
    raw_source_id: Optional[str] = None
    quality_flags: List[str] = Field(default_factory=list)


class ContractBin(BaseModel):
    ticker: str
    event_ticker: Optional[str] = None
    label: str
    contract_range: Optional[str] = None
    condition_type: Literal["above", "below", "between", "unknown"]
    lower_f: Optional[int] = None
    upper_f: Optional[int] = None
    lower_inclusive: bool = True
    upper_inclusive: bool = True
    source: str = "kalshi"
    raw_title: Optional[str] = None
    raw_subtitle: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    def contains(self, temp_f: int) -> bool:
        """Checks if a given temperature falls within this contract's range."""
        if self.lower_f is not None:
            if self.lower_inclusive:
                if temp_f < self.lower_f:
                    return False
            else:
                if temp_f <= self.lower_f:
                    return False
                    
        if self.upper_f is not None:
            if self.upper_inclusive:
                if temp_f > self.upper_f:
                    return False
            else:
                if temp_f >= self.upper_f:
                    return False
                    
        return True

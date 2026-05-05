import pytest
from src.forecasting.rules_model import RulesBasedForecaster
from datetime import datetime
import pytz

ET = pytz.timezone('US/Eastern')

def test_observed_max_82_zeros_lower_bins():
    forecaster = RulesBasedForecaster()
    # Mock data
    dt = datetime(2026, 5, 3).date()
    current_time = datetime(2026, 5, 3, 14, 0, tzinfo=ET)
    
    # Obs max 82
    prediction = forecaster.generate_daily_prediction(
        date_obj=dt,
        observed_max_so_far_f=82,
        current_temp_f=81,
        forecast_high_f=84,
        current_time_et=current_time,
        normal_high_f=84
    )
    
    assert prediction.probability_bins["<=78"] == 0.0
    assert prediction.probability_bins["79-80"] == 0.0
    assert prediction.probability_bins["81-82"] > 0.0

def test_observed_max_85_zeros_lower_bins():
    forecaster = RulesBasedForecaster()
    dt = datetime(2026, 5, 3).date()
    current_time = datetime(2026, 5, 3, 14, 0, tzinfo=ET)
    
    # Obs max 85
    prediction = forecaster.generate_daily_prediction(
        date_obj=dt,
        observed_max_so_far_f=85,
        current_temp_f=84,
        forecast_high_f=86,
        current_time_et=current_time,
        normal_high_f=84
    )
    
    assert prediction.probability_bins["<=78"] == 0.0
    assert prediction.probability_bins["79-80"] == 0.0
    assert prediction.probability_bins["81-82"] == 0.0
    assert prediction.probability_bins["83-84"] == 0.0
    assert prediction.probability_bins["85-86"] > 0.0

def test_probability_sums_to_one():
    forecaster = RulesBasedForecaster()
    dt = datetime(2026, 5, 3).date()
    current_time = datetime(2026, 5, 3, 14, 0, tzinfo=ET)
    
    prediction = forecaster.generate_daily_prediction(
        date_obj=dt,
        observed_max_so_far_f=80,
        current_temp_f=79,
        forecast_high_f=83,
        current_time_et=current_time,
        normal_high_f=84
    )
    
    total_prob = sum(prediction.probability_bins.values())
    assert abs(total_prob - 1.0) < 0.005

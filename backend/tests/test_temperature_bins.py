import math
from datetime import date, datetime
from forecasting.bin_converter import temp_to_bin
from forecasting.rules_model import (
    forecast_daily_high_bins, 
    validate_probability_bins, 
    zero_impossible_bins, 
    normalize_bins
)

def test_zeroing_82():
    """Test zeroing rule for observed max = 82."""
    res = forecast_daily_high_bins(observed_max_so_far_f=82, forecast_high_f=84)
    probs = res["probability_bins"]
    assert probs["<=78"] == 0
    assert probs["79-80"] == 0
    assert probs["81-82"] >= 0

def test_zeroing_85():
    """Test zeroing rule for observed max = 85."""
    res = forecast_daily_high_bins(observed_max_so_far_f=85, forecast_high_f=84)
    probs = res["probability_bins"]
    assert probs["<=78"] == 0
    assert probs["79-80"] == 0
    assert probs["81-82"] == 0
    assert probs["83-84"] == 0
    assert probs["85-86"] >= 0

def test_temp_82_maps():
    """Final temp 82 maps to 81-82."""
    assert temp_to_bin(82) == "81-82"

def test_sum_to_one():
    """Probabilities should sum to approximately 1.0."""
    res = forecast_daily_high_bins(observed_max_so_far_f=81, forecast_high_f=84)
    total = sum(res["probability_bins"].values())
    assert abs(total - 1.0) < 0.01

def test_all_bins_present():
    """All required bins must be present."""
    res = forecast_daily_high_bins(observed_max_so_far_f=81, forecast_high_f=84)
    required = ["<=78", "79-80", "81-82", "83-84", "85-86", ">=87"]
    for b in required:
        assert b in res["probability_bins"]

def test_warning_missing_forecast():
    """Missing forecast_high_f produces warning."""
    res = forecast_daily_high_bins(observed_max_so_far_f=81, forecast_high_f=None)
    assert any("forecast_high_f is missing" in w for w in res["warnings"])

def test_warning_stale_data():
    """Stale live data produces warning."""
    res = forecast_daily_high_bins(observed_max_so_far_f=81, forecast_high_f=84, live_data_stale=True)
    assert any("live data is stale" in w for w in res["warnings"])

def test_temp_to_bin_logic():
    """Verify temp_to_bin maps correctly across boundaries."""
    assert temp_to_bin(77) == "<=78"
    assert temp_to_bin(78) == "<=78"
    assert temp_to_bin(79) == "79-80"
    assert temp_to_bin(80) == "79-80"
    assert temp_to_bin(81) == "81-82"
    assert temp_to_bin(82) == "81-82"
    assert temp_to_bin(83) == "83-84"
    assert temp_to_bin(84) == "83-84"
    assert temp_to_bin(85) == "85-86"
    assert temp_to_bin(86) == "85-86"
    assert temp_to_bin(87) == ">=87"
    assert temp_to_bin(90) == ">=87"

def test_validate_probability_bins_logic():
    """Validation should catch missing bins or bad probabilities."""
    good_bins = {b: 1.0/6.0 for b in ["<=78", "79-80", "81-82", "83-84", "85-86", ">=87"]}
    validate_probability_bins(good_bins) # Should not raise
    
    bad_bins = good_bins.copy()
    del bad_bins["<=78"]
    try:
        validate_probability_bins(bad_bins)
        assert False, "Should have raised ValueError for missing bin"
    except ValueError:
        pass

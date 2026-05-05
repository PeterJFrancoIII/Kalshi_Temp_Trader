import math
import pytest
from src.calibration.metrics import (
    top_bin,
    brier_score_multiclass,
    log_loss_multiclass,
    score_prediction,
    validate_probabilities
)
from src.forecasting.bin_converter import temp_to_bin

def test_temp_to_bin_logic():
    # final high 82 maps to actual bin 81-82
    assert temp_to_bin(82) == "81-82"
    assert temp_to_bin(78) == "<=78"
    assert temp_to_bin(87) == ">=87"

def test_top_bin_logic():
    probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.6, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    # top-bin hit true when 81-82 has highest probability
    assert top_bin(probs) == "81-82"
    
    probs_low = {"<=78": 0.6, "79-80": 0.1, "81-82": 0.1, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    # top-bin hit false when another bin has highest probability
    assert top_bin(probs_low) == "<=78"

def test_score_prediction_hits():
    probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.6, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    result = score_prediction(probs, 82)
    assert result["top_bin_hit"] is True
    assert result["actual_bin"] == "81-82"
    assert result["top_predicted_bin"] == "81-82"

    probs_miss = {"<=78": 0.6, "79-80": 0.1, "81-82": 0.1, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    result_miss = score_prediction(probs_miss, 82)
    assert result_miss["top_bin_hit"] is False
    assert result_miss["actual_bin"] == "81-82"
    assert result_miss["top_predicted_bin"] == "<=78"

def test_brier_score_reasonable():
    probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.6, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    score = brier_score_multiclass(probs, "81-82")
    assert isinstance(score, float)
    assert 0 <= score <= 2.0  # Multiclass BS range
    
    # Perfect score
    probs_perfect = {"<=78": 0.0, "79-80": 0.0, "81-82": 1.0, "83-84": 0.0, "85-86": 0.0, ">=87": 0.0}
    assert brier_score_multiclass(probs_perfect, "81-82") == 0.0

def test_log_loss_finite_and_clipping():
    # zero-probability actual bin does not crash because of epsilon clipping
    probs_zero = {"<=78": 0.0, "79-80": 0.0, "81-82": 0.0, "83-84": 0.0, "85-86": 0.0, ">=87": 1.0}
    loss = log_loss_multiclass(probs_zero, "81-82")
    assert isinstance(loss, float)
    assert math.isfinite(loss)
    assert loss > 0
    
    # Perfect loss
    probs_perfect = {"<=78": 0.0, "79-80": 0.0, "81-82": 1.0, "83-84": 0.0, "85-86": 0.0, ">=87": 0.0}
    assert math.isclose(log_loss_multiclass(probs_perfect, "81-82"), 0.0, abs_tol=1e-10)

def test_invalid_probabilities_errors():
    # missing required bins
    probs_missing = {"<=78": 1.0}
    with pytest.raises(ValueError, match="Missing required bin"):
        validate_probabilities(probs_missing)
    
    # invalid probability range
    probs_range = {"<=78": 1.1, "79-80": -0.1, "81-82": 0.0, "83-84": 0.0, "85-86": 0.0, ">=87": 0.0}
    with pytest.raises(ValueError, match="Invalid probability"):
        validate_probabilities(probs_range)
    
    # sum not approximately 1
    probs_sum = {"<=78": 0.5, "79-80": 0.1, "81-82": 0.1, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    with pytest.raises(ValueError, match="sum to approximately 1.0"):
        validate_probabilities(probs_sum)

def test_may_3_2026_specific_case():
    # Requested in prompt: final high 82 maps to 81-82
    high = 82
    probs = {
        "<=78": 0.01,
        "79-80": 0.04,
        "81-82": 0.45,
        "83-84": 0.40,
        "85-86": 0.09,
        ">=87": 0.01
    }
    result = score_prediction(probs, high)
    assert result["actual_bin"] == "81-82"
    assert result["top_predicted_bin"] == "81-82"
    assert result["top_bin_hit"] is True
    assert result["brier_score"] < 1.0
    assert result["log_loss"] < 1.0

if __name__ == "__main__":
    test_temp_to_bin_logic()
    test_top_bin_logic()
    test_score_prediction_hits()
    test_brier_score_reasonable()
    test_log_loss_finite_and_clipping()
    test_may_3_2026_specific_case()
    print("All manual calibration tests passed!")

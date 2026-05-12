import math
import pytest
from src.calibration.metrics import (
    top_bin,
    brier_score_multiclass,
    log_loss_multiclass,
    score_prediction,
    validate_probabilities,
    crps_multiclass,
    expected_calibration_error,
    calculate_aggregate_stats,
    reliability_bins,
    calculate_aggregate_stats_by_lead_time,
    score_multi_source,
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

def test_crps_multiclass():
    # Perfect score: CDF matches exactly
    probs_perfect = {"<=78": 0.0, "79-80": 0.0, "81-82": 1.0, "83-84": 0.0, "85-86": 0.0, ">=87": 0.0}
    assert crps_multiclass(probs_perfect, "81-82") == 0.0
    
    # Worst score (predicted highest bin, actual lowest bin)
    probs_worst = {"<=78": 0.0, "79-80": 0.0, "81-82": 0.0, "83-84": 0.0, "85-86": 0.0, ">=87": 1.0}
    assert crps_multiclass(probs_worst, "<=78") == 5.0 # sum over 5 bins, each has diff=1

def test_expected_calibration_error():
    metrics = [
        {"top_predicted_prob": 0.9, "top_bin_hit": True},
        {"top_predicted_prob": 0.9, "top_bin_hit": False},
        {"top_predicted_prob": 0.1, "top_bin_hit": False},
        {"top_predicted_prob": 0.1, "top_bin_hit": False}
    ]
    # Bin 0.9 (idx 9): avg prob 0.9, hit rate 0.5. diff = 0.4. count = 2
    # Bin 0.1 (idx 1): avg prob 0.1, hit rate 0.0. diff = 0.1. count = 2
    # Total ECE: 0.5 * 0.4 + 0.5 * 0.1 = 0.2 + 0.05 = 0.25
    ece = expected_calibration_error(metrics)
    assert math.isclose(ece, 0.25, abs_tol=1e-5)

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

# ---------------------------------------------------------------------------
# P2 — reliability_bins tests
# ---------------------------------------------------------------------------

def test_reliability_bins_empty():
    assert reliability_bins([]) == []


def test_reliability_bins_basic_structure():
    metrics = [
        {"top_predicted_prob": 0.85, "top_bin_hit": True},
        {"top_predicted_prob": 0.82, "top_bin_hit": False},
        {"top_predicted_prob": 0.15, "top_bin_hit": False},
        {"top_predicted_prob": 0.10, "top_bin_hit": False},
    ]
    result = reliability_bins(metrics, num_bins=10)
    # Must be non-empty, sorted by bin_lower
    assert len(result) > 0
    for r in result:
        assert "bin_lower" in r
        assert "bin_upper" in r
        assert "avg_predicted_prob" in r
        assert "actual_hit_rate" in r
        assert "count" in r
        assert 0.0 <= r["actual_hit_rate"] <= 1.0
        assert r["count"] > 0


def test_reliability_bins_perfect_calibration():
    # Predictor always confident and always right — reliability bucket near 1.0 should have hit_rate=1.0
    metrics = [
        {"top_predicted_prob": 0.95, "top_bin_hit": True},
        {"top_predicted_prob": 0.92, "top_bin_hit": True},
    ]
    result = reliability_bins(metrics, num_bins=10)
    assert len(result) == 1
    assert result[0]["actual_hit_rate"] == 1.0


def test_reliability_bins_total_count_matches_input():
    metrics = [{"top_predicted_prob": p, "top_bin_hit": True} for p in [0.1, 0.3, 0.5, 0.7, 0.9]]
    result = reliability_bins(metrics, num_bins=10)
    assert sum(r["count"] for r in result) == len(metrics)


# ---------------------------------------------------------------------------
# P2 — score_prediction lead_time_hours tests
# ---------------------------------------------------------------------------

def test_score_prediction_without_lead_time():
    probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.6, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    result = score_prediction(probs, 82)
    assert "lead_time_hours" not in result


def test_score_prediction_with_lead_time():
    probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.6, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    result = score_prediction(probs, 82, lead_time_hours=18)
    assert result["lead_time_hours"] == 18
    assert result["top_bin_hit"] is True


# ---------------------------------------------------------------------------
# P2 — calculate_aggregate_stats_by_lead_time tests
# ---------------------------------------------------------------------------

def test_aggregate_stats_by_lead_time_basic():
    probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.6, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    metrics = [
        score_prediction(probs, 82, lead_time_hours=6),
        score_prediction(probs, 82, lead_time_hours=6),
        score_prediction(probs, 80, lead_time_hours=20),
    ]
    by_lead = calculate_aggregate_stats_by_lead_time(metrics)
    # 6h → "<12h", 20h → "<24h"
    assert "<12h" in by_lead
    assert "<24h" in by_lead
    assert by_lead["<12h"]["count"] == 2
    assert by_lead["<24h"]["count"] == 1


def test_aggregate_stats_by_lead_time_unknown_bucket():
    probs = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.6, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
    # No lead_time_hours → falls into "unknown" bucket
    metrics = [score_prediction(probs, 82)]
    by_lead = calculate_aggregate_stats_by_lead_time(metrics)
    assert "unknown" in by_lead
    assert by_lead["unknown"]["count"] == 1


# ---------------------------------------------------------------------------
# P2 — score_multi_source tests
# ---------------------------------------------------------------------------

_BASE_PROBS = {"<=78": 0.1, "79-80": 0.1, "81-82": 0.6, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}
_WORSE_PROBS = {"<=78": 0.6, "79-80": 0.1, "81-82": 0.1, "83-84": 0.1, "85-86": 0.1, ">=87": 0.0}


def test_score_multi_source_returns_all_sources():
    results = score_multi_source(
        {"twc_raw": _WORSE_PROBS, "blended": _BASE_PROBS},
        final_max_temp_f=82,
    )
    assert "twc_raw" in results
    assert "blended" in results


def test_score_multi_source_better_source_has_lower_brier():
    results = score_multi_source(
        {"twc_raw": _WORSE_PROBS, "blended": _BASE_PROBS},
        final_max_temp_f=82,
    )
    assert results["blended"]["brier_score"] < results["twc_raw"]["brier_score"]


def test_score_multi_source_with_lead_time():
    results = score_multi_source(
        {"blended": _BASE_PROBS},
        final_max_temp_f=82,
        lead_time_hours=24,
    )
    assert results["blended"]["lead_time_hours"] == 24


def test_score_multi_source_empty_sources():
    results = score_multi_source({}, final_max_temp_f=82)
    assert results == {}


if __name__ == "__main__":
    test_temp_to_bin_logic()
    test_top_bin_logic()
    test_score_prediction_hits()
    test_brier_score_reasonable()
    test_log_loss_finite_and_clipping()
    test_may_3_2026_specific_case()
    test_reliability_bins_empty()
    test_reliability_bins_basic_structure()
    test_reliability_bins_perfect_calibration()
    test_reliability_bins_total_count_matches_input()
    test_score_prediction_without_lead_time()
    test_score_prediction_with_lead_time()
    test_aggregate_stats_by_lead_time_basic()
    test_aggregate_stats_by_lead_time_unknown_bucket()
    test_score_multi_source_returns_all_sources()
    test_score_multi_source_better_source_has_lower_brier()
    test_score_multi_source_with_lead_time()
    test_score_multi_source_empty_sources()
    print("All manual calibration tests passed!")

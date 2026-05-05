import math
from typing import Dict, Any, List
from forecasting.bin_converter import temp_to_bin
from shared.types import REQUIRED_BINS

def top_bin(probability_bins: Dict[str, float]) -> str:
    """Returns the bin with the highest probability."""
    if not probability_bins:
        raise ValueError("Probabilities dictionary is empty")
    return max(probability_bins.items(), key=lambda x: x[1])[0]

def brier_score_multiclass(probability_bins: Dict[str, float], actual_bin: str) -> float:
    """
    Calculates the multi-class Brier score.
    BS = sum((p_i - y_i)^2)
    where y_i is 1 if bin i is the actual bin, 0 otherwise.
    """
    score = 0.0
    for b in REQUIRED_BINS:
        prob = probability_bins.get(b, 0.0)
        actual = 1.0 if b == actual_bin else 0.0
        score += (prob - actual) ** 2
    return score

def log_loss_multiclass(probability_bins: Dict[str, float], actual_bin: str, epsilon: float = 1e-15) -> float:
    """
    Calculates log loss with epsilon clipping to avoid log(0).
    Loss = -log(max(p_actual, epsilon))
    """
    prob = probability_bins.get(actual_bin, 0.0)
    prob = max(prob, epsilon)
    prob = min(prob, 1.0 - epsilon)
    return -math.log(prob)

def validate_probabilities(probability_bins: Dict[str, float]):
    """
    Validates that:
    - all required bins exist
    - probabilities are between 0 and 1
    - probabilities sum approximately to 1
    """
    for b in REQUIRED_BINS:
        if b not in probability_bins:
            raise ValueError(f"Missing required bin: {b}")
    
    total_prob = 0.0
    for b, prob in probability_bins.items():
        if not (0.0 <= prob <= 1.0):
            raise ValueError(f"Invalid probability for bin {b}: {prob}")
        total_prob += prob
    
    if not math.isclose(total_prob, 1.0, abs_tol=0.01):
        raise ValueError(f"Probabilities must sum to approximately 1.0, got {total_prob}")

def score_prediction(probability_bins: Dict[str, float], final_max_temp_f: int) -> Dict[str, Any]:
    """
    Scores a prediction against a final ground truth temperature.
    Returns:
    - final_max_temp_f
    - actual_bin
    - top_predicted_bin
    - top_bin_hit
    - brier_score
    - log_loss
    """
    validate_probabilities(probability_bins)

    actual_bin = temp_to_bin(final_max_temp_f)
    top_predicted = top_bin(probability_bins)
    
    return {
        "final_max_temp_f": final_max_temp_f,
        "actual_bin": actual_bin,
        "top_predicted_bin": top_predicted,
        "top_bin_hit": top_predicted == actual_bin,
        "brier_score": brier_score_multiclass(probability_bins, actual_bin),
        "log_loss": log_loss_multiclass(probability_bins, actual_bin)
    }

def calculate_aggregate_stats(metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate average performance stats over a list of metrics dictionaries."""
    if not metrics_list:
        return {}
        
    count = len(metrics_list)
    total_brier = sum(m["brier_score"] for m in metrics_list)
    total_log_loss = sum(m["log_loss"] for m in metrics_list)
    hits = sum(1 for m in metrics_list if m["top_bin_hit"])
    
    return {
        "count": count,
        "average_brier_score": total_brier / count,
        "average_log_loss": total_log_loss / count,
        "hit_rate": hits / count
    }

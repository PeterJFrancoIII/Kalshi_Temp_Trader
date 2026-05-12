import math
from collections import defaultdict
from typing import Dict, Any, List, Optional
from forecasting.bin_converter import temp_to_bin
from shared.types import REQUIRED_BINS

# Lead-time buckets (hours before market open) used for performance stratification.
# Bucket label = "< upper_h" except the final open-ended bucket.
_LEAD_TIME_BUCKET_UPPER_HOURS = [12, 24, 48, 72, 168]

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

def crps_multiclass(probability_bins: Dict[str, float], actual_bin: str) -> float:
    """
    Calculates Continuous Ranked Probability Score (CRPS).
    CRPS = sum((CDF_p - CDF_y)^2)
    Assumes REQUIRED_BINS are ordered.
    """
    score = 0.0
    cumulative_p = 0.0
    cumulative_y = 0.0
    for b in REQUIRED_BINS:
        cumulative_p += probability_bins.get(b, 0.0)
        cumulative_y += 1.0 if b == actual_bin else 0.0
        score += (cumulative_p - cumulative_y) ** 2
    return score

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

def score_prediction(
    probability_bins: Dict[str, float],
    final_max_temp_f: int,
    lead_time_hours: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Scores a prediction against a final ground truth temperature.

    Args:
        probability_bins: Dict mapping bin label → probability.
        final_max_temp_f: Observed daily maximum temperature (°F).
        lead_time_hours: Optional hours between forecast generation and the
            event date.  When provided it is stored in the result and used by
            calculate_aggregate_stats_by_lead_time() for stratified analysis.

    Returns dict with keys:
        final_max_temp_f, actual_bin, top_predicted_bin, top_predicted_prob,
        top_bin_hit, brier_score, log_loss, crps[, lead_time_hours]
    """
    validate_probabilities(probability_bins)

    actual_bin = temp_to_bin(final_max_temp_f)
    top_predicted = top_bin(probability_bins)

    result: Dict[str, Any] = {
        "final_max_temp_f": final_max_temp_f,
        "actual_bin": actual_bin,
        "top_predicted_bin": top_predicted,
        "top_predicted_prob": probability_bins.get(top_predicted, 0.0),
        "top_bin_hit": top_predicted == actual_bin,
        "brier_score": brier_score_multiclass(probability_bins, actual_bin),
        "log_loss": log_loss_multiclass(probability_bins, actual_bin),
        "crps": crps_multiclass(probability_bins, actual_bin),
    }
    if lead_time_hours is not None:
        result["lead_time_hours"] = lead_time_hours
    return result

def expected_calibration_error(metrics_list: List[Dict[str, Any]], num_bins: int = 10) -> float:
    """
    Calculates Expected Calibration Error (ECE).
    """
    if not metrics_list:
        return 0.0
        
    bins = [[] for _ in range(num_bins)]
    for m in metrics_list:
        # We expect score_prediction to output top_predicted_prob
        prob = m.get("top_predicted_prob", 0.0)
        bin_idx = min(int(prob * num_bins), num_bins - 1)
        bins[bin_idx].append(m)
        
    ece = 0.0
    total_count = len(metrics_list)
    
    for bin_items in bins:
        if not bin_items:
            continue
            
        bin_count = len(bin_items)
        avg_prob = sum(item.get("top_predicted_prob", 0.0) for item in bin_items) / bin_count
        hit_rate = sum(1 for item in bin_items if item.get("top_bin_hit")) / bin_count
        
        ece += (bin_count / total_count) * abs(avg_prob - hit_rate)
        
    return ece

def calculate_aggregate_stats(metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate average performance stats over a list of metrics dictionaries."""
    if not metrics_list:
        return {}
        
    count = len(metrics_list)
    total_brier = sum(m["brier_score"] for m in metrics_list)
    total_log_loss = sum(m["log_loss"] for m in metrics_list)
    total_crps = sum(m.get("crps", 0.0) for m in metrics_list)
    hits = sum(1 for m in metrics_list if m["top_bin_hit"])
    ece = expected_calibration_error(metrics_list)
    
    return {
        "count": count,
        "average_brier_score": total_brier / count,
        "average_log_loss": total_log_loss / count,
        "average_crps": total_crps / count,
        "expected_calibration_error": ece,
        "hit_rate": hits / count
    }


# ---------------------------------------------------------------------------
# P2 — Reliability diagram data
# ---------------------------------------------------------------------------

def reliability_bins(
    metrics_list: List[Dict[str, Any]],
    num_bins: int = 10,
) -> List[Dict[str, Any]]:
    """
    Produces data for a reliability (calibration) diagram.

    Groups score_prediction results by the model's top-bin confidence
    (top_predicted_prob) into equal-width buckets, then computes the actual
    hit rate per bucket.  Returns the data needed to plot a reliability curve:
    a well-calibrated model produces points close to the diagonal.

    Args:
        metrics_list: List of dicts returned by score_prediction().
        num_bins: Number of confidence buckets (default 10 → 0–10%, 10–20%, …)

    Returns:
        List of dicts, one per non-empty bucket, with keys:
            bin_lower          — lower bound of confidence interval (inclusive)
            bin_upper          — upper bound of confidence interval (exclusive)
            avg_predicted_prob — mean model confidence in this bucket
            actual_hit_rate    — fraction of predictions in bucket that were correct
            count              — number of predictions in this bucket
    """
    if not metrics_list:
        return []

    buckets: List[List[Dict[str, Any]]] = [[] for _ in range(num_bins)]
    for m in metrics_list:
        prob = m.get("top_predicted_prob", 0.0)
        idx = min(int(prob * num_bins), num_bins - 1)
        buckets[idx].append(m)

    result = []
    for i, items in enumerate(buckets):
        if not items:
            continue
        count = len(items)
        avg_prob = sum(item.get("top_predicted_prob", 0.0) for item in items) / count
        hit_rate = sum(1 for item in items if item.get("top_bin_hit")) / count
        result.append({
            "bin_lower": round(i / num_bins, 4),
            "bin_upper": round((i + 1) / num_bins, 4),
            "avg_predicted_prob": round(avg_prob, 4),
            "actual_hit_rate": round(hit_rate, 4),
            "count": count,
        })
    return result


# ---------------------------------------------------------------------------
# P2 — Lead-time stratification
# ---------------------------------------------------------------------------

def _lead_time_bucket_label(lead_time_hours: Optional[int]) -> str:
    """Maps a lead time in hours to a human-readable bucket label."""
    if lead_time_hours is None:
        return "unknown"
    for upper in _LEAD_TIME_BUCKET_UPPER_HOURS:
        if lead_time_hours < upper:
            return f"<{upper}h"
    return f">={_LEAD_TIME_BUCKET_UPPER_HOURS[-1]}h"


def calculate_aggregate_stats_by_lead_time(
    metrics_list: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Groups score_prediction results by lead_time_hours bucket and returns
    calculate_aggregate_stats() for each group.

    Bucket labels (hours before market): <12h, <24h, <48h, <72h, <168h, >=168h.
    Predictions without a lead_time_hours field fall into the "unknown" bucket.

    Args:
        metrics_list: List of dicts returned by score_prediction() with
            optional lead_time_hours key.

    Returns:
        Dict mapping bucket_label → aggregate_stats dict.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for m in metrics_list:
        label = _lead_time_bucket_label(m.get("lead_time_hours"))
        grouped[label].append(m)
    return {label: calculate_aggregate_stats(items) for label, items in grouped.items()}


# ---------------------------------------------------------------------------
# P2 — Multi-source comparison
# ---------------------------------------------------------------------------

def score_multi_source(
    sources: Dict[str, Dict[str, float]],
    final_max_temp_f: int,
    lead_time_hours: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Scores multiple named probability distributions against the same ground
    truth, enabling head-to-head calibration comparison between sources such
    as raw TWC, bias-corrected TWC, and the blended distribution.

    Args:
        sources: Mapping of source_name → probability_bins dict.
            e.g. {"twc_raw": {...}, "twc_corrected": {...}, "blended": {...}}
        final_max_temp_f: Observed daily maximum temperature (°F).
        lead_time_hours: Optional lead time applied to all sources.

    Returns:
        Dict mapping source_name → score_prediction result dict.

    Example:
        >>> results = score_multi_source(
        ...     {"raw": raw_bins, "blended": blended_bins},
        ...     final_max_temp_f=84,
        ...     lead_time_hours=18,
        ... )
        >>> results["raw"]["brier_score"]   # twc_raw Brier score
        >>> results["blended"]["crps"]      # blended CRPS
    """
    return {
        name: score_prediction(bins, final_max_temp_f, lead_time_hours=lead_time_hours)
        for name, bins in sources.items()
    }

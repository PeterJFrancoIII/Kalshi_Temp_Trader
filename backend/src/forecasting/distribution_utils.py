"""
Shared integer-temperature distribution utilities for the KMIA forecast pipeline.

All distributions in this module use Dict[int, float] — integer Fahrenheit
temperature keys mapped to probability masses.  Fixed Kalshi bin strings are
NOT used here; callers that need fixed bins should call
integer_dist_to_fixed_bins() at the boundary.
"""

import math
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Standard 6 KMIA Kalshi bins: (label, inclusive_low, inclusive_high)
_FIXED_BIN_RANGES: List[Tuple[str, int, int]] = [
    ("<=78",  -999,  78),
    ("79-80",   79,  80),
    ("81-82",   81,  82),
    ("83-84",   83,  84),
    ("85-86",   85,  86),
    (">=87",    87, 999),
]


# ---------------------------------------------------------------------------
# Standard normal CDF (no scipy dependency)
# ---------------------------------------------------------------------------

def _normal_cdf(z: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ---------------------------------------------------------------------------
# Integer distribution construction
# ---------------------------------------------------------------------------

def build_integer_distribution(
    center_f: int,
    std_f: float = 2.2,
    temp_range: Tuple[int, int] = (60, 105),
) -> Dict[int, float]:
    """
    Builds a discrete normal distribution over integer Fahrenheit temperatures.

    Each integer bucket t captures the mass P(t - 0.5 < X <= t + 0.5) for
    X ~ N(center_f, std_f²).  Probabilities are renormalized to sum to 1.0
    after truncating to temp_range.

    Args:
        center_f:   Distribution center (e.g. NWS forecast high).
        std_f:      Standard deviation in °F.  Default 2.2 (calibrated value).
        temp_range: (min_temp, max_temp) inclusive.

    Returns:
        Dict mapping integer temperature → probability mass (sums to 1.0).
    """
    lo, hi = temp_range
    probs: Dict[int, float] = {}
    for t in range(lo, hi + 1):
        z_low = (t - 0.5 - center_f) / std_f
        z_high = (t + 0.5 - center_f) / std_f
        p = _normal_cdf(z_high) - _normal_cdf(z_low)
        if p > 1e-8:
            probs[t] = p
    total = sum(probs.values())
    if total > 0:
        probs = {t: round(p / total, 6) for t, p in probs.items()}
    return probs


# ---------------------------------------------------------------------------
# Distribution transforms
# ---------------------------------------------------------------------------

def normalize_probability_mass(probs: Dict[int, float]) -> Dict[int, float]:
    """Renormalizes an integer distribution to sum to 1.0."""
    total = sum(probs.values())
    if total <= 0:
        return probs
    return {t: round(p / total, 6) for t, p in probs.items()}


def build_integer_distribution_from_samples(samples: List[int]) -> Dict[int, float]:
    """
    Builds a discrete probability distribution from a list of integer samples.

    Args:
        samples: List of integer Fahrenheit temperatures.

    Returns:
        Dict mapping integer temperature → probability mass.
    """
    if not samples:
        return {}
    counts: Dict[int, int] = {}
    for s in samples:
        counts[s] = counts.get(s, 0) + 1
    total = len(samples)
    return {t: round(c / total, 6) for t, c in counts.items()}


def validate_distribution(probs: Dict[int, float]) -> List[str]:
    """
    Validates that a distribution sums to ~1.0 and has no negative values.
    
    Returns:
        List of warning strings.
    """
    warnings = []
    total = sum(probs.values())
    if not (0.99 <= total <= 1.01):
        warnings.append(f"Probability mass sum is {total}, not near 1.0")
    if any(p < 0 for p in probs.values()):
        warnings.append("Negative probabilities found")
    return warnings


def zero_impossible_temps(
    probs: Dict[int, float],
    observed_min_f: int,
) -> Dict[int, float]:
    """
    Zeros out probabilities for temperatures strictly below observed_min_f.

    This is a hard constraint: the daily max cannot be less than the observed
    maximum so far.  Remaining probability is renormalized.
    """
    zeroed = {t: (0.0 if t < observed_min_f else p) for t, p in probs.items()}
    return normalize_probability_mass(zeroed)


def blend_integer_distributions(
    dist1: Dict[int, float], 
    dist2: Dict[int, float], 
    weight1: float, 
    weight2: float
) -> Dict[int, float]:
    """
    Blends two integer distributions using specified weights.
    
    The result is normalized.
    """
    blended = {}
    
    # Get all unique keys
    all_keys = set(dist1.keys()).union(set(dist2.keys()))
    
    for k in all_keys:
        p1 = dist1.get(k, 0.0)
        p2 = dist2.get(k, 0.0)
        blended[k] = p1 * weight1 + p2 * weight2
        
    return normalize_probability_mass(blended)


def shift_distribution(probs: Dict[int, float], shift_f: int) -> Dict[int, float]:
    """
    Rigidly shifts an integer distribution by shift_f degrees.

    Positive shift_f = warming; negative = cooling.
    """
    return {t + shift_f: p for t, p in probs.items()}


def shift_distribution_fractional(probs: Dict[int, float], shift_f: float) -> Dict[int, float]:
    """
    Rigidly shifts an integer distribution by shift_f degrees (can be fractional).
    
    For a fractional shift, mass is linearly interpolated between adjacent integer buckets.
    Example: 100% mass at 90 shifted by -0.5 results in 50% at 89 and 50% at 90.
    """
    if shift_f == 0:
        return probs
        
    new_probs: Dict[int, float] = {}
    
    # Let s_int = floor(shift_f)
    # Let s_frac = shift_f - s_int
    # new_p(t + s_int) += (1 - s_frac) * old_p(t)
    # new_p(t + s_int + 1) += s_frac * old_p(t)
    
    s_int = math.floor(shift_f)
    s_frac = shift_f - s_int
    
    for t, p in probs.items():
        # Lower bucket
        t_low = t + s_int
        new_probs[t_low] = new_probs.get(t_low, 0.0) + (1.0 - s_frac) * p
        
        # Upper bucket
        t_high = t + s_int + 1
        if s_frac > 0:
            new_probs[t_high] = new_probs.get(t_high, 0.0) + s_frac * p
            
    return normalize_probability_mass(new_probs)


def apply_weather_suppression_integer(
    probs: Dict[int, float],
    thunderstorm_flag: bool = False,
    recent_rain_flag: bool = False,
    overcast_flag: bool = False,
    thunderstorm_severity: str = "none",
) -> Dict[int, float]:
    """
    Applies a cooling shift to the integer distribution based on weather flags or severity.

    Severity levels for thunderstorms:
    - 'slight chance' / 'isolated': -0.5°F shift
    - 'chance' / 'scattered': -1.0°F shift
    - 'likely' / 'definite' / generic 'thunderstorm': -2.0°F shift

    Rain / overcast:
    - -1.0°F shift if flags are set and no thunderstorm severity is provided.
    """
    shift = 0.0
    
    # 1. Map thunderstorm severity to shift
    t_sev = thunderstorm_severity.lower()
    if "slight" in t_sev or "isolated" in t_sev:
        shift = -0.5
    elif "chance" in t_sev or "scattered" in t_sev:
        shift = -1.0
    elif "likely" in t_sev or "definite" in t_sev or "thunderstorm" in t_sev or thunderstorm_flag:
        shift = -2.0
        
    # 2. Fallback to rain/overcast if no thunderstorm suppression
    if shift == 0.0:
        if recent_rain_flag or overcast_flag:
            shift = -1.0
            
    if shift == 0.0:
        return probs
        
    return shift_distribution_fractional(probs, shift)


# ---------------------------------------------------------------------------
# CDF utilities
# ---------------------------------------------------------------------------

def build_cdf(probs: Dict[int, float]) -> Dict[int, float]:
    """Builds a CDF from an integer PMF (sorted by temperature)."""
    cdf: Dict[int, float] = {}
    cum = 0.0
    for t in sorted(probs.keys()):
        cum += probs[t]
        cdf[t] = round(cum, 6)
    return cdf


def compute_percentile(cdf: Dict[int, float], percentile: float) -> Optional[int]:
    """Returns the lowest integer temperature at which CDF >= percentile."""
    for t in sorted(cdf.keys()):
        if cdf[t] >= percentile:
            return t
    return None


# ---------------------------------------------------------------------------
# Fixed-bin conversion (backward compatibility)
# ---------------------------------------------------------------------------

def integer_dist_to_fixed_bins(
    integer_probs: Dict[int, float],
) -> Dict[str, float]:
    """
    Aggregates an integer-temperature distribution into the 6 standard Kalshi bins.

    Returns a dict keyed by bin label (e.g. "<=78", "81-82", ">=87") that
    preserves all probability mass.  The result is NOT renormalized — if the
    input sums to 1.0 the output will too.
    """
    bins: Dict[str, float] = {label: 0.0 for label, _, _ in _FIXED_BIN_RANGES}
    for temp, prob in integer_probs.items():
        for label, lo, hi in _FIXED_BIN_RANGES:
            if lo <= temp <= hi:
                bins[label] += prob
                break
    return {label: round(p, 6) for label, p in bins.items()}


# ---------------------------------------------------------------------------
# Canonical TemperatureDistribution artifact builders & validators
# ---------------------------------------------------------------------------

def build_integer_distribution_from_bins(
    probability_bins: Dict[str, float],
    observed_max_so_far_f: Optional[float] = None,
    station: str = "KMIA",
    target_date: Optional[str] = None,
    forecast_as_of_time: Optional[str] = None,
    source: str = "rules_v2_climatology",
    confidence: Optional[str] = None,
    warnings: Optional[List[str]] = None
) -> dict:
    """
    Converts a legacy fixed-bin probability distribution into a canonical
    integer Fahrenheit temperature probability distribution.

    Legacy bins mapping support:
    - <=78 spreads over [72, 78] (7 buckets)
    - 79-80 maps to [79, 80] (2 buckets)
    - 81-82 maps to [81, 82] (2 buckets)
    - 83-84 maps to [83, 84] (2 buckets)
    - 85-86 maps to [85, 86] (2 buckets)
    - >=87 spreads over [87, 96] (10 buckets)

    Probabilities are split equally among integer Fahrenheit keys within each support,
    truncated below math.ceil(observed_max_so_far_f) if present, and renormalized.
    """
    local_warnings = list(warnings) if warnings is not None else []
    # Provenance disclaimer
    local_warnings.append("This distribution is derived from legacy fixed-bin mappings and is not dynamically calibrated at the integer level.")

    # Standard expected bins
    expected_bins = {"<=78", "79-80", "81-82", "83-84", "85-86", ">=87"}
    input_bins = set(probability_bins.keys())

    # Check for invalid bins
    invalid_bins = input_bins - expected_bins
    if invalid_bins:
        local_warnings.append(f"Invalid bins found in probability_bins: {list(invalid_bins)}")

    # Check for missing standard bins
    missing_bins = expected_bins - input_bins
    if missing_bins:
        local_warnings.append(f"Missing standard bins in probability_bins: {list(missing_bins)}")

    # Define bounded supports for the bins
    bin_supports = {
        "<=78": list(range(72, 79)),  # 72..78
        "79-80": list(range(79, 81)),  # 79..80
        "81-82": list(range(81, 83)),  # 81..82
        "83-84": list(range(83, 85)),  # 83..84
        "85-86": list(range(85, 87)),  # 85..86
        ">=87": list(range(87, 97)),  # 87..96
    }

    # Initialize raw integer probabilities
    raw_dist: Dict[int, float] = {t: 0.0 for t in range(72, 97)}

    # Map legacy bins into integer temperature probabilities
    for bin_name, support in bin_supports.items():
        prob = probability_bins.get(bin_name, 0.0)
        if prob > 0.0:
            share = prob / len(support)
            for t in support:
                raw_dist[t] = raw_dist.get(t, 0.0) + share

    # Truncate strictly below observed_max_so_far_f if provided
    if observed_max_so_far_f is not None:
        cutoff = math.ceil(observed_max_so_far_f)
        for t in list(raw_dist.keys()):
            if t < cutoff:
                raw_dist[t] = 0.0

    # Renormalize remaining probability mass
    total_prob = sum(raw_dist.values())
    integer_distribution: Dict[str, float] = {}
    sum_probability = 0.0

    if total_prob <= 0.0:
        local_warnings.append("Truncation removed all probability mass")
        integer_distribution = {str(t): 0.0 for t in sorted(raw_dist.keys())}
        sum_probability = 0.0
    else:
        integer_distribution = {
            str(t): round(p / total_prob, 6) for t, p in sorted(raw_dist.items())
        }
        sum_probability = round(sum(integer_distribution.values()), 6)

    return {
        "station": station,
        "target_date": target_date,
        "forecast_as_of_time": forecast_as_of_time,
        "metric": "daily_max_temperature_f",
        "source": source,
        "confidence": confidence,
        "integer_distribution": integer_distribution,
        "observed_max_so_far_f": observed_max_so_far_f,
        "warnings": local_warnings,
        "sum_probability": sum_probability,
        "schema_version": "1.0.0"
    }


def validate_temperature_distribution(distribution: dict) -> List[str]:
    """
    Validates a canonical TemperatureDistribution dictionary.

    Returns a list of warning/error strings. If valid, the list will be empty.
    """
    errors: List[str] = []

    if not isinstance(distribution, dict):
        return ["Distribution must be a dictionary"]

    # Check required keys
    required_keys = {
        "station", "target_date", "forecast_as_of_time", "metric",
        "source", "confidence", "integer_distribution",
        "observed_max_so_far_f", "warnings", "sum_probability", "schema_version"
    }
    for rk in required_keys:
        if rk not in distribution:
            errors.append(f"Missing required key: {rk}")

    # If key missing, exit early to prevent KeyErrors
    if errors:
        return errors

    # Check metric
    if distribution["metric"] != "daily_max_temperature_f":
        errors.append(f"Invalid metric: {distribution['metric']}")

    # Check integer_distribution
    int_dist = distribution["integer_distribution"]
    if not isinstance(int_dist, dict):
        errors.append("integer_distribution must be a dictionary")
        return errors

    # Validate keys and values in integer_distribution
    dist_sum = 0.0
    observed_max = distribution["observed_max_so_far_f"]
    cutoff = math.ceil(observed_max) if observed_max is not None else None

    for t_str, prob in int_dist.items():
        if not isinstance(t_str, str):
            errors.append(f"integer_distribution key must be string, got: {type(t_str)}")
            continue

        try:
            t_int = int(t_str)
        except ValueError:
            errors.append(f"integer_distribution key must represent an integer, got: {t_str}")
            continue

        if not isinstance(prob, (int, float)):
            errors.append(f"probability value for temp {t_str} must be numeric, got: {type(prob)}")
            continue

        if prob < 0.0:
            errors.append(f"probability value for temp {t_str} cannot be negative: {prob}")

        dist_sum += prob

        # Check observed max constraint
        if cutoff is not None and t_int < cutoff and prob > 0.0:
            errors.append(f"Non-zero probability {prob} found for temperature {t_str} below observed max cutoff {cutoff}")

    # Check sum probability consistency
    reported_sum = distribution["sum_probability"]
    if abs(dist_sum - reported_sum) > 1e-5:
        errors.append(f"sum_probability {reported_sum} does not match actual sum of integer_distribution {dist_sum}")

    # Check if sum is ~1.0 unless truncation warning is present
    has_truncation_empty_warning = any("Truncation removed all probability mass" in w for w in distribution.get("warnings", []))
    if not has_truncation_empty_warning:
        if not (0.99 <= dist_sum <= 1.01):
            errors.append(f"Total probability mass {dist_sum} is not close to 1.0")
    else:
        if dist_sum > 0.0:
            errors.append(f"Truncation warning present but total probability is non-zero: {dist_sum}")

    return errors


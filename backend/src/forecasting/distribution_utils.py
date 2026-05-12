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
    std_f: float = 3.0,
    temp_range: Tuple[int, int] = (60, 115),
) -> Dict[int, float]:
    """
    Builds a discrete normal distribution over integer Fahrenheit temperatures.

    Each integer bucket t captures the mass P(t - 0.5 < X <= t + 0.5) for
    X ~ N(center_f, std_f²).  Probabilities are renormalized to sum to 1.0
    after truncating to temp_range.

    Args:
        center_f:   Distribution center (e.g. NWS forecast high).
        std_f:      Standard deviation in °F.  Default 3.0 (scaffold value).
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


def apply_weather_suppression_integer(
    probs: Dict[int, float],
    thunderstorm_flag: bool,
    recent_rain_flag: bool,
    overcast_flag: bool,
) -> Dict[int, float]:
    """
    Applies a cooling shift to the integer distribution based on weather flags.

    Uses the same heuristic magnitudes as the legacy fixed-bin suppressor:
    - Thunderstorm → -2°F shift
    - Rain / overcast → -1°F shift

    Consistent with apply_regime_adjustment() in kmia_distribution_blender.
    """
    if thunderstorm_flag:
        return shift_distribution(probs, -2)
    if recent_rain_flag or overcast_flag:
        return shift_distribution(probs, -1)
    return probs


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

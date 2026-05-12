import copy
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
try:
    from dateutil import tz
except ImportError:
    import datetime.timezone as tz

logger = logging.getLogger(__name__)

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def normalize_probability_mass(probs: Dict[int, float]) -> Dict[int, float]:
    """Normalizes probability mass to sum to 1.0."""
    total = sum(probs.values())
    if total <= 0:
        return probs
    return {temp: round(prob / total, 4) for temp, prob in probs.items()}

def build_cdf(probs: Dict[int, float]) -> Dict[int, float]:
    """Builds a cumulative distribution function from a probability mass function."""
    cdf = {}
    sorted_temps = sorted(probs.keys())
    cum_prob = 0.0
    for temp in sorted_temps:
        cum_prob += probs[temp]
        cdf[temp] = round(cum_prob, 4)
    return cdf

def compute_percentile(cdf: Dict[int, float], percentile: float) -> Optional[int]:
    """Computes the temperature at which the CDF reaches or exceeds the percentile."""
    for temp in sorted(cdf.keys()):
        if cdf[temp] >= percentile:
            return temp
    return None

def shift_distribution(probs: Dict[int, float], shift_amount: int) -> Dict[int, float]:
    """Shifts the entire distribution by a discrete integer amount."""
    shifted = {}
    for temp, prob in probs.items():
        shifted[temp + shift_amount] = prob
    return shifted

def correct_distribution(
    distribution: Dict[str, Any],
    nws_snapshot: Dict[str, Any],
    current_time_et: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Applies NWS observation-based bias corrections to a daily max temperature distribution.
    """
    output = copy.deepcopy(distribution)
    
    if "correction_reasons" not in output:
        output["correction_reasons"] = []
    
    if current_time_et is None:
        try:
            current_time_et = datetime.now(tz.gettz('America/New_York'))
        except Exception:
            # Fallback if tz not properly available
            current_time_et = datetime.now()
            
    hour = current_time_et.hour
    
    probs = output.get("integer_probs", {})
    if not probs:
        return output
        
    # Convert keys to int (just in case)
    probs = {int(k): float(v) for k, v in probs.items()}
    
    stale_data = nws_snapshot.get("stale_data", True)
    
    # 1. Rule 1: Observed Max Truncation
    obs_max = nws_snapshot.get("observed_max_so_far_f")
    if obs_max is not None:
        obs_max_int = int(round(obs_max))
        truncated = False
        for temp in list(probs.keys()):
            if temp < obs_max_int:
                probs[temp] = 0.0
                truncated = True
        if truncated:
            probs = normalize_probability_mass(probs)
            output["correction_reasons"].append(f"Truncated lower-tail probabilities below observed max of {obs_max}F.")

    # 2. Rule 2: Stale Data Check
    if stale_data:
        output["correction_reasons"].append("Stale data flagged; skipped speculative regime shifts.")
        output["warnings"].append("Stale NWS observations. Confidence downgraded.")
        # We stop applying heuristic shifts, but we already applied the observed max truncation (a hard truth)
    else:
        # We can apply heuristic regime shifts
        wind_dir = nws_snapshot.get("wind_direction_compass")
        wind_speed = nws_snapshot.get("wind_speed_mph")
        current_temp = nws_snapshot.get("current_temp_f")
        
        # Rule 3: Early Sea Breeze (Cooling Shift)
        # Moderate east winds before late afternoon
        if wind_dir in ["E", "ENE", "ESE", "SE"] and wind_speed is not None and wind_speed > 8.0:
            probs = shift_distribution(probs, -1)
            output["correction_reasons"].append(f"Applied early sea-breeze cooling shift (-1F) due to {wind_dir} winds at {wind_speed} mph.")
            
        # Rule 4: Offshore / Westerly Flow (Warming Shift)
        elif wind_dir in ["W", "WNW", "WSW", "SW"]:
            probs = shift_distribution(probs, 1)
            output["correction_reasons"].append(f"Applied offshore/westerly warming shift (+1F) due to {wind_dir} winds.")
            
        # Rule 5: Faster-Than-Expected Heating (Warm Ramp)
        # E.g. >= 85F before 11:00 AM ET.
        if current_temp is not None and hour < 11 and current_temp >= 85.0:
            probs = shift_distribution(probs, 1)
            output["correction_reasons"].append(f"Applied warm ramp shift (+1F) due to high morning temperature ({current_temp}F at {hour}h ET).")

    # Finalize distribution
    output["integer_probs"] = probs
    output["cdf"] = build_cdf(probs)
    output["probability_mass_sum"] = sum(probs.values())
    
    # Compute percentiles
    output["p10"] = compute_percentile(output["cdf"], 0.10)
    output["p50"] = compute_percentile(output["cdf"], 0.50)
    output["p90"] = compute_percentile(output["cdf"], 0.90)

    # Note the corrector version
    output["calibration_version"] = output.get("calibration_version", "") + "+bias_corrected_v1"

    return output

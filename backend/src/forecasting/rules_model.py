import math
from datetime import date, datetime
from typing import Optional, Dict, List, Any

from shared.types import REQUIRED_BINS

def validate_probability_bins(bins: Dict[str, float]):
    """
    Validates that all required bins are present and probabilities are valid (0-1).
    Raises ValueError if invalid.
    """
    for b in REQUIRED_BINS:
        if b not in bins:
            raise ValueError(f"Missing required bin: {b}")
    
    total = 0.0
    for b, prob in bins.items():
        if not (0.0 <= prob <= 1.0):
            raise ValueError(f"Probability for bin {b} must be between 0 and 1, got {prob}")
        total += prob
            
    # We check for total sum roughly 1.0 during normalization/output, 
    # but here we just check for basic validity.
    if total < 0:
        raise ValueError("Total probability cannot be negative")

def zero_impossible_bins(bins: Dict[str, float], observed_max_so_far_f: Optional[int]) -> Dict[str, float]:
    """
    Strict rule: If the upper bound of a bin is less than the observed max so far, 
    that bin must receive 0.0 probability.
    """
    if not observed_max_so_far_f:
        return bins
    
    # Bin upper bounds for comparison
    boundaries = {
        "<=78": 78,
        "79-80": 80,
        "81-82": 82,
        "83-84": 84,
        "85-86": 86,
        ">=87": 999  # Effectively infinity
    }
    
    new_bins = bins.copy()
    for b, upper in boundaries.items():
        if upper < observed_max_so_far_f:
            new_bins[b] = 0.0
            
    return new_bins

def normalize_bins(bins: Dict[str, float]) -> Dict[str, float]:
    """
    Ensures that probabilities sum to 1.0.
    If the total is 0 (all bins zeroed), falls back to 1.0 in the highest bin.
    """
    total = sum(bins.values())
    if total <= 0:
        # Fallback: All probability to the highest bin
        fallback = {b: 0.0 for b in REQUIRED_BINS}
        fallback[">=87"] = 1.0
        return fallback
        
    return {b: round(prob / total, 4) for b, prob in bins.items()}

def forecast_daily_high_bins(
    observed_max_so_far_f: Optional[int] = None,
    current_temp_f: Optional[int] = None,
    forecast_high_f: Optional[int] = None,
    normal_high_f: Optional[int] = None,
    recent_rain_flag: bool = False,
    thunderstorm_flag: bool = False,
    overcast_flag: bool = False,
    current_time_et: Optional[datetime] = None,
    live_data_stale: bool = False
) -> Dict[str, Any]:
    """
    Rules-based forecast logic that returns a DailyPrediction-like dictionary.
    """
    warnings = []
    main_drivers = []
    
    # 1. Validation / Warnings for missing or stale data
    if live_data_stale:
        warnings.append("live data is stale")
    if forecast_high_f is None:
        warnings.append("forecast_high_f is missing")
    if observed_max_so_far_f is None:
        warnings.append("observed_max_so_far_f is missing")
    if current_temp_f is None:
        warnings.append("current_temp_f is missing")

    # Determine base baseline
    if forecast_high_f is not None:
        best_base = forecast_high_f
        main_drivers.append(f"NWS Forecast High: {forecast_high_f}°F")
    else:
        # Fallback to normal high if available, else 82
        best_base = normal_high_f if normal_high_f is not None else 82
        if normal_high_f is not None:
            main_drivers.append(f"Using normal high ({normal_high_f}°F) due to missing forecast.")
        else:
            main_drivers.append("Using Miami baseline (82°F) due to missing forecast.")

    # Current observed max so far (handle missing as 0 or current temp)
    obs_max = observed_max_so_far_f if observed_max_so_far_f is not None else (current_temp_f if current_temp_f is not None else 0)

    # 2. Determine best single number (mean forecast)
    best_single_number_f = best_base
    
    # Heuristic suppression
    if thunderstorm_flag:
        best_single_number_f -= 2
        main_drivers.append("Suppressed expected high due to thunderstorms.")
    elif recent_rain_flag or overcast_flag:
        best_single_number_f -= 1
        main_drivers.append("Suppressed expected high due to rain or overcast conditions.")
            
    # Hard floor: cannot be below what we've already seen
    best_single_number_f = max(best_single_number_f, obs_max)

    # 3. Build initial distribution (heuristic-based)
    from .bin_converter import temp_to_bin
    target_bin = temp_to_bin(best_single_number_f)
    
    initial_bins = {b: 0.01 for b in REQUIRED_BINS} # Small prior for all
    initial_bins[target_bin] = 0.70
    
    # Distribute remaining weight to adjacent bins
    try:
        idx = REQUIRED_BINS.index(target_bin)
        if idx > 0:
            initial_bins[REQUIRED_BINS[idx-1]] += 0.14
        if idx < len(REQUIRED_BINS) - 1:
            initial_bins[REQUIRED_BINS[idx+1]] += 0.14
    except ValueError:
        pass

    # 4. Apply Hard Constraints
    constrained_bins = zero_impossible_bins(initial_bins, obs_max)
    
    # 5. Normalize
    final_bins = normalize_bins(constrained_bins)
    
    # 6. Confidence heuristic
    confidence = "medium"
    if obs_max >= 85:
        confidence = "high"
    elif current_time_et and current_time_et.hour >= 16: # After 4 PM
        confidence = "high"
    elif forecast_high_f is None:
        confidence = "low"

    if obs_max > best_base:
        warnings.append(f"Observed max ({obs_max}°F) already exceeds base forecast ({best_base}°F).")

    return {
        "station": "KMIA",
        "date": datetime.now().date().isoformat(),
        "metric": "daily_max_temperature_f",
        "best_single_number_f": best_single_number_f,
        "probability_bins": final_bins,
        "observed_max_so_far_f": obs_max,
        "current_temp_f": current_temp_f,
        "forecast_high_f": forecast_high_f,
        "confidence": confidence,
        "main_drivers": main_drivers,
        "warnings": warnings
    }

class RulesBasedForecaster:
    """
    Wrapper for Rules-Based Forecasting Engine.
    """
    def generate_daily_prediction(self, **kwargs) -> Any:
        result = forecast_daily_high_bins(**kwargs)
        try:
            from shared.types import DailyPrediction
            from datetime import date
            if isinstance(result["date"], str):
                result["date"] = date.fromisoformat(result["date"])
            return DailyPrediction(**result)
        except ImportError:
            return result

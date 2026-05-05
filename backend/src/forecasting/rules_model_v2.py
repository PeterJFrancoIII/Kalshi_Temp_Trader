import math
from datetime import datetime
from typing import Optional, Dict, List, Any
from forecasting.bin_converter import temp_to_bin
from forecasting.rules_model import zero_impossible_bins, normalize_bins, validate_probability_bins
from forecasting.climatology_model import climatology_prior_for_date

from shared.types import REQUIRED_BINS

def forecast_target_distribution(forecast_high_f: int) -> Dict[str, float]:
    """
    Builds a distribution around the forecast high.
    - target bin gets 0.55
    - adjacent lower bin gets 0.20
    - adjacent upper bin gets 0.20
    - remaining bins share 0.05
    """
    target_bin = temp_to_bin(forecast_high_f)
    dist = {b: 0.0 for b in REQUIRED_BINS}
    
    try:
        idx = REQUIRED_BINS.index(target_bin)
        dist[target_bin] = 0.55
        
        # Determine adjacent bins
        adjacents = []
        if idx > 0:
            adjacents.append(REQUIRED_BINS[idx-1])
        if idx < len(REQUIRED_BINS) - 1:
            adjacents.append(REQUIRED_BINS[idx+1])
            
        # Distribute 0.40 to adjacents
        if len(adjacents) == 2:
            dist[adjacents[0]] = 0.20
            dist[adjacents[1]] = 0.20
        elif len(adjacents) == 1:
            # If only one adjacent, give it the full 0.40
            dist[adjacents[0]] = 0.40
        else:
            # No adjacents (shouldn't happen with 6 bins unless something is wrong)
            dist[target_bin] = 0.95
            
        # Distribute 0.05 to remaining
        rem_count = len([b for b in REQUIRED_BINS if b != target_bin and b not in adjacents])
        if rem_count > 0:
            rem_prob = 0.05 / rem_count
            for b in REQUIRED_BINS:
                if b != target_bin and b not in adjacents:
                    dist[b] = rem_prob
    except (ValueError, IndexError):
        # Fallback if something goes wrong
        dist = {b: round(1.0 / len(REQUIRED_BINS), 4) for b in REQUIRED_BINS}
        
    return normalize_bins(dist)

def apply_weather_suppression(
    bins: Dict[str, float], 
    recent_rain_flag: bool, 
    thunderstorm_flag: bool, 
    overcast_flag: bool
) -> Dict[str, float]:
    """
    Adjusts probabilities based on weather suppression flags.
    """
    new_bins = bins.copy()
    
    # Define mass to move
    mass_to_move = 0.0
    if thunderstorm_flag:
        mass_to_move = 0.15 # Stronger discount
    elif recent_rain_flag or overcast_flag:
        mass_to_move = 0.05 # Modest discount
        
    if mass_to_move == 0:
        return new_bins
        
    # Source bins (upper bins)
    source_bins = [">=87", "85-86", "83-84"]
    # Target bins (lower plausible bins)
    target_bins = ["81-82", "79-80", "<=78"]
    
    # Take mass from sources
    total_taken = 0.0
    for sb in source_bins:
        if sb in new_bins:
            reduction = new_bins[sb] * mass_to_move
            new_bins[sb] -= reduction
            total_taken += reduction
            
    # Add mass to targets (equally among non-zero targets if possible)
    if total_taken > 0:
        # For simplicity in rules model v2, we just distribute back to all targets
        # we'll rely on zero_impossible_bins to clean it up later if they are impossible
        add_per_bin = total_taken / len(target_bins)
        for tb in target_bins:
            new_bins[tb] += add_per_bin
            
    return new_bins

def forecast_daily_high_bins_v2(
    input_features: Dict[str, Any], 
    history_records: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Combined Forecast Model v2.
    """
    target_date = input_features.get("target_date")
    if not target_date:
        target_date = datetime.now().date().isoformat()
        
    observed_max_so_far_f = input_features.get("observed_max_so_far_f", 0)
    forecast_high_f = input_features.get("forecast_high_f")
    
    warnings = []
    main_drivers = []
    
    # 1. Climatology Prior
    prior_res = climatology_prior_for_date(history_records or [], target_date)
    climatology_dist = prior_res["probability_bins"]
    if prior_res["warnings"]:
        warnings.extend(prior_res["warnings"])
    else:
        main_drivers.append("Integrated 30-year seasonal climatology prior.")
        
    # 2. Forecast Target Distribution
    if forecast_high_f is not None:
        forecast_dist = forecast_target_distribution(forecast_high_f)
        main_drivers.append(f"Centered forecast around NWS high of {forecast_high_f}F.")
    else:
        warnings.append("forecast_high_f is missing. Using climatology as primary lead.")
        forecast_dist = climatology_dist.copy()

    # 3. Blend (45% Climatology, 45% Forecast, 10% rules-based adjustment space)
    blended_bins = {}
    for b in REQUIRED_BINS:
        # Base blend
        blended_bins[b] = (climatology_dist[b] * 0.45) + (forecast_dist[b] * 0.45)
        # Small uniform prior for the remaining 10%
        blended_bins[b] += (0.10 / len(REQUIRED_BINS))

    # 4. Apply weather suppression
    recent_rain_flag = input_features.get("recent_rain_flag", False)
    thunderstorm_flag = input_features.get("thunderstorm_flag", False)
    overcast_flag = input_features.get("overcast_flag", False)
    
    blended_bins = apply_weather_suppression(
        blended_bins, 
        recent_rain_flag, 
        thunderstorm_flag, 
        overcast_flag
    )
    if thunderstorm_flag:
        main_drivers.append("Adjusted for expected thunderstorms.")
    elif recent_rain_flag or overcast_flag:
        main_drivers.append("Adjusted for cloud cover/precipitation.")

    # 5. Apply Hard live constraint
    final_bins = zero_impossible_bins(blended_bins, observed_max_so_far_f)
    
    # 6. Normalize
    final_bins = normalize_bins(final_bins)
    
    # 7. Validation
    validate_probability_bins(final_bins)
    
    # Best single number (heuristic: peak of distribution or forecast high)
    peak_bin = max(final_bins, key=final_bins.get)
    # This is a bit crude but works for v2
    best_single_number_f = forecast_high_f if forecast_high_f else 82
    if observed_max_so_far_f > best_single_number_f:
        best_single_number_f = observed_max_so_far_f

    # Confidence heuristic
    confidence = "medium"
    if input_features.get("stale_data_flag"):
        confidence = "low"
    elif observed_max_so_far_f >= 85:
        confidence = "high"

    return {
        "station": "KMIA",
        "date": target_date,
        "metric": "daily_max_temperature_f",
        "model_version": "rules_v2_climatology",
        "best_single_number_f": best_single_number_f,
        "probability_bins": final_bins,
        "observed_max_so_far_f": observed_max_so_far_f,
        "current_temp_f": input_features.get("current_temp_f"),
        "forecast_high_f": forecast_high_f,
        "confidence": confidence,
        "main_drivers": main_drivers,
        "warnings": warnings
    }

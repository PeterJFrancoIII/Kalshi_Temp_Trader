import math
from datetime import datetime
from typing import Optional, Dict, List, Any
from forecasting.bin_converter import temp_to_bin
from forecasting.rules_model import zero_impossible_bins, normalize_bins, validate_probability_bins
from forecasting.climatology_model import climatology_prior_for_date, climatology_prior_integer_for_date
from forecasting.distribution_utils import (
    build_integer_distribution,
    apply_weather_suppression_integer,
    zero_impossible_temps,
    normalize_probability_mass,
    build_cdf,
    compute_percentile,
    integer_dist_to_fixed_bins,
    blend_integer_distributions,
)
from forecasting.calibration_config import (
    V2_CLIMATOLOGY_WEIGHT,
    V2_FORECAST_WEIGHT,
    V2_UNIFORM_WEIGHT
)

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
    
    # --- 1. Probability Distribution Source of Truth ---
    # We calculate the high-resolution integer distribution first, blending
    # climatology and forecast leads, then apply weather suppression and 
    # hard constraints. Legacy bins are derived from this final distribution.
    
    integer_dist: Dict[int, float] = {}
    int_cdf: Dict[int, float] = {}
    
    # Climatology lead
    clim_int_dist = climatology_prior_integer_for_date(history_records or [], target_date)
    if clim_int_dist:
        main_drivers.append("Integrated 30-year seasonal climatology prior.")
    
    # Forecast lead
    if forecast_high_f is not None:
        main_drivers.append(f"Centered forecast around NWS high of {forecast_high_f}F.")
        center = forecast_high_f
        if observed_max_so_far_f is not None:
            center = max(int(forecast_high_f), int(observed_max_so_far_f))
        
        forecast_int_dist = build_integer_distribution(center_f=center)
        
        # Blend (using centralized weights)
        if clim_int_dist:
            # Mixture model of climatology and NWS forecast
            integer_dist = blend_integer_distributions(
                clim_int_dist, forecast_int_dist, V2_CLIMATOLOGY_WEIGHT, V2_FORECAST_WEIGHT
            )
            # Add uniform floor
            uniform_prob = V2_UNIFORM_WEIGHT / 56 # Approx range 60-115
            for t in range(60, 116):
                integer_dist[t] = integer_dist.get(t, 0.0) + uniform_prob
            integer_dist = normalize_probability_mass(integer_dist)
        else:
            integer_dist = forecast_int_dist
            warnings.append("Climatology lead unavailable; using forecast distribution only.")
    else:
        warnings.append("forecast_high_f is missing. Using climatology as primary lead.")
        integer_dist = clim_int_dist

    # --- 2. Apply weather suppression and constraints ---
    recent_rain_flag = input_features.get("recent_rain_flag", False)
    thunderstorm_flag = input_features.get("thunderstorm_flag", False)
    overcast_flag = input_features.get("overcast_flag", False)
    thunderstorm_severity = input_features.get("thunderstorm_severity", "none")

    if integer_dist:
        integer_dist = apply_weather_suppression_integer(
            integer_dist,
            thunderstorm_flag=thunderstorm_flag,
            recent_rain_flag=recent_rain_flag,
            overcast_flag=overcast_flag,
            thunderstorm_severity=thunderstorm_severity,
        )

        if thunderstorm_severity != "none":
            main_drivers.append(f"Adjusted for {thunderstorm_severity} thunderstorms.")
        elif thunderstorm_flag:
            main_drivers.append("Adjusted for expected thunderstorms.")
        elif recent_rain_flag or overcast_flag:
            main_drivers.append("Adjusted for cloud cover/precipitation.")

        # Apply Hard live constraint (observed max)
        if observed_max_so_far_f is not None and observed_max_so_far_f > 0:
            integer_dist = zero_impossible_temps(integer_dist, observed_max_so_far_f)
        else:
            integer_dist = normalize_probability_mass(integer_dist)
            if observed_max_so_far_f is None:
                warnings.append("No same-day NWS observations available; skipping lower-tail truncation.")

        # --- 3. Derive legacy bins and metadata ---
        final_bins = integer_dist_to_fixed_bins(integer_dist)
        int_cdf = build_cdf(integer_dist)
        validate_probability_bins(final_bins)
    else:
        # Fallback: Equal distribution
        final_bins = {b: 1.0/len(REQUIRED_BINS) for b in REQUIRED_BINS}
        warnings.append("Failed to generate valid distribution; using uniform fallback.")

    # Best single number (heuristic: expected value of distribution)
    expected_value = sum(t * p for t, p in integer_dist.items()) if integer_dist else (forecast_high_f if forecast_high_f else 82)
    best_single_number_f = int(round(expected_value))
    
    if observed_max_so_far_f is not None and observed_max_so_far_f > best_single_number_f:
        best_single_number_f = observed_max_so_far_f

    # Mode calculation
    dist_mode = max(integer_dist, key=integer_dist.get) if integer_dist else best_single_number_f

    # Weather suppression shift for metadata (replicating mapping logic)
    suppression_shift = 0.0
    if integer_dist:
        t_sev = thunderstorm_severity.lower()
        if "slight" in t_sev or "isolated" in t_sev:
            suppression_shift = -0.5
        elif "chance" in t_sev or "scattered" in t_sev:
            suppression_shift = -1.0
        elif "likely" in t_sev or "definite" in t_sev or "thunderstorm" in t_sev or thunderstorm_flag:
            suppression_shift = -2.0
        elif recent_rain_flag or overcast_flag:
            suppression_shift = -1.0

    # Confidence heuristic
    confidence = "medium"
    if input_features.get("stale_data_flag"):
        confidence = "low"
    elif observed_max_so_far_f is not None and observed_max_so_far_f >= 85:
        confidence = "high"

    return {
        "station": "KMIA",
        "date": target_date,
        "metric": "daily_max_temperature_f",
        "model_version": "rules_v2_climatology",
        "best_single_number_f": best_single_number_f,
        "deterministic_anchor_f": forecast_high_f,
        "final_distribution_mean_f": round(expected_value, 2) if integer_dist else None,
        "final_distribution_mode_f": dist_mode,
        "forecast_weight": V2_FORECAST_WEIGHT,
        "climatology_weight": V2_CLIMATOLOGY_WEIGHT,
        "weather_suppression_shift_f": suppression_shift,
        "probability_bins": final_bins,
        "integer_distribution": integer_dist,
        "integer_distribution_cdf": int_cdf,
        "observed_max_so_far_f": observed_max_so_far_f,
        "current_temp_f": input_features.get("current_temp_f"),
        "forecast_high_f": forecast_high_f,
        "confidence": confidence,
        "main_drivers": main_drivers,
        "warnings": warnings
    }

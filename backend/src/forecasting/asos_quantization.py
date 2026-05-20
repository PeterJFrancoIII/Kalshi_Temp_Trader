"""Utility functions for ASOS quantization and RH tie-breaker logic.

Detects Celsius-derived temperature reporting patterns and performs
latent temperature inference using relative humidity and dew point physics.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dateutil import tz

def is_celsius_quantized_fahrenheit(temp_f: float) -> bool:
    """Checks if a Fahrenheit temperature is consistent with a whole Celsius degree.
    
    ASOS/Synoptic stations often report in whole degrees Celsius, which are
    then converted to Fahrenheit. This creates repeating quantized values:
    - 29C -> 84.2F
    - 30C -> 86.0F
    - 31C -> 87.8F
    - 32C -> 89.6F
    - 33C -> 91.4F
    """
    if temp_f is None:
        return False
    temp_c = (temp_f - 32.0) / 1.8
    # Check if the difference from the nearest whole Celsius degree is very small
    return abs(temp_c - round(temp_c)) < 0.01

def rh_from_temp_dewpoint(temp_f: float, dewpoint_f: float) -> Optional[float]:
    """Calculates relative humidity percentage from temperature and dew point."""
    if temp_f is None or dewpoint_f is None:
        return None
    # Convert to Celsius
    t_c = (temp_f - 32.0) / 1.8
    td_c = (dewpoint_f - 32.0) / 1.8
    
    a = 17.67
    b = 243.5
    
    try:
        ps_t = 6.112 * math.exp((a * t_c) / (t_c + b))
        ps_td = 6.112 * math.exp((a * td_c) / (td_c + b))
        rh = 100.0 * (ps_td / ps_t)
        return min(100.0, max(0.0, rh))
    except (ZeroDivisionError, ValueError):
        return None

def temperature_from_dewpoint_rh(dewpoint_f: float, rh_pct: float) -> Optional[float]:
    """Computes the thermodynamic implied temperature from dew point and RH."""
    if dewpoint_f is None or rh_pct is None or rh_pct <= 0:
        return None
    # Convert dewpoint to Celsius
    td_c = (dewpoint_f - 32.0) / 1.8
    
    a = 17.67
    b = 243.5
    
    try:
        # Saturation vapor pressure term for dewpoint
        gamma_td = (a * td_c) / (td_c + b)
        # Solve for T saturation vapor pressure term using RH
        gamma_t = gamma_td - math.log(rh_pct / 100.0)
        # Solve for T in Celsius
        t_c = (b * gamma_t) / (a - gamma_t)
        # Convert to Fahrenheit
        t_f = t_c * 1.8 + 32.0
        return t_f
    except (ZeroDivisionError, ValueError):
        return None

def is_wind_direction_stable(current_wd: float, history_wds: List[float], max_diff: float = 40.0) -> bool:
    """Checks if the wind direction has remained stable (circular difference)."""
    if current_wd is None:
        return False
    for wd in history_wds:
        if wd is None:
            continue
        diff = abs(current_wd - wd) % 360
        diff = min(diff, 360 - diff)
        if diff > max_diff:
            return False
    return True

def is_pressure_stable(current_p: float, history_ps: List[float], max_diff: float = 1.0) -> bool:
    """Checks if the atmospheric pressure has remained stable."""
    if current_p is None:
        return False
    for p in history_ps:
        if p is None:
            continue
        if abs(current_p - p) > max_diff:
            return False
    return True

def parse_ts(ts_val: Any) -> Optional[datetime]:
    """Parses a timestamp value into a datetime object."""
    if isinstance(ts_val, datetime):
        return ts_val
    if isinstance(ts_val, str):
        try:
            if ts_val.endswith("Z"):
                ts_val = ts_val[:-1] + "+00:00"
            return datetime.fromisoformat(ts_val)
        except ValueError:
            return None
    return None

def safe_float(val: Any) -> Optional[float]:
    """Safely converts a value to float, returning None if conversion fails."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def compass_to_degrees(compass: Any) -> Optional[float]:
    """Converts a compass direction string to degrees."""
    if not isinstance(compass, str):
        return None
    mapping = {
        "N": 0.0, "NNE": 22.5, "NE": 45.0, "ENE": 67.5,
        "E": 90.0, "ESE": 112.5, "SE": 135.0, "SSE": 157.5,
        "S": 180.0, "SSW": 202.5, "SW": 225.0, "WSW": 247.5,
        "W": 270.0, "WNW": 292.5, "NW": 315.0, "NNW": 337.5
    }
    cleaned = compass.strip().upper()
    return mapping.get(cleaned)

def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Maps custom key names from various API and DB schemas to a normalized schema."""
    temp = row.get("air_temp_f")
    if temp is None:
        temp = row.get("temperature_f")
        
    rh = row.get("relative_humidity_pct")
    if rh is None:
        rh = row.get("relative_humidity")
    if rh is None:
        rh = row.get("rh")
        
    dp = row.get("dew_point_f")
    if dp is None:
        dp = row.get("dewpoint_f")
        
    wd = row.get("wind_direction_deg")
    if wd is None:
        wd = row.get("wind_direction")
        
    ws = row.get("wind_speed_mph")
    if ws is None:
        ws = row.get("wind_speed")
        
    press = row.get("pressure")
    if press is None:
        press = row.get("barometric_pressure_mb")
    if press is None:
        press = row.get("sea_level_pressure_mb")
        
    ts = row.get("time_utc")
    if ts is None:
        ts = row.get("timestamp")
        
    qc = row.get("qc_flags", [])
    
    # Try parsing wind direction
    wind_dir_deg = safe_float(wd)
    if wind_dir_deg is None and wd is not None:
        wind_dir_deg = compass_to_degrees(wd)
    
    return {
        "timestamp": parse_ts(ts),
        "temp_f": safe_float(temp),
        "rh_pct": safe_float(rh),
        "dewpoint_f": safe_float(dp),
        "wind_dir": wind_dir_deg,
        "wind_speed": safe_float(ws),
        "pressure": safe_float(press),
        "qc_flags": qc
    }


def infer_latent_temperature_from_rh(
    rows: List[Dict[str, Any]], 
    station_tz: str = "America/New_York",
    rh_drop_threshold: float = 2.0,
    wind_dir_stability_threshold: float = 40.0,
    pressure_stability_threshold: float = 1.0,
    min_flat_observations: int = 3,
    max_lookback_minutes: int = 15
) -> Dict[str, Any]:
    """Analyzes recent observations to detect Celsius quantization and latent warming.
    
    Under stable wind and pressure (no airmass advection) and during daytime
    heating hours, if the reported temperature is flat at a quantized value
    but the relative humidity is falling materially, we infer that the underlying
    true temperature is rising within the Celsius bucket.
    """
    default_result = {
        "reported_observed_max_f": None,
        "latent_observed_max_floor_f": None,
        "latent_observed_max_inferred_f": None,
        "latent_boundary_touch_probability": 0.0,
        "rh_tiebreaker_signal": "NO_SIGNAL",
        "confidence": "none",
        "quantization_warning": False,
        "explanation": "No signal detected.",
        "evidence": [],
        "source_rows_used": 0
    }

    # 1. Normalize and filter rows
    norm_rows = []
    for r in rows:
        norm = normalize_row(r)
        if norm["timestamp"] is not None and norm["temp_f"] is not None:
            # Reconstruct RH if missing but temp and dewpoint exist
            if norm["rh_pct"] is None and norm["dewpoint_f"] is not None:
                norm["rh_pct"] = rh_from_temp_dewpoint(norm["temp_f"], norm["dewpoint_f"])
            
            if norm["rh_pct"] is not None:
                norm_rows.append(norm)
                
    if not norm_rows:
        default_result["explanation"] = "No valid observations found with temperature and humidity."
        return default_result

    # Sort chronological (oldest first)
    norm_rows.sort(key=lambda x: x["timestamp"])
    
    current_row = norm_rows[-1]
    current_temp = current_row["temp_f"]
    current_rh = current_row["rh_pct"]
    current_time = current_row["timestamp"]
    
    default_result["reported_observed_max_f"] = current_temp
    default_result["latent_observed_max_floor_f"] = current_temp
    default_result["latent_observed_max_inferred_f"] = current_temp

    # 2. Check Celsius quantization
    is_quantized = is_celsius_quantized_fahrenheit(current_temp)
    default_result["quantization_warning"] = is_quantized

    # 3. Extract lookback window
    cutoff_time = current_time - timedelta(minutes=max_lookback_minutes)
    lookback_rows = [r for r in norm_rows if r["timestamp"] >= cutoff_time]
    default_result["source_rows_used"] = len(lookback_rows)
    
    if len(lookback_rows) < min_flat_observations:
        default_result["explanation"] = f"Insufficient observations in the last {max_lookback_minutes}m (found {len(lookback_rows)}, need {min_flat_observations})."
        return default_result

    # 4. Check temperature flatness
    # The temperature must remain exactly flat at the quantized level
    is_temp_flat = all(r["temp_f"] == current_temp for r in lookback_rows)
    if not is_temp_flat:
        default_result["explanation"] = "Reported temperature is not flat during the lookback window."
        return default_result

    # 5. Check stability criteria (wind, pressure, QC)
    wind_dirs = [r["wind_dir"] for r in lookback_rows if r["wind_dir"] is not None]
    is_wind_stable = is_wind_direction_stable(current_row["wind_dir"], wind_dirs, wind_dir_stability_threshold) if current_row["wind_dir"] is not None else True
    
    pressures = [r["pressure"] for r in lookback_rows if r["pressure"] is not None]
    is_press_stable = is_pressure_stable(current_row["pressure"], pressures, pressure_stability_threshold) if current_row["pressure"] is not None else True
    
    # Check for QC issues (empty dict/list is fine, any values mean flag is set)
    has_qc_issue = any(r["qc_flags"] for r in lookback_rows if r["qc_flags"])

    if not is_wind_stable or not is_press_stable:
        default_result["rh_tiebreaker_signal"] = "AMBIGUOUS"
        default_result["explanation"] = "Meteorological stability criteria not met (wind or pressure shift detected)."
        return default_result

    # 6. Check time-of-day heating window (KMIA local time)
    local_tz = tz.gettz(station_tz)
    local_dt = current_time.astimezone(local_tz)
    # Require daytime hours where solar heating is active
    if not (8 <= local_dt.hour < 20):
        default_result["explanation"] = f"Observation time {local_dt.strftime('%H:%M')} is outside active heating window."
        return default_result
        
    is_peak_heating = 10 <= local_dt.hour < 17

    # 7. Check relative humidity drop
    # Find the maximum RH in the lookback
    max_rh_row = max(lookback_rows, key=lambda x: x["rh_pct"])
    max_rh = max_rh_row["rh_pct"]
    rh_drop = max_rh - current_rh

    if rh_drop < rh_drop_threshold:
        default_result["explanation"] = f"RH drop of {rh_drop:.1f}% is below threshold of {rh_drop_threshold}%."
        return default_result

    # 8. Check dew point physics to classify signal
    # If dewpoint is available, check if dewpoint is stable
    dp_current = current_row["dewpoint_f"]
    dp_baseline = max_rh_row["dewpoint_f"]
    
    signal = "LIKELY_UPPER_BUCKET_WARMING"
    confidence = "medium"
    
    if dp_current is not None and dp_baseline is not None:
        dp_change = dp_current - dp_baseline
        # If dewpoint drops significantly, the RH drop is driven by drying of the air, not warming
        if dp_change < -1.5:
            signal = "DEWPOINT_DROP"
            confidence = "none"
        # If dewpoint is stable, we have a high-confidence warming signal
        elif abs(dp_change) <= 1.0:
            signal = "LIKELY_UPPER_BUCKET_WARMING"
            confidence = "high" if is_peak_heating else "medium"
        else:
            signal = "AMBIGUOUS"
            confidence = "low"
    else:
        # Without dewpoint, use RH drop as a probabilistic indicator
        signal = "LIKELY_UPPER_BUCKET_WARMING"
        confidence = "medium" if is_peak_heating else "low"

    if has_qc_issue:
        # Downgrade confidence if there are any quality control issues
        confidence = "low" if confidence in ["high", "medium"] else confidence

    if signal != "LIKELY_UPPER_BUCKET_WARMING" or confidence == "none":
        default_result["rh_tiebreaker_signal"] = signal
        default_result["confidence"] = confidence
        default_result["explanation"] = f"Tie-breaker signal was classified as {signal} (dewpoint change: {dp_current - dp_baseline if dp_current is not None else 'N/A'}F)."
        return default_result

    # 9. Compute latent temperature
    implied_temp = None
    if dp_current is not None:
        implied_temp = temperature_from_dewpoint_rh(dp_current, current_rh)
        
    if implied_temp is not None:
        # Cap implied temp within the Celsius bucket range: [temp, temp + 0.9F]
        inferred_temp = max(current_temp, min(implied_temp, current_temp + 0.9))
    else:
        # Default fallback to bucket midpoint
        inferred_temp = current_temp + 0.5

    floor_temp = math.ceil(current_temp)
    # Boundary touch probability based on confidence
    prob_map = {
        "high": 0.65,
        "medium": 0.35,
        "low": 0.15
    }
    touch_prob = prob_map.get(confidence, 0.0)

    # If the current reported temp is not quantized but we still met criteria (unusual)
    if not is_quantized:
        touch_prob = 0.0  # Reset touch prob for non-quantized values
        
    implied_str = f"{implied_temp:.2f}F" if implied_temp is not None else "N/A"
    explanation = (
        f"Detected Celsius-quantized temp flat at {current_temp}F with an RH drop of {rh_drop:.1f}% "
        f"({max_rh:.1f}% -> {current_rh:.1f}%) during stable weather. "
        f"Inferred true temperature is {inferred_temp:.2f}F (implied by dewpoint physics: {implied_str})."
    )

    # Construct structured evidence list
    evidence = []
    if is_quantized:
        evidence.append(f"reported temperature flat at {current_temp}F (Celsius-quantized)")
    else:
        evidence.append(f"reported temperature flat at {current_temp}F")
    evidence.append(f"relative humidity dropped from {max_rh:.2f}% to {current_rh:.2f}%")
    if current_row["wind_dir"] is not None:
        evidence.append("wind direction remained stable")
    if current_row["pressure"] is not None:
        evidence.append("pressure stable")

    return {
        "reported_observed_max_f": current_temp,
        "latent_observed_max_floor_f": floor_temp,
        "latent_observed_max_inferred_f": round(inferred_temp, 2),
        "latent_boundary_touch_probability": touch_prob,
        "rh_tiebreaker_signal": signal,
        "confidence": confidence,
        "quantization_warning": is_quantized,
        "explanation": explanation,
        "evidence": evidence,
        "source_rows_used": len(lookback_rows)
    }

def apply_latent_observation_adjustment(
    distribution: Dict[int, float], 
    latent_inference: Dict[str, Any]
) -> Dict[int, float]:
    """Applies local probability mass adjustment near Kalshi thresholds.
    
    If the RH tie-breaker signal indicates likely upper bucket warming, we shift
    some probability mass from the target boundary temperature to the next degree.
    """
    if not latent_inference or latent_inference.get("rh_tiebreaker_signal") != "LIKELY_UPPER_BUCKET_WARMING":
        return distribution

    confidence = latent_inference.get("confidence", "none")
    touch_prob = latent_inference.get("latent_boundary_touch_probability", 0.0)
    
    # Determine shift fraction based on confidence
    alpha = 0.0
    if confidence == "high":
        alpha = 0.25
    elif confidence == "medium":
        alpha = 0.15
    elif confidence == "low":
        alpha = 0.05
        
    if alpha <= 0.0 or not distribution:
        return distribution

    current_temp = latent_inference.get("reported_observed_max_f")
    if current_temp is None:
        return distribution

    # Target boundary integer is the next integer degree
    target_boundary = int(math.floor(current_temp)) + 1
    
    adjusted = distribution.copy()
    
    # 1. Shift from target_boundary to target_boundary + 1
    if target_boundary in adjusted:
        shift_mass = adjusted[target_boundary] * alpha
        adjusted[target_boundary] = adjusted[target_boundary] - shift_mass
        next_temp = target_boundary + 1
        adjusted[next_temp] = adjusted.get(next_temp, 0.0) + shift_mass

    # 2. Shift from target_boundary - 1 to target_boundary (if it exists and has mass)
    prev_temp = target_boundary - 1
    if prev_temp in adjusted and adjusted[prev_temp] > 0.0:
        shift_mass_prev = adjusted[prev_temp] * alpha
        adjusted[prev_temp] = adjusted[prev_temp] - shift_mass_prev
        adjusted[target_boundary] = adjusted.get(target_boundary, 0.0) + shift_mass_prev

    # Renormalize to ensure sum is exactly 1.0 (imported from distribution_utils later, or local helper)
    total = sum(adjusted.values())
    if total > 0:
        adjusted = {t: p / total for t, p in adjusted.items()}
        
    return adjusted

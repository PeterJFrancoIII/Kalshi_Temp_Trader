import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from shared.artifact_paths import WEATHER_TWC_DIR, FORECAST_DISTRIBUTIONS_DIR

# Anchored to project root — never CWD-relative.
DEFAULT_SNAPSHOT_PATH = str(WEATHER_TWC_DIR / "latest_twc_probabilistic_kmia_snapshot.json")
DEFAULT_OUTPUT_DIR = str(FORECAST_DISTRIBUTIONS_DIR)

def load_latest_twc_snapshot(path: str = DEFAULT_SNAPSHOT_PATH) -> Dict[str, Any]:
    """Loads the latest TWC probabilistic snapshot."""
    if not os.path.exists(path):
        return {
            "status": "unavailable",
            "warnings": [f"Snapshot file not found: {path}"]
        }
    
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        return {
            "status": "unavailable",
            "warnings": [f"Error reading snapshot: {str(e)}"]
        }

from forecasting.distribution_utils import (
    normalize_probability_mass,
    build_cdf,
    compute_percentile,
    validate_distribution,
)

def convert_hourly_to_daily_max(snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts hourly temperature PDFs/probabilities into an approximate daily max distribution.
    Uses conservative assumptions (independence).
    """
    station = snapshot_data.get("station", "KMIA")
    # For target_date, try to parse from fetched_at_utc or use today
    fetched_at = snapshot_data.get("fetched_at_utc")
    target_date = "YYYY-MM-DD"
    if fetched_at:
        try:
            target_date = fetched_at.split("T")[0]
        except:
            pass
    
    output = {
        "station": station,
        "target_date": target_date,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_primary": "TWC_PROBABILISTIC",
        "source_snapshot_path": DEFAULT_SNAPSHOT_PATH,
        "integer_probs": {},
        "cdf": {},
        "p10": None,
        "p50": None,
        "p90": None,
        "probability_mass_sum": 0.0,
        "calibration_version": "twc_daily_max_scaffold_v1",
        "warnings": []
    }

    if snapshot_data.get("status") == "unavailable" or snapshot_data.get("api_status") == "missing_credentials":
        output["warnings"].append("TWC source data unavailable or missing credentials")
        return output

    hourly_data = snapshot_data.get("parsed_pdf_or_probability_fields")
    if not hourly_data:
        output["warnings"].append("Missing probability/PDF fields")
        return output

    # Simple daily-max approximation assuming independence
    # P(Max <= y) = prod_t P(T_t <= y)
    
    hourly_cdfs = []
    all_temps = set()
    
    for hour_entry in hourly_data:
        probs = hour_entry.get("probabilities", {})
        if not probs:
            continue
        # Convert keys to int
        probs_int = {int(k): float(v) for k, v in probs.items()}
        norm_probs = normalize_probability_mass(probs_int)
        cdf = build_cdf(norm_probs)
        hourly_cdfs.append(cdf)
        all_temps.update(probs_int.keys())
        
    if not hourly_cdfs:
        output["warnings"].append("No valid hourly probabilities found")
        return output
        
    sorted_temps = sorted(list(all_temps))
    
    # For each temp, compute product of CDFs
    max_cdf = {}
    for temp in sorted_temps:
        prod_cdf = 1.0
        for cdf in hourly_cdfs:
            p = 0.0
            for t in sorted(cdf.keys()):
                if t <= temp:
                    p = cdf[t]
                else:
                    break
            prod_cdf *= p
        max_cdf[temp] = prod_cdf
        
    # Convert CDF to PMF
    max_probs = {}
    prev_cdf = 0.0
    for temp in sorted_temps:
        curr_cdf = max_cdf[temp]
        prob = curr_cdf - prev_cdf
        if prob > 0:
            max_probs[temp] = round(prob, 4)
        prev_cdf = curr_cdf
        
    # Normalize
    max_probs = normalize_probability_mass(max_probs)
    
    output["integer_probs"] = max_probs
    output["cdf"] = build_cdf(max_probs)
    output["probability_mass_sum"] = sum(max_probs.values())
    
    # Compute percentiles
    output["p10"] = compute_percentile(output["cdf"], 0.10)
    output["p50"] = compute_percentile(output["cdf"], 0.50)
    output["p90"] = compute_percentile(output["cdf"], 0.90)
    
    output["warnings"].extend(validate_distribution(max_probs))
    output["warnings"].append("Scaffold approximation: assumed independent hourly distributions. Requires calibration.")
    
    return output

def write_distribution_snapshot(distribution: Dict[str, Any], output_dir: str = DEFAULT_OUTPUT_DIR):
    """Writes the distribution to a snapshot file."""
    os.makedirs(output_dir, exist_ok=True)
    
    target_date = distribution.get("target_date", "YYYY-MM-DD")
    timestamp = int(datetime.now().timestamp())
    
    # Latest
    latest_path = os.path.join(output_dir, "latest_kmia_daily_max_distribution.json")
    with open(latest_path, "w") as f:
        json.dump(distribution, f, indent=2)
        
    # Timestamped
    ts_path = os.path.join(output_dir, f"kmia_daily_max_distribution_{target_date}_{timestamp}.json")
    with open(ts_path, "w") as f:
        json.dump(distribution, f, indent=2)

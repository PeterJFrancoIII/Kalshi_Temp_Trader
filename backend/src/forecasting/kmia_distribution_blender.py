import os
import json
import logging
import copy
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from shared.artifact_paths import FORECAST_DISTRIBUTIONS_DIR

from forecasting.distribution_utils import (
    normalize_probability_mass,
    build_cdf,
    compute_percentile,
    blend_integer_distributions,
)
from forecasting.calibration_config import (
    BLENDER_TWC_WEIGHT,
    BLENDER_NBM_WEIGHT
)

logger = logging.getLogger(__name__)

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def load_json_if_exists(file_path: str) -> Optional[Dict[str, Any]]:
    """Loads JSON data from a file if it exists."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load JSON from {file_path}: {e}")
            return None
    return None

def validate_distribution(probs: Dict[int, float]) -> bool:
    """Validates that a distribution is non-empty and has non-negative probabilities."""
    if not probs:
        return False
    if any(p < 0 for p in probs.values()):
        return False
    return True


def apply_regime_adjustment(
    probs: Dict[int, float], 
    adjustment_type: str, 
    magnitude: int = 1
) -> Dict[int, float]:
    """Applies a deterministic shift to the distribution for regime adjustments."""
    adjusted = {}
    shift = magnitude if adjustment_type == "warming" else -magnitude
    
    for temp, prob in probs.items():
        adjusted[temp + shift] = prob
        
    return adjusted

def blend_distributions(
    twc_dist: Optional[Dict[str, Any]] = None,
    corrected_twc_dist: Optional[Dict[str, Any]] = None,
    nbm_dist: Optional[Dict[str, Any]] = None,
    hrrr_features: Optional[Dict[str, Any]] = None,
    wfo_warnings: Optional[List[str]] = None,
    target_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Blends multiple forecast distributions into a canonical KMIA daily max distribution.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    
    output = {
        "station": "KMIA",
        "target_date": target_date,
        "generated_at_utc": generated_at,
        "source_primary": "UNAVAILABLE",
        "source_components": [],
        "component_weights": {},
        "integer_probs": {},
        "cdf": {},
        "p10": None,
        "p50": None,
        "p90": None,
        "probability_mass_sum": 0.0,
        "calibration_version": "kmia_distribution_blender_scaffold_v1",
        "blend_reasons": [],
        "warnings": [],
        "status": "UNAVAILABLE"
    }
    
    # 1. Determine Primary Prior
    primary_dist = None
    primary_name = ""
    
    if corrected_twc_dist and validate_distribution(corrected_twc_dist.get("integer_probs", {})):
        primary_dist = corrected_twc_dist["integer_probs"]
        primary_name = "CORRECTED_TWC"
        output["blend_reasons"].append("Using corrected TWC distribution as primary prior.")
        if target_date is None:
            target_date = corrected_twc_dist.get("target_date")
    elif twc_dist and validate_distribution(twc_dist.get("integer_probs", {})):
        primary_dist = twc_dist["integer_probs"]
        primary_name = "RAW_TWC"
        output["blend_reasons"].append("Using raw TWC distribution as primary prior.")
        if target_date is None:
            target_date = twc_dist.get("target_date")
        
    if not primary_dist:
        output["warnings"].append("No valid primary distribution (TWC) available.")
        return output
        
    # Convert keys to int
    primary_dist = {int(k): float(v) for k, v in primary_dist.items()}
    
    output["target_date"] = target_date
    output["source_primary"] = primary_name
    output["source_components"].append(primary_name)
    output["component_weights"][primary_name] = 1.0
    output["integer_probs"] = primary_dist
    output["status"] = "OK"
    
    # 2. Blend with NBM if available
    if nbm_dist and validate_distribution(nbm_dist.get("integer_probs", {})):
        nbm_probs = {int(k): float(v) for k, v in nbm_dist["integer_probs"].items()}
        
        # Using centralized weights
        twc_weight = BLENDER_TWC_WEIGHT
        nbm_weight = BLENDER_NBM_WEIGHT
        
        output["integer_probs"] = blend_integer_distributions(
            output["integer_probs"], nbm_probs, twc_weight, nbm_weight
        )
        
        output["source_components"].append("NBM")
        output["component_weights"][primary_name] = twc_weight
        output["component_weights"]["NBM"] = nbm_weight
        output["blend_reasons"].append(f"Blended NBM with weight {nbm_weight} (empirical scaffold).")
        
    # 3. HRRR Regime Adjustments
    if hrrr_features:
        regime = hrrr_features.get("regime")
        if regime == "sea_breeze":
            output["integer_probs"] = apply_regime_adjustment(output["integer_probs"], "cooling", 1)
            output["blend_reasons"].append("Applied HRRR sea-breeze cooling shift (-1F).")
            output["warnings"].append("HRRR regime adjustment is a scaffold heuristic.")
        elif regime == "offshore":
            output["integer_probs"] = apply_regime_adjustment(output["integer_probs"], "warming", 1)
            output["blend_reasons"].append("Applied HRRR offshore warming shift (+1F).")
            output["warnings"].append("HRRR regime adjustment is a scaffold heuristic.")

    # 4. WFO Warnings/Confidence
    if wfo_warnings:
        output["warnings"].extend(wfo_warnings)
        output["blend_reasons"].append(f"Added {len(wfo_warnings)} WFO warnings/notes.")

    # Finalize
    output["integer_probs"] = {int(k): float(v) for k, v in output["integer_probs"].items()}
    output["cdf"] = build_cdf(output["integer_probs"])
    output["probability_mass_sum"] = sum(output["integer_probs"].values())
    output["p10"] = compute_percentile(output["cdf"], 0.10)
    output["p50"] = compute_percentile(output["cdf"], 0.50)
    output["p90"] = compute_percentile(output["cdf"], 0.90)
    
    return output

def write_blended_distribution_snapshot(dist: Dict[str, Any], output_dir: str = None):
    """Writes the blended distribution to disk."""
    if output_dir is None:
        output_dir = str(FORECAST_DISTRIBUTIONS_DIR)
    os.makedirs(output_dir, exist_ok=True)
    
    target_date = dist.get("target_date") or "unknown_date"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    # Latest file
    latest_path = os.path.join(output_dir, "latest_kmia_blended_distribution.json")
    with open(latest_path, 'w') as f:
        json.dump(dist, f, indent=2)
        
    # Timestamped file
    hist_path = os.path.join(output_dir, f"kmia_blended_distribution_{target_date}_{timestamp}.json")
    with open(hist_path, 'w') as f:
        json.dump(dist, f, indent=2)
        
    return latest_path, hist_path

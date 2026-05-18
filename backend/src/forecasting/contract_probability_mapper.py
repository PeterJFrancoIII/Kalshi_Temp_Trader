from typing import Dict, List, Any, Optional, Union
import math
from market_data.kalshi_contract_mapper import extract_contract_thresholds
from forecasting.distribution_utils import validate_temperature_distribution, validate_distribution

def map_contract_probability(
    temperature_distribution: Union[dict, Any],
    contract_mapping: dict,
) -> dict:
    """
    Integrates a temperature distribution over the parsed contract range.

    Args:
        temperature_distribution: Dict (canonical or raw) representing the temperature distribution.
        contract_mapping: Dict containing parsed contract fields (output of extract_contract_thresholds).

    Returns:
        Dict with fields:
            - market_ticker: str or None
            - contract_range_label: str or None
            - condition_type: str
            - threshold_f: float or None
            - range_high_f: float or None
            - model_probability: float or None
            - tradable: bool
            - warnings: list[str]
            - distribution_source: str
            - schema_version: str
    """
    # 1. Initialize output dictionary
    ticker = contract_mapping.get("ticker")
    contract_range = contract_mapping.get("contract_range")
    cond_type = contract_mapping.get("condition_type", "unknown")
    thresh = contract_mapping.get("threshold_f")
    high = contract_mapping.get("range_high_f")

    res = {
        "market_ticker": ticker,
        "contract_range_label": contract_range,
        "condition_type": cond_type,
        "threshold_f": thresh,
        "range_high_f": high,
        "model_probability": None,
        "tradable": False,
        "warnings": [],
        "distribution_source": "unknown",
        "schema_version": "1.0.0"
    }

    # Gather contract mapping warnings
    parse_warnings = contract_mapping.get("parse_warnings", [])
    res["warnings"].extend(parse_warnings)

    # 2. Check if contract mapping itself is invalid or uncertain
    if contract_mapping.get("uncertain") or cond_type == "unknown":
        res["warnings"].append("Contract mapping is uncertain or has unknown condition type")
        return res

    # 3. Parse temperature distribution
    raw_dist = {}
    source = "unknown"
    schema_ver = "1.0.0"
    dist_warnings = []

    if not isinstance(temperature_distribution, dict):
        res["warnings"].append("Temperature distribution is not a dictionary")
        return res

    if "integer_distribution" in temperature_distribution:
        # Canonical TemperatureDistribution format
        canonical_dist = temperature_distribution
        source = canonical_dist.get("source", "canonical_distribution")
        schema_ver = canonical_dist.get("schema_version", "1.0.0")
        dist_warnings.extend(canonical_dist.get("warnings", []))

        # Validate canonical distribution
        validation_errors = validate_temperature_distribution(canonical_dist)
        if validation_errors:
            res["warnings"].extend(validation_errors)
            res["warnings"].append("Canonical temperature distribution validation failed")
            res["distribution_source"] = source
            res["schema_version"] = schema_ver
            return res

        int_dist = canonical_dist.get("integer_distribution", {})
        for k, v in int_dist.items():
            try:
                raw_dist[int(k)] = float(v)
            except (ValueError, TypeError):
                pass
    else:
        # Raw {int: float} or {str: float} dict format
        source = "raw_dict"
        schema_ver = "1.0.0"
        for k, v in temperature_distribution.items():
            try:
                raw_dist[int(k)] = float(v)
            except (ValueError, TypeError):
                pass

        # Validate raw distribution
        validation_errors = validate_distribution(raw_dist)
        if validation_errors:
            res["warnings"].extend(validation_errors)
            res["warnings"].append("Raw distribution validation failed")
            res["distribution_source"] = source
            res["schema_version"] = schema_ver
            return res

    res["distribution_source"] = source
    res["schema_version"] = schema_ver
    res["warnings"].extend(dist_warnings)

    # 4. Integrate probability mass
    # Set lower/upper bounds for temperature integration
    low_limit = -999.0
    high_limit = 999.0
    lower_inc = contract_mapping.get("lower_inclusive", True)
    upper_inc = contract_mapping.get("upper_inclusive", True)

    if cond_type == "above":
        if thresh is None:
            res["warnings"].append("Missing threshold_f for above condition")
            return res
        if lower_inc:
            # temp >= threshold_f. E.g. temp >= 86.5 -> ceil(86.5) = 87
            low_limit = float(math.ceil(thresh))
        else:
            # temp > threshold_f. E.g. temp > 86.5 -> floor(86.5) + 1 = 87
            low_limit = float(math.floor(thresh) + 1)
        high_limit = 999.0

    elif cond_type == "below":
        if thresh is None:
            res["warnings"].append("Missing threshold_f for below condition")
            return res
        low_limit = -999.0
        if upper_inc:
            # temp <= threshold_f. E.g. temp <= 84.5 -> floor(84.5) = 84
            high_limit = float(math.floor(thresh))
        else:
            # temp < threshold_f. E.g. temp < 84.5 -> ceil(84.5) - 1 = 84
            high_limit = float(math.ceil(thresh) - 1)

    elif cond_type == "between":
        if thresh is None or high is None:
            res["warnings"].append("Missing threshold_f or range_high_f for between condition")
            return res
        if lower_inc:
            low_limit = float(math.ceil(thresh))
        else:
            low_limit = float(math.floor(thresh) + 1)

        if upper_inc:
            high_limit = float(math.floor(high))
        else:
            high_limit = float(math.ceil(high) - 1)

    else:
        res["warnings"].append(f"Unsupported condition type: {cond_type}")
        return res

    # Integrate the probability mass
    prob_sum = 0.0
    for temp, p in raw_dist.items():
        if low_limit <= float(temp) <= high_limit:
            prob_sum += p

    res["model_probability"] = round(prob_sum, 6)
    res["tradable"] = True
    return res

def map_market_probabilities(
    temperature_distribution: Union[dict, Any],
    markets: List[dict],
) -> List[dict]:
    """
    Convenience helper to extract contract thresholds from raw Kalshi markets
    and map model probabilities for all of them.

    Args:
        temperature_distribution: Dict (canonical or raw) representing the temperature distribution.
        markets: List of raw Kalshi market dictionaries.

    Returns:
        List of per-contract probability mapper results.
    """
    results = []
    for market in markets:
        contract_mapping = extract_contract_thresholds(market)
        res = map_contract_probability(temperature_distribution, contract_mapping)
        results.append(res)
    return results

def map_distribution_to_contracts(
    distribution: Dict[int, float],
    contract_ranges: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Backward-compatible wrapper that calls map_contract_probability.
    """
    results = {}
    for mapping in contract_ranges:
        ticker = mapping.get("ticker")
        if not ticker:
            continue
        # Call the new logic
        res = map_contract_probability(distribution, mapping)
        # Wrap the result under the expected keys for backward compatibility
        results[ticker] = {
            "probability": res.get("model_probability"),
            "condition_type": res.get("condition_type"),
            "threshold_f": res.get("threshold_f"),
            "range_high_f": res.get("range_high_f"),
            "lower_inclusive": mapping.get("lower_inclusive"),
            "upper_inclusive": mapping.get("upper_inclusive")
        }
    return results

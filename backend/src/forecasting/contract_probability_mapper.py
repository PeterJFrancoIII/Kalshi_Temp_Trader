from typing import Dict, List, Any
import math

def map_distribution_to_contracts(distribution: Dict[int, float], contract_ranges: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Integrates the blended probability distribution over active contract ranges.
    
    Args:
        distribution: Dict mapping integer high temperatures to probabilities.
        contract_ranges: List of parsed contract range dicts (output of extract_contract_thresholds).
        
    Returns:
        Dict mapping ticker to dict with fields:
            - probability: integrated probability
            - condition_type
            - threshold_f
            - range_high_f
            - lower_inclusive
            - upper_inclusive
    """
    results = {}
    
    for contract in contract_ranges:
        ticker = contract.get("ticker")
        if not ticker:
            continue
            
        cond = contract.get("condition_type")
        thresh = contract.get("threshold_f")
        high = contract.get("range_high_f")
        lower_inc = contract.get("lower_inclusive")
        upper_inc = contract.get("upper_inclusive")
        
        prob = 0.0
        
        if cond == "above" and thresh is not None:
            for temp, p in distribution.items():
                if lower_inc:
                    if temp >= thresh:
                        prob += p
                else:
                    if temp > thresh:
                        prob += p
                        
        elif cond == "below" and thresh is not None:
            for temp, p in distribution.items():
                if upper_inc:
                    if temp <= thresh:
                        prob += p
                else:
                    if temp < thresh:
                        prob += p
                        
        elif cond == "between" and thresh is not None and high is not None:
            for temp, p in distribution.items():
                if lower_inc and upper_inc:
                    if thresh <= temp <= high:
                        prob += p
                elif lower_inc and not upper_inc:
                    if thresh <= temp < high:
                        prob += p
                elif not lower_inc and upper_inc:
                    if thresh < temp <= high:
                        prob += p
                else:
                    if thresh < temp < high:
                        prob += p
                        
        results[ticker] = {
            "probability": prob,
            "condition_type": cond,
            "threshold_f": thresh,
            "range_high_f": high,
            "lower_inclusive": lower_inc,
            "upper_inclusive": upper_inc
        }
        
    return results

from typing import Dict, Any

REQUIRED_BINS = ["<=78", "79-80", "81-82", "83-84", "85-86", ">=87"]

def validate_llm_review_output(output: Dict[str, Any], observed_max_so_far_f: int) -> bool:
    """
    Validates the structured output from an LLM reviewer.
    Returns True if valid, raises ValueError if invalid.
    """
    # 1. Check required bins exist
    if "probability_bins" not in output:
        raise ValueError("Missing 'probability_bins' in output")
        
    bins = output["probability_bins"]
    for b in REQUIRED_BINS:
        if b not in bins:
            raise ValueError(f"Missing required bin: {b}")
            
    # 2. Probabilities are numbers between 0 and 1
    total_prob = 0.0
    for b in REQUIRED_BINS:
        prob = bins[b]
        if not isinstance(prob, (int, float)):
            raise ValueError(f"Probability for bin {b} is not a number: {prob}")
        if not (0.0 <= prob <= 1.0):
            raise ValueError(f"Probability for bin {b} out of range [0, 1]: {prob}")
        total_prob += prob
        
    # 3. Probabilities sum approximately 1
    if abs(total_prob - 1.0) > 0.01:
        raise ValueError(f"Probabilities sum to {total_prob}, expected ~1.0")
        
    # 4. Impossible lower bins are 0
    if observed_max_so_far_f > 78 and bins.get("<=78", 0) > 1e-6:
        raise ValueError(f"Bin <=78 must be 0 because observed max is {observed_max_so_far_f}")
    if observed_max_so_far_f > 80 and bins.get("79-80", 0) > 1e-6:
        raise ValueError(f"Bin 79-80 must be 0 because observed max is {observed_max_so_far_f}")
    if observed_max_so_far_f > 82 and bins.get("81-82", 0) > 1e-6:
        raise ValueError(f"Bin 81-82 must be 0 because observed max is {observed_max_so_far_f}")
    if observed_max_so_far_f > 84 and bins.get("83-84", 0) > 1e-6:
        raise ValueError(f"Bin 83-84 must be 0 because observed max is {observed_max_so_far_f}")
    if observed_max_so_far_f > 86 and bins.get("85-86", 0) > 1e-6:
        raise ValueError(f"Bin 85-86 must be 0 because observed max is {observed_max_so_far_f}")

    # 5. Confidence is low, medium, or high
    if "confidence" not in output:
        raise ValueError("Missing 'confidence' in output")
    conf = str(output["confidence"]).lower()
    if conf not in ["low", "medium", "high"]:
        raise ValueError(f"Invalid confidence level: {conf}")
        
    return True

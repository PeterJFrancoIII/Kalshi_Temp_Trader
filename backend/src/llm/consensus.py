from typing import Dict, Any, List

def get_top_bin(bins: Dict[str, float]) -> str:
    """Returns the bin with the highest probability."""
    if not bins:
        return ""
    return max(bins.items(), key=lambda x: x[1])[0]

def compare_reviews(review_a: Dict[str, Any], review_b: Dict[str, Any]) -> List[str]:
    """
    Compares two LLM reviews and returns a list of disagreement flags.
    Flags:
    - top bin differs
    - any bin differs by > 0.15
    - confidence high vs low mismatch
    """
    flags = []
    
    bins_a = review_a.get("probability_bins", {})
    bins_b = review_b.get("probability_bins", {})
    
    # 1. Top bin differs
    top_a = get_top_bin(bins_a)
    top_b = get_top_bin(bins_b)
    if top_a and top_b and top_a != top_b:
        flags.append(f"Top bin disagreement: {top_a} vs {top_b}")
        
    # 2. Any bin differs by > 0.15
    all_bins = set(bins_a.keys()) | set(bins_b.keys())
    for b in all_bins:
        val_a = bins_a.get(b, 0.0)
        val_b = bins_b.get(b, 0.0)
        if abs(val_a - val_b) > 0.15:
            flags.append(f"Bin {b} differs by >0.15: {val_a:.2f} vs {val_b:.2f}")
            
    # 3. Confidence high vs low mismatch
    conf_a = str(review_a.get("confidence", "")).lower()
    conf_b = str(review_b.get("confidence", "")).lower()
    if (conf_a == "high" and conf_b == "low") or (conf_a == "low" and conf_b == "high"):
        flags.append(f"Confidence mismatch: {conf_a} vs {conf_b}")
        
    return flags

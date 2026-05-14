"""
Shared normalization utilities for Kalshi contract labels.
"""
import re

def normalize_contract_key(label: str) -> str:
    """
    Normalizes contract labels for consistent map lookup.
    Example: '<86.0' -> '<86', '91-92' -> '91-92', '86.0 - 87.0' -> '86-87'
    """
    if not label:
        return ""
    
    # Remove whitespace
    res = label.replace(" ", "")
    
    # Standardize inequalities: '>=' -> '>', '<=' -> '<' if following common Kalshi patterns
    # But actually Kalshi uses '<86' or '>=95'. 
    # Let's just remove .0 from any numbers
    res = re.sub(r"\.0\b", "", res)
    
    return res

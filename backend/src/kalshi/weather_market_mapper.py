import re
from typing import List, Dict, Any

def map_kalshi_subtitle_to_bin(subtitle: str) -> Dict[str, Any]:
    """
    Maps Kalshi contract ranges (usually in subtitle) to our standard bins:
    <=78, 79-80, 81-82, 83-84, 85-86, >=87
    """
    if not subtitle:
        return {
            "mapped_bin": None,
            "uncertain_mapping": True,
            "reason": "Missing subtitle"
        }
        
    s = subtitle.lower().strip()
    
    # 1. Boundary matches (single number)
    
    # <=78 variants
    if "78" in s and ("below" in s or "lower" in s or "less" in s or "<" in s):
        return {"mapped_bin": "<=78", "uncertain_mapping": False, "reason": "Matched <=78 boundary"}
    if "79" in s and ("below" in s or "<" in s) and "80" not in s:
        # "below 79" -> <=78
        return {"mapped_bin": "<=78", "uncertain_mapping": False, "reason": "Matched below 79 boundary"}
        
    # >=87 variants
    if "87" in s and ("above" in s or "higher" in s or "more" in s or "at least" in s or ">" in s):
        return {"mapped_bin": ">=87", "uncertain_mapping": False, "reason": "Matched >=87 boundary"}
    if "86" in s and ("above" in s or ">" in s) and "85" not in s:
        # "above 86" -> >=87
        return {"mapped_bin": ">=87", "uncertain_mapping": False, "reason": "Matched above 86 boundary"}
        
    # 2. Range matches (two numbers) like "79° to 80°", "79 through 80", or "81 to 82"
    match = re.search(r'(\d+)[^\d]+(\d+)', s)
    if match:
        low = int(match.group(1))
        high = int(match.group(2))
        
        if low == 79 and high == 80: return {"mapped_bin": "79-80", "uncertain_mapping": False, "reason": "Matched 79-80 range"}
        if low == 81 and high == 82: return {"mapped_bin": "81-82", "uncertain_mapping": False, "reason": "Matched 81-82 range"}
        if low == 83 and high == 84: return {"mapped_bin": "83-84", "uncertain_mapping": False, "reason": "Matched 83-84 range"}
        if low == 85 and high == 86: return {"mapped_bin": "85-86", "uncertain_mapping": False, "reason": "Matched 85-86 range"}
        
    # 3. Fallbacks for less structured subtitles (keywords)
    if "79" in s and "80" in s: return {"mapped_bin": "79-80", "uncertain_mapping": False, "reason": "Matched 79 and 80 keywords"}
    if "81" in s and "82" in s: return {"mapped_bin": "81-82", "uncertain_mapping": False, "reason": "Matched 81 and 82 keywords"}
    if "83" in s and "84" in s: return {"mapped_bin": "83-84", "uncertain_mapping": False, "reason": "Matched 83 and 84 keywords"}
    if "85" in s and "86" in s: return {"mapped_bin": "85-86", "uncertain_mapping": False, "reason": "Matched 85 and 86 keywords"}

    return {
        "mapped_bin": None, 
        "uncertain_mapping": True, 
        "reason": f"No regex or keyword match found for: {subtitle}"
    }

def map_markets_to_bins(markets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Takes a list of Kalshi market dictionaries and maps their tickers to our internal bins.
    Returns a structure indicating if mapping was fully successful.
    """
    bin_mapping = {}
    uncertain = False
    reasons = []
    
    for market in markets:
        ticker = market.get("ticker", "")
        subtitle = market.get("subtitle", "")
        result = map_kalshi_subtitle_to_bin(subtitle)
        
        if result["uncertain_mapping"]:
            uncertain = True
            reasons.append(f"{ticker}: {result['reason']}")
        else:
            bin_mapping[result["mapped_bin"]] = ticker
            
    return {
        "mapping": bin_mapping,
        "uncertain_mapping": uncertain,
        "reasons": reasons
    }


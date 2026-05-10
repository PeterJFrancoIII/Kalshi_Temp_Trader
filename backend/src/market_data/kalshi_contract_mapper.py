import re
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

logger = logging.getLogger(__name__)

def extract_contract_thresholds(market: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts condition type and thresholds from a Kalshi market object.
    Condition types: 'above', 'below', 'between', 'unknown'
    """
    ticker = market.get("ticker", "")
    title = market.get("title", "")
    subtitle = market.get("subtitle", "")
    strike_type = market.get("strike_type", "").lower()
    
    res = {
        "condition_type": "unknown",
        "threshold_f": None,
        "range_high_f": None,
        "raw_text": f"{title} {subtitle}".strip(),
        "warnings": []
    }
    
    # 1. Use structured fields if available
    if strike_type == "greater" and market.get("floor_strike") is not None:
        res["condition_type"] = "above"
        res["threshold_f"] = float(market["floor_strike"])
    elif strike_type == "less" and market.get("cap_strike") is not None:
        res["condition_type"] = "below"
        res["threshold_f"] = float(market["cap_strike"])
    elif strike_type == "between" and market.get("floor_strike") is not None and market.get("cap_strike") is not None:
        res["condition_type"] = "between"
        res["threshold_f"] = float(market["floor_strike"])
        res["range_high_f"] = float(market["cap_strike"])
    
    # 2. Regex fallback if structured fields failed or for validation
    if res["condition_type"] == "unknown":
        text = res["raw_text"].lower().replace("\u00b0", "deg")
        
        # Range/Between: "90-91", "90 to 91"
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-|and)\s*(\d+(?:\.\d+)?)", text)
        if range_match:
            res["condition_type"] = "between"
            res["threshold_f"] = float(range_match.group(1))
            res["range_high_f"] = float(range_match.group(2))
        
        # Above: ">91", "91 or above", "above 91", ">=95"
        elif re.search(r"(\d+(?:\.\d+)?)\s*or\s*above", text) or re.search(r"(?:above\s+|>=|>|>\s*)(\d+(?:\.\d+)?)", text):
            match = re.search(r"(\d+(?:\.\d+)?)\s*or\s*above", text) or re.search(r"(?:above\s+|>=|>|>\s*)(\d+(?:\.\d+)?)", text)
            res["condition_type"] = "above"
            val = float(match.group(1))
            if ">=" in text:
                res["threshold_f"] = val - 1.0 # >=95 means >94
            else:
                res["threshold_f"] = val
                
        # Below: "<84", "84 or below", "below 84", "<=89"
        elif re.search(r"(\d+(?:\.\d+)?)\s*or\s*below", text) or re.search(r"(?:below\s+|<=|<|<\s*)(\d+(?:\.\d+)?)", text):
            match = re.search(r"(\d+(?:\.\d+)?)\s*or\s*below", text) or re.search(r"(?:below\s+|<=|<|<\s*)(\d+(?:\.\d+)?)", text)
            res["condition_type"] = "below"
            val = float(match.group(1))
            if "<=" in text:
                res["threshold_f"] = val + 1.0 # <=89 means <90
            else:
                res["threshold_f"] = val

    # 3. Ticker fallback: B86.5
    if res["condition_type"] == "unknown" and "-B" in ticker:
        ticker_match = re.search(r"-B(\d+(?:\.\d+)?)", ticker)
        if ticker_match:
            res["condition_type"] = "above" # B usually denotes binary above/below boundary
            res["threshold_f"] = float(ticker_match.group(1))

    if res["condition_type"] == "unknown":
        res["warnings"].append(f"Could not determine condition for ticker {ticker}")
        
    return res

def bin_string_to_range(bin_str: str) -> tuple[int, int]:
    """
    Converts a bin string like "91-92", ">=95", "<=89" into a tuple of (low, high) integers.
    """
    if bin_str.startswith("<="):
        high = int(bin_str[2:])
        low = -999
    elif bin_str.startswith(">="):
        low = int(bin_str[2:])
        high = 999
    elif bin_str.startswith("<"):
        high = int(bin_str[1:]) - 1
        low = -999
    elif bin_str.startswith(">"):
        low = int(bin_str[1:]) + 1
        high = 999
    elif "-" in bin_str:
        parts = bin_str.split("-")
        low = int(parts[0])
        high = int(parts[1])
    else:
        # Single number
        low = int(bin_str)
        high = int(bin_str)
        
    return low, high

def mapping_to_bin_string(mapping: Dict[str, Any]) -> Optional[str]:
    """
    Converts a contract mapping dict back into a bin string like "91-92", ">=95", "<=89".
    """
    cond = mapping.get("condition_type")
    thresh = mapping.get("threshold_f")
    high = mapping.get("range_high_f")
    
    if thresh is None:
        return None
        
    import math
    
    if cond == "between" and high is not None:
        return f"{int(thresh)}-{int(high)}"
    elif cond == "above":
        # Use > for integer thresholds to match user request
        if thresh == float(int(thresh)):
            return f">{int(thresh)}"
        return f">={math.floor(thresh) + 1}"
    elif cond == "below":
        # Use < for integer thresholds to match user request
        if thresh == float(int(thresh)):
            return f"<{int(thresh)}"
        return f"<={math.ceil(thresh) - 1}"
        
    return None

def market_to_contract_bin(market: Dict[str, Any]) -> Any:
    """
    Converts a Kalshi market object into a ContractBin Pydantic model.
    """
    from shared.types import ContractBin
    
    mapping = extract_contract_thresholds(market)
    label = mapping_to_bin_string(mapping) or "unknown"
    
    low, high = -999, 999
    if label != "unknown":
        low, high = bin_string_to_range(label)
        
    return ContractBin(
        ticker=market.get("ticker", ""),
        event_ticker=market.get("event_ticker"),
        label=label,
        condition_type=mapping.get("condition_type", "unknown"),
        lower_f=low if low != -999 else None,
        upper_f=high if high != 999 else None,
        lower_inclusive=True,
        upper_inclusive=True,
        source="kalshi",
        raw_title=market.get("title"),
        raw_subtitle=market.get("subtitle"),
        warnings=mapping.get("warnings", [])
    )

def parse_kalshi_markets(snapshot_path: Path) -> List[Dict[str, Any]]:
    """
    Parses a Kalshi market snapshot and returns KMIA temperature markets with structured thresholds.
    """
    if not snapshot_path.exists():
        logger.warning(f"Snapshot not found: {snapshot_path}")
        return []
        
    try:
        with open(snapshot_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading snapshot {snapshot_path}: {e}")
        return []
        
    all_markets = data.get("markets", [])
    if not all_markets:
        # Check alternate keys
        all_markets = data.get("selected_temperature_markets", []) or data.get("manual_matches", [])
        
    kmia_markets = []
    for m in all_markets:
        ticker = m.get("ticker", "")
        # Filter for KXHIGHMIA
        if "KXHIGHMIA" not in ticker:
            continue
            
        status = m.get("status", "").lower()
        if status not in ["open", "active", "pending"]:
            continue
            
        mapping = extract_contract_thresholds(m)
        contract_bin = market_to_contract_bin(m)
        
        # Enrich market object
        m["contract_mapping"] = mapping
        m["contract_bin"] = contract_bin.model_dump()
        kmia_markets.append(m)
        
    return kmia_markets

if __name__ == "__main__":
    # Test with a local file if it exists
    test_path = Path("backend/data/processed/kalshi_market_snapshots/latest_kalshi_market_snapshot.json")
    markets = parse_kalshi_markets(test_path)
    print(f"Found {len(markets)} active KMIA markets.")
    for m in markets:
        map_info = m["contract_mapping"]
        print(f"Ticker: {m['ticker']} | {map_info['condition_type']} {map_info['threshold_f']}")

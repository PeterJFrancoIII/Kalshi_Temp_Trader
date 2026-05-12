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
        "ticker": ticker,
        "event_ticker": market.get("event_ticker"),
        "condition_type": "unknown",
        "contract_range": None,
        "lower_inclusive": None,
        "upper_inclusive": None,
        "threshold_f": None,
        "range_high_f": None,
        "yes_bid": market.get("yes_bid_dollars") or (market.get("yes_bid") / 100.0 if market.get("yes_bid") is not None else None),
        "yes_ask": market.get("yes_ask_dollars") or (market.get("yes_ask") / 100.0 if market.get("yes_ask") is not None else None),
        "close_time": market.get("close_time"),
        "parse_warnings": []
    }
    
    # 1. Use structured fields if available
    if strike_type == "greater" and market.get("floor_strike") is not None:
        res["condition_type"] = "above"
        res["threshold_f"] = float(market["floor_strike"])
        res["lower_inclusive"] = False # Kalshi "greater" usually means strict >
        res["contract_range"] = f">{res['threshold_f']}"
    elif strike_type == "less" and market.get("cap_strike") is not None:
        res["condition_type"] = "below"
        res["threshold_f"] = float(market["cap_strike"])
        res["upper_inclusive"] = False # Kalshi "less" usually means strict <
        res["contract_range"] = f"<{res['threshold_f']}"
    elif strike_type == "between" and market.get("floor_strike") is not None and market.get("cap_strike") is not None:
        res["condition_type"] = "between"
        res["threshold_f"] = float(market["floor_strike"])
        res["range_high_f"] = float(market["cap_strike"])
        res["lower_inclusive"] = True
        res["upper_inclusive"] = True
        res["contract_range"] = f"{res['threshold_f']}-{res['range_high_f']}"
    
    # 2. Regex fallback if structured fields failed or for validation
    if res["condition_type"] == "unknown":
        text = f"{title} {subtitle}".strip().lower().replace("\u00b0", "deg")
        
        # Range/Between: "90-91", "90 to 91"
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-|and)\s*(\d+(?:\.\d+)?)", text)
        if range_match:
            res["condition_type"] = "between"
            res["threshold_f"] = float(range_match.group(1))
            res["range_high_f"] = float(range_match.group(2))
            res["lower_inclusive"] = True
            res["upper_inclusive"] = True
            res["contract_range"] = f"{res['threshold_f']}-{res['range_high_f']}"
        
        # Above: ">91", "91 or above", "above 91", ">=95"
        elif re.search(r"(\d+(?:\.\d+)?)\s*or\s*above", text) or re.search(r"(?:above\s+|>=|>|>\s*)(\d+(?:\.\d+)?)", text):
            match = re.search(r"(\d+(?:\.\d+)?)\s*or\s*above", text) or re.search(r"(?:above\s+|>=|>|>\s*)(\d+(?:\.\d+)?)", text)
            res["condition_type"] = "above"
            val = float(match.group(1))
            res["threshold_f"] = val
            if "or above" in text or ">=" in text:
                res["lower_inclusive"] = True
                res["contract_range"] = f">={val}"
            else:
                res["lower_inclusive"] = False
                res["contract_range"] = f">{val}"
                
        # Below: "<84", "84 or below", "below 84", "<=89"
        elif re.search(r"(\d+(?:\.\d+)?)\s*or\s*below", text) or re.search(r"(?:below\s+|<=|<|<\s*)(\d+(?:\.\d+)?)", text):
            match = re.search(r"(\d+(?:\.\d+)?)\s*or\s*below", text) or re.search(r"(?:below\s+|<=|<|<\s*)(\d+(?:\.\d+)?)", text)
            res["condition_type"] = "below"
            val = float(match.group(1))
            res["threshold_f"] = val
            if "or below" in text or "<=" in text:
                res["upper_inclusive"] = True
                res["contract_range"] = f"<={val}"
            else:
                res["upper_inclusive"] = False
                res["contract_range"] = f"<{val}"

    # 3. Ticker fallback: B86.5
    if res["condition_type"] == "unknown" and "-B" in ticker:
        ticker_match = re.search(r"-B(\d+(?:\.\d+)?)", ticker)
        if ticker_match:
            res["condition_type"] = "above"
            res["threshold_f"] = float(ticker_match.group(1))
            res["lower_inclusive"] = False # Ticker B usually denotes boundary, assumed strict >
            res["contract_range"] = f">{res['threshold_f']}"

    if res["condition_type"] == "unknown":
        res["parse_warnings"].append(f"Could not determine condition for ticker {ticker}")
        
    return res

def bin_string_to_range(bin_str: str) -> tuple[int, int]:
    """
    Converts a bin string like "91-92", ">=95", "<=89" into a tuple of (low, high) integers.
    Supports half-degree boundaries by mapping them to clean integer ranges.
    """
    if bin_str.startswith("<="):
        high = int(float(bin_str[2:]))
        low = -999
    elif bin_str.startswith(">="):
        low = int(float(bin_str[2:]))
        high = 999
    elif bin_str.startswith("<"):
        val = float(bin_str[1:])
        if val.is_integer():
            high = int(val) - 1
        else:
            high = int(val) # <84.5 means <=84
        low = -999
    elif bin_str.startswith(">"):
        val = float(bin_str[1:])
        if val.is_integer():
            low = int(val) + 1
        else:
            low = int(val) + 1 # >84.5 means >=85
        high = 999
    elif "-" in bin_str:
        parts = bin_str.split("-")
        low = int(float(parts[0]))
        high = int(float(parts[1]))
    else:
        val = float(bin_str)
        low = int(val)
        high = int(val)
        
    return low, high

def map_distribution_to_bins(integer_dist: Dict[int, float], target_bins: List[str]) -> Dict[str, float]:
    """
    Maps an integer temperature distribution to a set of target bins.
    """
    mapped = {}
    for bin_str in target_bins:
        try:
            lower, upper = bin_string_to_range(bin_str)
            prob = 0.0
            for temp, p in integer_dist.items():
                if lower <= temp <= upper:
                    prob += p
            mapped[bin_str] = prob
        except ValueError:
            mapped[bin_str] = 0.0
    return mapped

def mapping_to_bin_string(mapping: Dict[str, Any]) -> Optional[str]:
    """
    Converts a contract mapping dict back into a bin string like "91-92", ">=95", "<=89".
    """
    cond = mapping.get("condition_type")
    thresh = mapping.get("threshold_f")
    high = mapping.get("range_high_f")
    lower_inc = mapping.get("lower_inclusive")
    upper_inc = mapping.get("upper_inclusive")
    
    if thresh is None:
        return None
        
    import math
    if cond == "between" and high is not None:
        return f"{int(thresh)}-{int(high)}"
    elif cond == "above":
        if thresh == float(int(thresh)):
            if lower_inc:
                return f">={int(thresh)}"
            else:
                return f">{int(thresh)}"
        else:
            if lower_inc:
                return f">={math.ceil(thresh)}"
            else:
                return f">={math.floor(thresh) + 1}"
    elif cond == "below":
        if thresh == float(int(thresh)):
            if upper_inc:
                return f"<={int(thresh)}"
            else:
                return f"<{int(thresh)}"
        else:
            if upper_inc:
                return f"<={math.floor(thresh)}"
            else:
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
        contract_range=mapping.get("contract_range"),
        condition_type=mapping.get("condition_type", "unknown"),
        lower_f=low if low != -999 else None,
        upper_f=high if high != 999 else None,
        lower_inclusive=mapping.get("lower_inclusive") if mapping.get("lower_inclusive") is not None else True,
        upper_inclusive=mapping.get("upper_inclusive") if mapping.get("upper_inclusive") is not None else True,
        source="kalshi",
        raw_title=market.get("title"),
        raw_subtitle=market.get("subtitle"),
        warnings=mapping.get("parse_warnings", [])
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

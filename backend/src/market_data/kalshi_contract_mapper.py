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
        "market_ticker": ticker,
        "event_ticker": market.get("event_ticker"),
        "condition_type": "unknown",
        "contract_range": None,
        "contract_range_label": None,
        "lower_inclusive": None,
        "upper_inclusive": None,
        "threshold_f": None,
        "range_high_f": None,
        "yes_bid": market.get("yes_bid_dollars") or (market.get("yes_bid") / 100.0 if market.get("yes_bid") is not None else None),
        "yes_ask": market.get("yes_ask_dollars") or (market.get("yes_ask") / 100.0 if market.get("yes_ask") is not None else None),
        "close_time": market.get("close_time"),
        "fallback_used": False,
        "uncertain": False,
        "parse_warnings": [],
        "warnings": []
    }
    
    # 0. Extract threshold/type from ticker suffix if present
    ticker_thresh = None
    ticker_type = None  # "T" or "B"
    if "-B" in ticker:
        ticker_match = re.search(r"-B(\d+(?:\.\d+)?)", ticker)
        if ticker_match:
            ticker_thresh = float(ticker_match.group(1))
            ticker_type = "B"
    elif "-T" in ticker:
        ticker_match = re.search(r"-T(\d+(?:\.\d+)?)", ticker)
        if ticker_match:
            ticker_thresh = float(ticker_match.group(1))
            ticker_type = "T"
            
    # 1. Use structured fields if available
    structured_parsed = False
    if strike_type == "greater" and market.get("floor_strike") is not None:
        res["condition_type"] = "above"
        res["threshold_f"] = float(market["floor_strike"])
        res["lower_inclusive"] = False # Kalshi "greater" usually means strict >
        res["contract_range"] = f">{res['threshold_f']}"
        structured_parsed = True
    elif strike_type == "less" and market.get("cap_strike") is not None:
        res["condition_type"] = "below"
        res["threshold_f"] = float(market["cap_strike"])
        res["upper_inclusive"] = False # Kalshi "less" usually means strict <
        res["contract_range"] = f"<{res['threshold_f']}"
        structured_parsed = True
    elif strike_type == "between" and market.get("floor_strike") is not None and market.get("cap_strike") is not None:
        res["condition_type"] = "between"
        res["threshold_f"] = float(market["floor_strike"])
        res["range_high_f"] = float(market["cap_strike"])
        res["lower_inclusive"] = True
        res["upper_inclusive"] = True
        res["contract_range"] = f"{res['threshold_f']}-{res['range_high_f']}"
        structured_parsed = True
        
    # 2. Regex fallback if structured fields failed
    if res["condition_type"] == "unknown":
        text = f"{title} {subtitle}".strip().lower().replace("\u00b0", "deg")
        
        # Range/Between: "90-91", "90 to 91", "90 and 91", "91 or 92", "91/92"
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-|and|or|and/or|/)\s*(\d+(?:\.\d+)?)", text)
        
        above_match_1 = re.search(r"(\d+(?:\.\d+)?)\s*or\s*(?:above|greater)", text)
        above_match_2 = re.search(r"(?:above|greater\s+than|>=|>)\s*(\d+(?:\.\d+)?)", text)
        above_match = above_match_1 or above_match_2
        
        below_match_1 = re.search(r"(\d+(?:\.\d+)?)\s*or\s*(?:below|less)", text)
        below_match_2 = re.search(r"(?:below|less\s+than|<=|<)\s*(\d+(?:\.\d+)?)", text)
        below_match = below_match_1 or below_match_2
        
        if range_match:
            res["condition_type"] = "between"
            res["threshold_f"] = float(range_match.group(1))
            res["range_high_f"] = float(range_match.group(2))
            res["lower_inclusive"] = True
            res["upper_inclusive"] = True
            res["contract_range"] = f"{res['threshold_f']}-{res['range_high_f']}"
        elif above_match and below_match:
            res["condition_type"] = "unknown"
            res["uncertain"] = True
            res["parse_warnings"].append("Conflicting above and below patterns in text")
        elif above_match:
            res["condition_type"] = "above"
            val = float(above_match.group(1))
            res["threshold_f"] = val
            if "or above" in text or "or greater" in text or ">=" in text:
                res["lower_inclusive"] = True
                res["contract_range"] = f">={val}"
            else:
                res["lower_inclusive"] = False
                res["contract_range"] = f">{val}"
        elif below_match:
            res["condition_type"] = "below"
            val = float(below_match.group(1))
            res["threshold_f"] = val
            if "or below" in text or "or less" in text or "<=" in text:
                res["upper_inclusive"] = True
                res["contract_range"] = f"<={val}"
            else:
                res["upper_inclusive"] = False
                res["contract_range"] = f"<{val}"
        else:
            # Check if text contains any numbers
            all_numbers = re.findall(r"\d+(?:\.\d+)?", text)
            if all_numbers:
                res["condition_type"] = "unknown"
                res["uncertain"] = True
                res["parse_warnings"].append(f"Numbers found in text ({all_numbers}) but no recognized condition pattern")

    # 3. Ticker fallback
    if res["condition_type"] == "unknown" and not res["uncertain"]:
        if ticker_type == "B" and ticker_thresh is not None:
            res["condition_type"] = "above"
            res["threshold_f"] = ticker_thresh
            res["lower_inclusive"] = False # Ticker B usually denotes boundary, assumed strict >
            res["contract_range"] = f">{res['threshold_f']}"
        elif ticker_type == "T" and ticker_thresh is not None:
            # Extract threshold but do NOT infer direction (above/below) from T suffix alone.
            # Leave condition_type as "unknown" for second-pass fallback in parse_kalshi_markets.
            res["threshold_f"] = ticker_thresh

    # 4. Validation / Conflict checking
    if res["condition_type"] != "unknown":
        text = f"{title} {subtitle}".strip().lower().replace("\u00b0", "deg")
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-|and)\s*(\d+(?:\.\d+)?)", text)
        above_match_1 = re.search(r"(\d+(?:\.\d+)?)\s*or\s*(?:above|greater)", text)
        above_match_2 = re.search(r"(?:above|greater\s+than|>=|>)\s*(\d+(?:\.\d+)?)", text)
        above_match = above_match_1 or above_match_2
        below_match_1 = re.search(r"(\d+(?:\.\d+)?)\s*or\s*(?:below|less)", text)
        below_match_2 = re.search(r"(?:below|less\s+than|<=|<)\s*(\d+(?:\.\d+)?)", text)
        below_match = below_match_1 or below_match_2
        
        conflict = False
        conflict_reason = ""
        
        # Check condition conflicts
        if res["condition_type"] == "above":
            if below_match and not above_match:
                conflict = True
                conflict_reason = "Parsed/structured says above, but text says below"
            elif range_match:
                conflict = True
                conflict_reason = "Parsed/structured says above, but text says range/between"
        elif res["condition_type"] == "below":
            if above_match and not below_match:
                conflict = True
                conflict_reason = "Parsed/structured says below, but text says above"
            elif range_match:
                conflict = True
                conflict_reason = "Parsed/structured says below, but text says range/between"
        elif res["condition_type"] == "between":
            if (above_match or below_match) and not range_match:
                conflict = True
                conflict_reason = "Parsed/structured says between, but text does not have a range/between pattern"
                
        # Check threshold conflicts if text has numbers
        if not conflict and res["threshold_f"] is not None:
            text_numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
            if text_numbers:
                if res["condition_type"] in ("above", "below"):
                    if res["threshold_f"] not in text_numbers:
                        if not any(abs(res["threshold_f"] - tn) < 0.01 for tn in text_numbers):
                            conflict = True
                            conflict_reason = f"Parsed threshold {res['threshold_f']} does not match any numbers in text {text_numbers}"
                elif res["condition_type"] == "between" and res["range_high_f"] is not None:
                    if res["threshold_f"] not in text_numbers or res["range_high_f"] not in text_numbers:
                        if not (any(abs(res["threshold_f"] - tn) < 0.01 for tn in text_numbers) and any(abs(res["range_high_f"] - tn) < 0.01 for tn in text_numbers)):
                            conflict = True
                            conflict_reason = f"Parsed range {res['threshold_f']}-{res['range_high_f']} does not match numbers in text {text_numbers}"
                            
        # Check ticker conflicts
        if not conflict and ticker_thresh is not None and res["condition_type"] in ("above", "below"):
            if res["threshold_f"] is not None and abs(res["threshold_f"] - ticker_thresh) > 0.01:
                conflict = True
                conflict_reason = f"Parsed threshold {res['threshold_f']} does not match ticker threshold {ticker_thresh}"
                
        if conflict:
            res["condition_type"] = "unknown"
            res["uncertain"] = True
            res["parse_warnings"].append(f"Ambiguous or conflicting contract data: {conflict_reason}")

    if res["condition_type"] == "unknown":
        res["uncertain"] = True
        res["parse_warnings"].append(f"Could not determine condition for ticker {ticker}")
        
    res["contract_range_label"] = mapping_to_bin_string(res) or "unknown"
    res["warnings"] = res["parse_warnings"]
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
                return f">={int(thresh) + 1}"
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
                return f"<={int(thresh) - 1}"
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
    
    # Use existing mapping if already enriched, otherwise extract
    mapping = market.get("contract_mapping") or extract_contract_thresholds(market)
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
        warnings=mapping.get("parse_warnings", []) + ([f"Fallback direction used"] if mapping.get("fallback_used") else [])
    )

def apply_parsing_fallbacks(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Applies multi-market fallbacks for unresolved contracts.
    Specifically: T-contracts where direction is unknown.
    Rule: lowest T threshold = below, highest T threshold = above.
    """
    # Group unknown T-markets by event
    unknowns_by_event = {}
    for m in markets:
        mapping = m.get("contract_mapping", {})
        ticker = m.get("ticker", "")
        if mapping.get("condition_type") == "unknown" and "-T" in ticker:
            et = m.get("event_ticker", "unknown_event")
            unknowns_by_event.setdefault(et, []).append(m)
            
    for et, m_list in unknowns_by_event.items():
        if len(m_list) < 1:
            continue
            
        # Sort by threshold
        m_list.sort(key=lambda x: x["contract_mapping"].get("threshold_f") or 0)
        
        # Lowest T threshold = below
        lowest = m_list[0]
        mapping_low = lowest["contract_mapping"]
        mapping_low["condition_type"] = "below"
        mapping_low["upper_inclusive"] = False
        mapping_low["contract_range"] = f"<{mapping_low['threshold_f']}"
        mapping_low["fallback_used"] = True
        mapping_low["uncertain"] = False
        mapping_low["parse_warnings"].append(f"Inferred direction 'below' as lowest T-contract in event {et}")
        mapping_low["contract_range_label"] = mapping_to_bin_string(mapping_low) or "unknown"
        mapping_low["warnings"] = mapping_low["parse_warnings"]
        
        # Re-generate contract_bin for the market
        lowest["contract_bin"] = market_to_contract_bin(lowest).model_dump()
        
        # Highest T threshold = above (if it's a different market)
        if len(m_list) > 1:
            highest = m_list[-1]
            mapping_high = highest["contract_mapping"]
            mapping_high["condition_type"] = "above"
            mapping_high["lower_inclusive"] = False
            mapping_high["contract_range"] = f">{mapping_high['threshold_f']}"
            mapping_high["fallback_used"] = True
            mapping_high["uncertain"] = False
            mapping_high["parse_warnings"].append(f"Inferred direction 'above' as highest T-contract in event {et}")
            mapping_high["contract_range_label"] = mapping_to_bin_string(mapping_high) or "unknown"
            mapping_high["warnings"] = mapping_high["parse_warnings"]
            
            # Re-generate contract_bin for the market
            highest["contract_bin"] = market_to_contract_bin(highest).model_dump()
            
    return markets

def parse_kalshi_markets(snapshot_path: Path, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parses a Kalshi market snapshot and returns KMIA temperature markets with structured thresholds.
    If target_date is provided (YYYY-MM-DD), only returns markets for that date.
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
            
        # Optional: Filter by target date
        if target_date:
            from shared.timestamp_utils import parse_ticker_date
            ticker_date = parse_ticker_date(ticker)
            if ticker_date and ticker_date != target_date:
                continue
            
        mapping = extract_contract_thresholds(m)
        contract_bin = market_to_contract_bin(m)
        
        # Enrich market object
        m["contract_mapping"] = mapping
        m["contract_bin"] = contract_bin.model_dump()
        kmia_markets.append(m)
        
    return apply_parsing_fallbacks(kmia_markets)

if __name__ == "__main__":
    # Test with a local file if it exists
    test_path = Path("backend/data/processed/kalshi_market_snapshots/latest_kalshi_market_snapshot.json")
    markets = parse_kalshi_markets(test_path)
    print(f"Found {len(markets)} active KMIA markets.")
    for m in markets:
        map_info = m["contract_mapping"]
        print(f"Ticker: {m['ticker']} | {map_info['condition_type']} {map_info['threshold_f']}")

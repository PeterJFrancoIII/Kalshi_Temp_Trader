from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class OrderBookMetrics:
    yes_bid: int
    yes_ask: int
    no_bid: int
    no_ask: int
    yes_mid: float
    no_mid: float
    spread: int
    depth_summary: int # Total quantity in top level bids

def calculate_orderbook_metrics(raw_orderbook: Dict[str, Any]) -> OrderBookMetrics:
    """
    Computes standard metrics from a Kalshi orderbook response.
    Prices are scaled to cents (0-100).
    
    Rule:
    yes bid at X cents = no ask at 100 - X cents.
    no bid at X cents = yes ask at 100 - X cents.
    """
    orderbook = raw_orderbook.get("orderbook_fp", {})
    yes_bids = orderbook.get("yes_dollars", [])
    no_bids = orderbook.get("no_dollars", [])
    
    # Default to 0 cents if no bids available
    yes_bid_cents = 0
    no_bid_cents = 0
    
    if yes_bids:
        # Highest bid is the first element, convert to cents
        yes_bid_cents = int(float(yes_bids[0][0]) * 100)
        
    if no_bids:
        no_bid_cents = int(float(no_bids[0][0]) * 100)
        
    # Apply Rule:
    # no bid at X implies yes ask at 100 - X
    # yes bid at X implies no ask at 100 - X
    yes_ask_cents = 100 - no_bid_cents if no_bid_cents > 0 else 100
    no_ask_cents = 100 - yes_bid_cents if yes_bid_cents > 0 else 100
    
    # Mid and Spread
    yes_mid = (yes_bid_cents + yes_ask_cents) / 2.0
    no_mid = (no_bid_cents + no_ask_cents) / 2.0
    spread = yes_ask_cents - yes_bid_cents
    
    # Depth summary: Sum of top quantities
    depth_yes = int(float(yes_bids[0][1])) if yes_bids else 0
    depth_no = int(float(no_bids[0][1])) if no_bids else 0
    depth_summary = depth_yes + depth_no
        
    return OrderBookMetrics(
        yes_bid=yes_bid_cents,
        yes_ask=yes_ask_cents,
        no_bid=no_bid_cents,
        no_ask=no_ask_cents,
        yes_mid=yes_mid,
        no_mid=no_mid,
        spread=spread,
        depth_summary=depth_summary
    )


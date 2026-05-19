from typing import List, Dict, Any
from market_data.kalshi_public_client import KalshiPublicClient

def discover_miami_daily_high_markets(client: KalshiPublicClient) -> List[Dict[str, Any]]:
    """
    Finds open Kalshi markets related to Miami/KMIA daily high temperatures.
    """
    # Fetch all open markets.
    # Note: We rely on the /markets endpoint. If pagination is needed later,
    # we can add cursor iteration, but this satisfies the MVP.
    response = client.get_markets(status="open")
    markets = response.get("markets", [])
    
    miami_markets = []
    for market in markets:
        title = market.get("title", "").lower()
        ticker = market.get("ticker", "").lower()
        subtitle = market.get("subtitle", "").lower()
        
        # Check if it relates to Miami/KMIA high temperature
        is_miami = "miami" in title or "miami" in subtitle or "kmia" in title or "kmia" in subtitle or "mia" in ticker
        is_high_temp = "high" in title or "temperature" in title
        
        if is_miami and is_high_temp:
            miami_markets.append(market)
            
    return miami_markets

import requests
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

class KalshiPublicClient:
    """
    Read-only unauthenticated client for Kalshi public market data.
    """
    
    KALSHI_PUBLIC_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def __init__(self, base_url: str = KALSHI_PUBLIC_BASE_URL):
        self.base_url = base_url

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Internal helper for unauthenticated GET requests."""
        url = f"{self.base_url}{path}"
        response = requests.get(url, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
        return response.json()

    def get_market(self, market_ticker: str) -> Dict[str, Any]:
        """Fetch details for a specific market ticker."""
        return self._get(f"/markets/{market_ticker}")

    def get_markets_for_series(self, series_ticker: str, status: str = "open") -> Dict[str, Any]:
        """Fetch markets for a specific series (e.g., KXKX)."""
        return self._get("/markets", params={"series_ticker": series_ticker, "status": status})

    def get_orderbook(self, market_ticker: str) -> Dict[str, Any]:
        """Fetch orderbook for a specific market ticker."""
        return self._get(f"/markets/{market_ticker}/orderbook")

    def discover_temperature_markets(self, query_terms: List[str]) -> Dict[str, Any]:
        """
        Exhaustively discover markets matching query terms across multiple endpoints.
        Returns a dict with detailed discovery metadata and candidates.
        """
        attempts = []
        all_markets = []
        
        # 1. Attempt: Get all open markets
        m_path = "/markets"
        m_params = {"status": "open", "limit": 1000}
        attempts.append({"endpoint": m_path, "params": m_params})
        try:
            m_resp = self._get(m_path, params=m_params)
            markets = m_resp.get("markets", [])
            all_markets.extend(markets)
            attempts[-1]["count"] = len(markets)
            attempts[-1]["status"] = "success"
        except Exception as e:
            attempts[-1]["status"] = "error"
            attempts[-1]["error"] = str(e)

        # 2. Attempt: Get all series (to check for weather series)
        s_path = "/series"
        attempts.append({"endpoint": s_path, "params": {}})
        try:
            s_resp = self._get(s_path)
            series = s_resp.get("series", [])
            attempts[-1]["count"] = len(series)
            attempts[-1]["status"] = "success"
            
            # If we find a series matching 'temperature', 'weather', or 'miami'
            # we could potentially crawl its markets specifically.
            # For now, we just log the series count.
        except Exception as e:
            attempts[-1]["status"] = "error"
            attempts[-1]["error"] = str(e)

        # Candidate Discovery (Broad match)
        candidates = []
        seen_tickers = set()
        
        for market in all_markets:
            ticker = market.get("ticker", "")
            if ticker in seen_tickers:
                continue
            seen_tickers.add(ticker)
            
            search_text = (
                f"{market.get('title', '')} {market.get('subtitle', '')} "
                f"{ticker} {market.get('category', '')} {market.get('event_ticker', '')} "
                f"{market.get('series_ticker', '')}"
            ).lower()
            
            if any(term.lower() in search_text for term in query_terms):
                candidates.append(market)
                
        return {
            "endpoint_attempts": attempts,
            "total_raw_markets_seen": len(seen_tickers),
            "candidate_markets": candidates
        }

    def save_market_snapshot(self, snapshot: Dict[str, Any], output_dir: Path) -> Path:
        """
        Save a market data snapshot to a JSON file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        filename = f"kalshi_market_snapshot_{timestamp}.json"
        filepath = output_dir / filename
        
        # Also maintain a 'latest' file
        latest_path = output_dir / "latest_kalshi_market_snapshot.json"
        
        with open(filepath, 'w') as f:
            json.dump(snapshot, f, indent=2)
            
        # Copy to latest
        with open(latest_path, 'w') as f:
            json.dump(snapshot, f, indent=2)
            
        return filepath

import requests
from typing import Dict, Any, Optional

class KalshiPublicClient:
    """
    Read-only unauthenticated client for Kalshi market data.
    Uses the requests library as per requirement.
    """
    
    # Standard public URL from the docs
    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or self.BASE_URL

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Internal helper for unauthenticated GET requests.
        """
        url = f"{self.base_url}{path}"
        response = requests.get(url, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
        return response.json()

    def get_events(self, series_ticker: Optional[str] = None, status: str = "open") -> Dict[str, Any]:
        """
        Fetches events from Kalshi.
        """
        params = {}
        if series_ticker:
            params["series_ticker"] = series_ticker
        if status:
            params["status"] = status
        return self._get("/events", params=params)

    def get_markets(self, series_ticker: Optional[str] = None, status: str = "open") -> Dict[str, Any]:
        """
        Fetches markets from Kalshi.
        """
        params = {}
        if series_ticker:
            params["series_ticker"] = series_ticker
        if status:
            params["status"] = status
        return self._get("/markets", params=params)

    def get_market(self, ticker: str) -> Dict[str, Any]:
        """
        Fetches a specific market by ticker.
        """
        return self._get(f"/markets/{ticker}")

    def get_orderbook(self, ticker: str) -> Dict[str, Any]:
        """
        Fetches the orderbook for a specific market.
        """
        return self._get(f"/markets/{ticker}/orderbook")


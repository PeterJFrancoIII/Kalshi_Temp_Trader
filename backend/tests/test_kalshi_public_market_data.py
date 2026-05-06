import os
import pytest
from market_data.kalshi_public_client import KalshiPublicClient

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def test_kalshi_client_no_auth_references():
    """
    Verify that the KalshiPublicClient does not contain logic for authentication,
    API keys, or private secrets.
    """
    with open("backend/src/market_data/kalshi_public_client.py", "r") as f:
        content = f.read().lower()
        
    # We allow "unauthenticated" but forbid "auth" otherwise
    content_clean = content.replace("unauthenticated", "READ_ONLY_MODE")
    
    forbidden = ["api_key", "secret_key", "private_key", "auth_", "token", "sign", "password"]
    for term in forbidden:
        assert term not in content_clean, f"Potentially authenticated term '{term}' found in public client."

def test_kalshi_client_mocked_discovery(monkeypatch):
    """
    Verify discovery logic with mocked API responses.
    """
    class MockResponse:
        def json(self):
            return {
                "markets": [
                    {"title": "Will it be hot in Miami?", "ticker": "MIA-HOT", "subtitle": "High temp > 90"},
                    {"title": "Rain in Seattle", "ticker": "SEA-RAIN", "subtitle": "Wet"}
                ]
            }
        def raise_for_status(self):
            pass

    def mock_get(*args, **kwargs):
        return MockResponse()

    import requests
    monkeypatch.setattr(requests, "get", mock_get)
    
    client = KalshiPublicClient()
    discovered = client.discover_temperature_markets(["miami", "high"])
    
    assert len(discovered) == 1
    assert discovered[0]["ticker"] == "MIA-HOT"

def test_kalshi_updater_logic():
    """
    Verify that the updater correctly references the market data module.
    """
    with open("backend/src/market_data/update_kalshi_snapshots.py", "r") as f:
        content = f.read()
    
    assert "kalshi_market_snapshots" in content
    assert "KalshiPublicClient" in content

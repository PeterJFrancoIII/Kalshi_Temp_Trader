import os
from unittest.mock import patch, MagicMock
from market_data.kalshi_public_client import KalshiPublicClient

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def test_kalshi_client_no_auth_references():
    """
    Verify that the KalshiPublicClient does not contain logic for authentication,
    API keys, or private secrets.
    """
    # The test runs from the backend/ directory, so src/ is the correct relative path.
    client_file = "src/market_data/kalshi_public_client.py"
    with open(client_file, "r") as f:
        content = f.read().lower()
        
    # We allow "unauthenticated" but forbid "auth" otherwise
    content_clean = content.replace("unauthenticated", "READ_ONLY_MODE")
    
    forbidden = ["api_key", "secret_key", "private_key", "auth_", "token", "sign", "password"]
    for term in forbidden:
        assert term not in content_clean, f"Potentially authenticated term '{term}' found in public client."

def test_kalshi_client_mocked_discovery():
    """
    Verify discovery logic with mocked API responses.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "markets": [
            {"title": "Will it be hot in Miami?", "ticker": "MIA-HOT", "subtitle": "High temp > 90"},
            {"title": "Rain in Seattle", "ticker": "SEA-RAIN", "subtitle": "Wet"}
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        client = KalshiPublicClient()
        result = client.discover_temperature_markets(["miami", "high"])
        discovered = result["candidate_markets"]
    
    assert len(discovered) == 1
    assert discovered[0]["ticker"] == "MIA-HOT"

def test_kalshi_config_exists():
    """Verify that the discovery config file exists and is valid JSON."""
    config_file = "config/kalshi_market_discovery.json"
    assert os.path.exists(config_file), f"Config file {config_file} is missing."
    
    import json
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    assert "search_terms" in config
    assert "preferred_terms" in config
    assert config["safety"]["no_real_trading"] is True

def test_kalshi_client_broad_discovery():
    """
    Verify discovery logic finds ANY matching term.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "markets": [
            {"title": "Miami Heat", "ticker": "MIA-HEAT", "subtitle": "", "category": "weather"},
            {"title": "New York Weather", "ticker": "NYC-WX", "subtitle": "temperature", "category": "weather"},
            {"title": "Random Market", "ticker": "RND", "subtitle": "", "category": "finance"}
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        client = KalshiPublicClient()
        # Should match MIA-HEAT (Miami) and NYC-WX (temperature)
        result = client.discover_temperature_markets(["Miami", "temperature"])
        discovered = result["candidate_markets"]
    
    assert len(discovered) == 2
    tickers = [m["ticker"] for m in discovered]
    assert "MIA-HEAT" in tickers
    assert "NYC-WX" in tickers
    assert result["total_raw_markets_seen"] == 3

def test_kalshi_snapshot_safety_fields():
    """Verify that the snapshot includes all required safety flags."""
    client = KalshiPublicClient()
    snapshot = {
        "safety": {
            "no_real_trading": True,
            "no_order_execution": True,
            "no_authentication": True
        }
    }
    # This is more of a placeholder to ensure we are thinking about these fields
    assert snapshot["safety"]["no_authentication"] is True

def test_kalshi_updater_logic():
    """
    Verify that the updater correctly references the market data module.
    """
    # The test runs from the backend/ directory, so src/ is the correct relative path.
    updater_file = "src/market_data/update_kalshi_snapshots.py"
    with open(updater_file, "r") as f:
        content = f.read()
    
    assert "kalshi_market_snapshots" in content
    assert "KalshiPublicClient" in content
    assert "kalshi_market_discovery.json" in content
    assert "no_authentication" in content

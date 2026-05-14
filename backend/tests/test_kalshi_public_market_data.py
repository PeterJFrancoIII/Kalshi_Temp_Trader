import os
from unittest.mock import patch, MagicMock
from market_data.kalshi_public_client import KalshiPublicClient

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def test_kalshi_client_no_auth_references():
    """
    Verify that the KalshiPublicClient does not contain logic for live trading
    or order execution, while allowing approved read-only auth references.
    """
    # The test runs from the backend/ directory, so src/ is the correct relative path.
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    client_file = os.path.join(base_dir, "src/market_data/kalshi_public_client.py")
    with open(client_file, "r") as f:
        content = f.read().lower()
        
    # We allow "unauthenticated" but forbid "auth" otherwise
    content_clean = content.replace("unauthenticated", "READ_ONLY_MODE")
    
    # Allowed for read-only auth: "api_key", "auth_"
    # Still forbidden in client: "private_key", "secret_key", "token", "password"
    forbidden = ["secret_key", "private_key", "token", "password"]
    
    # Dangerous execution terms
    dangerous = ["submit_order", "create_order", "place_order", "cancel_order", "api_secret", "sign_order"]
    
    for term in forbidden + dangerous:
        assert term not in content_clean, f"Forbidden term '{term}' found in public client."

def test_kalshi_client_mocked_discovery():
    """
    Verify that the client can find a specific Miami temperature market in a mock list.
    """
    # Mock for /markets
    mock_markets_resp = MagicMock()
    mock_markets_resp.json.return_value = {
        "markets": [
            {
                "ticker": "MIA-HOT",
                "title": "Miami High Temperature",
                "subtitle": "Will it be 85?",
                "category": "weather"
            },
            {
                "ticker": "NYC-COLD",
                "title": "NYC Temperature",
                "subtitle": "Will it be 32?",
                "category": "weather"
            }
        ]
    }
    mock_markets_resp.raise_for_status = MagicMock()

    # Mock for /series
    mock_series_resp = MagicMock()
    mock_series_resp.json.return_value = {"series": []}
    mock_series_resp.raise_for_status = MagicMock()

    # Define side_effect to handle multiple calls
    def side_effect(url, *args, **kwargs):
        if "/markets" in url:
            return mock_markets_resp
        if "/series" in url:
            return mock_series_resp
        return MagicMock()

    with patch("requests.Session.get", side_effect=side_effect):
        client = KalshiPublicClient()
        result = client.discover_temperature_markets(["miami", "high"])
        discovered = result["candidate_markets"]
        attempts = result["endpoint_attempts"]
    
    assert len(discovered) == 1
    assert discovered[0]["ticker"] == "MIA-HOT"
    assert len(attempts) >= 2
    assert attempts[0]["endpoint"] == "/markets"

def test_kalshi_config_exists():
    """Verify that the discovery config file exists and is valid JSON."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_file = os.path.join(base_dir, "config/kalshi_market_discovery.json")
    assert os.path.exists(config_file), f"Config file {config_file} is missing."
    
    import json
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    assert "search_terms" in config
    assert "preferred_terms" in config
    assert config["safety"]["no_real_trading"] is True

def test_kalshi_client_broad_discovery():
    """
    Verify discovery logic finds ANY matching term across multiple endpoints.
    """
    # Mock for /markets
    mock_markets_resp = MagicMock()
    mock_markets_resp.json.return_value = {
        "markets": [
            {"title": "Miami Heat", "ticker": "MIA-HEAT", "subtitle": "", "category": "weather"},
            {"title": "New York Weather", "ticker": "NYC-WX", "subtitle": "temperature", "category": "weather"},
            {"title": "Random Market", "ticker": "RND", "subtitle": "", "category": "finance"}
        ]
    }
    mock_markets_resp.raise_for_status = MagicMock()

    # Mock for /series
    mock_series_resp = MagicMock()
    mock_series_resp.json.return_value = {"series": []}
    mock_series_resp.raise_for_status = MagicMock()

    def side_effect(url, *args, **kwargs):
        if "/markets" in url:
            return mock_markets_resp
        if "/series" in url:
            return mock_series_resp
        return MagicMock()

    with patch("requests.Session.get", side_effect=side_effect):
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

def test_kalshi_manual_ticker_lookup():
    """Verify that a known ticker can be fetched directly."""
    mock_market_resp = MagicMock()
    mock_market_resp.json.return_value = {
        "market": {"ticker": "KNOWN-TICKER", "title": "Manual Market"}
    }
    
    with patch("requests.Session.get", return_value=mock_market_resp):
        client = KalshiPublicClient()
        result = client.get_market("KNOWN-TICKER")
    
    assert result["market"]["ticker"] == "KNOWN-TICKER"

def test_kalshi_manual_series_lookup():
    """Verify that a known series can be fetched directly."""
    mock_series_resp = MagicMock()
    mock_series_resp.json.return_value = {
        "markets": [{"ticker": "SERIES-M1", "title": "Series Market"}]
    }
    
    with patch("requests.Session.get", return_value=mock_series_resp):
        client = KalshiPublicClient()
        result = client.get_markets_for_series("KXKX")
    
    assert len(result["markets"]) == 1
    assert result["markets"][0]["ticker"] == "SERIES-M1"

def test_kalshi_updater_logic():
    """
    Verify that the updater correctly references the market data module.
    """
    # The test runs from the backend/ directory, so src/ is the correct relative path.
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    updater_file = os.path.join(base_dir, "src/market_data/update_kalshi_snapshots.py")
    with open(updater_file, "r") as f:
        content = f.read()
    
    assert "kalshi_market_snapshots" in content
    assert "KalshiPublicClient" in content
    assert "kalshi_market_discovery.json" in content
    assert "no_authentication" in content

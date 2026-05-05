from kalshi.weather_market_mapper import map_kalshi_subtitle_to_bin, map_markets_to_bins
from kalshi.orderbook import calculate_orderbook_metrics, OrderBookMetrics

def test_map_kalshi_subtitle_to_bin():
    # Test valid mappings
    res = map_kalshi_subtitle_to_bin("78° or lower")
    assert res["mapped_bin"] == "<=78"
    assert res["uncertain_mapping"] is False
    
    res = map_kalshi_subtitle_to_bin("79° to 80°")
    assert res["mapped_bin"] == "79-80"
    
    res = map_kalshi_subtitle_to_bin("81° to 82°")
    assert res["mapped_bin"] == "81-82"
    
    res = map_kalshi_subtitle_to_bin("83° to 84°")
    assert res["mapped_bin"] == "83-84"
    
    res = map_kalshi_subtitle_to_bin("85° to 86°")
    assert res["mapped_bin"] == "85-86"
    
    res = map_kalshi_subtitle_to_bin("87° or higher")
    assert res["mapped_bin"] == ">=87"
    
    # Test fallback
    res = map_kalshi_subtitle_to_bin("85 to 86")
    assert res["mapped_bin"] == "85-86"
    
    res = map_kalshi_subtitle_to_bin("78 or below")
    assert res["mapped_bin"] == "<=78"
    
    res = map_kalshi_subtitle_to_bin("at or below 78")
    assert res["mapped_bin"] == "<=78"
    
    res = map_kalshi_subtitle_to_bin("below 79")
    assert res["mapped_bin"] == "<=78"
    
    res = map_kalshi_subtitle_to_bin("79 through 80")
    assert res["mapped_bin"] == "79-80"
    
    res = map_kalshi_subtitle_to_bin("between 79 and 80")
    assert res["mapped_bin"] == "79-80"
    
    res = map_kalshi_subtitle_to_bin("81 through 82")
    assert res["mapped_bin"] == "81-82"
    
    res = map_kalshi_subtitle_to_bin("83 through 84")
    assert res["mapped_bin"] == "83-84"
    
    res = map_kalshi_subtitle_to_bin("85 through 86")
    assert res["mapped_bin"] == "85-86"
    
    res = map_kalshi_subtitle_to_bin("87 or above")
    assert res["mapped_bin"] == ">=87"
    
    res = map_kalshi_subtitle_to_bin("at least 87")
    assert res["mapped_bin"] == ">=87"
    
    res = map_kalshi_subtitle_to_bin("above 86")
    assert res["mapped_bin"] == ">=87"
    
    # Test uncertain mapping
    res = map_kalshi_subtitle_to_bin("Unknown format 100 degrees")
    assert res["mapped_bin"] is None
    assert res["uncertain_mapping"] is True
    assert "No regex or keyword match" in res["reason"]

def test_map_markets_to_bins():
    markets = [
        {"ticker": "KXHIGHMIA-231102-T81", "subtitle": "81° to 82°"},
        {"ticker": "KXHIGHMIA-231102-T83", "subtitle": "83° to 84°"},
        {"ticker": "KXHIGHMIA-231102-T87", "subtitle": "87° or higher"}
    ]
    mapping_res = map_markets_to_bins(markets)
    assert mapping_res["uncertain_mapping"] is False
    assert mapping_res["mapping"] == {
        "81-82": "KXHIGHMIA-231102-T81",
        "83-84": "KXHIGHMIA-231102-T83",
        ">=87": "KXHIGHMIA-231102-T87",
    }
    
def test_map_markets_to_bins_uncertain():
    markets = [
        {"ticker": "KXHIGHMIA-231102-T81", "subtitle": "81° to 82°"},
        {"ticker": "KXHIGHMIA-231102-TXYZ", "subtitle": "random string"}
    ]
    mapping_res = map_markets_to_bins(markets)
    assert mapping_res["uncertain_mapping"] is True
    assert mapping_res["mapping"] == {"81-82": "KXHIGHMIA-231102-T81"}
    assert any("random string" in r for r in mapping_res["reasons"])

def test_calculate_orderbook_metrics():
    # Example raw orderbook response (mocked)
    raw_orderbook = {
        "orderbook_fp": {
            "yes_dollars": [["0.1500", "100.00"], ["0.1400", "50.00"]],
            "no_dollars": [["0.8000", "200.00"], ["0.7500", "150.00"]]
        }
    }
    
    metrics = calculate_orderbook_metrics(raw_orderbook)
    
    # yes_bid_cents = 15
    # no_bid_cents = 80
    # yes_ask_cents = 100 - 80 = 20
    # no_ask_cents = 100 - 15 = 85
    # yes_mid = (15 + 20) / 2 = 17.5
    # no_mid = (80 + 85) / 2 = 82.5
    # spread = 20 - 15 = 5
    # depth_summary = 100 + 200 = 300 (top quantities)
    
    assert metrics.yes_bid == 15
    assert metrics.no_bid == 80
    assert metrics.yes_ask == 20
    assert metrics.no_ask == 85
    assert metrics.yes_mid == 17.5
    assert metrics.no_mid == 82.5
    assert metrics.spread == 5
    assert metrics.depth_summary == 300

def test_calculate_orderbook_metrics_empty():
    raw_orderbook = {
        "orderbook_fp": {
            "yes_dollars": [],
            "no_dollars": []
        }
    }
    
    metrics = calculate_orderbook_metrics(raw_orderbook)
    
    assert metrics.yes_bid == 0
    assert metrics.no_bid == 0
    assert metrics.yes_ask == 100
    assert metrics.no_ask == 100
    assert metrics.yes_mid == 50.0
    assert metrics.no_mid == 50.0
    assert metrics.spread == 100
    assert metrics.depth_summary == 0

def test_read_only_constraint():
    """
    Ensures that the client doesn't have any order placement methods.
    """
    from kalshi.client import KalshiPublicClient
    client = KalshiPublicClient()
    
    forbidden = ["create_order", "cancel_order", "place_order", "buy", "sell"]
    for f in forbidden:
        assert not hasattr(client, f), f"Client should not have method {f}"

if __name__ == '__main__':
    test_map_kalshi_subtitle_to_bin()
    test_map_markets_to_bins()
    test_map_markets_to_bins_uncertain()
    test_calculate_orderbook_metrics()
    test_calculate_orderbook_metrics_empty()
    test_read_only_constraint()
    print("All Kalshi integration tests passed.")


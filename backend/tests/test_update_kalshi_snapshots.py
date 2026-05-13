import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json
import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

mock_client_class = MagicMock()

mocks = {
    'requests': MagicMock(),
    'pydantic': MagicMock(),
    'beautifulsoup4': MagicMock(),
    'python-dateutil': MagicMock(),
    'dateutil': MagicMock(),
    'dateutil.parser': MagicMock(),
    'market_data.kalshi_public_client': MagicMock(KalshiPublicClient=mock_client_class)
}

with patch.dict('sys.modules', mocks):
    # Import main but we will patch things before calling it
    from market_data.update_kalshi_snapshots import main

class TestUpdateKalshiSnapshots(unittest.TestCase):

    @patch('market_data.update_kalshi_snapshots.Path')
    @patch('builtins.open', new_callable=mock_open)
    def test_relaxed_filtering(self, mock_file, mock_path):
        """Test that relaxed Miami high-temperature filtering does not require literal KMIA."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.reset_mock()
        mock_client_class.return_value = mock_client
        
        # Mock config loading
        mock_path.return_value.exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps({
            "search_terms": ["Miami"],
            "preferred_terms": ["Miami", "KMIA", "temperature", "high"],
            "known_series_tickers": [],
            "known_market_tickers": []
        })
        
        # Mock discovery returning a market with "Miami temperature high" but no "KMIA"
        mock_client.discover_temperature_markets.return_value = {
            "candidate_markets": [
                {
                    "ticker": "MOCK-1",
                    "title": "Will the high temp in Miami be high?",
                    "subtitle": "Temperature market",
                    "series_ticker": "KX"
                }
            ],
            "endpoint_attempts": [],
            "total_raw_markets_seen": 1
        }
        mock_client.get_orderbook.return_value = {"yes_bids": [], "no_bids": []}
        mock_client.save_market_snapshot.return_value = "mock_path"
        
        # Run main
        try:
            main()
        except SystemExit:
            pass # Expect success
            
        # Verify that the market was selected despite missing "KMIA"
        args, kwargs = mock_client.save_market_snapshot.call_args
        snapshot = args[0]
        self.assertEqual(len(snapshot["selected_temperature_markets"]), 1)
        self.assertEqual(snapshot["selected_temperature_markets"][0]["ticker"], "MOCK-1")

    @patch('market_data.update_kalshi_snapshots.Path')
    def test_preservation_on_empty_fetch(self, mock_path):
        """Test that failed/empty fetch preserves previous valid latest snapshot."""
        mock_client = MagicMock()
        mock_client_class.reset_mock()
        mock_client_class.return_value = mock_client
        
        # Mock config
        mock_path_config = MagicMock()
        mock_path_config.exists.return_value = False # fallback to default config
        
        # Mock latest snapshot path exists
        mock_path_latest = MagicMock()
        mock_path_latest.exists.return_value = True
        
        # Mock open for reading previous snapshot
        def path_side_effect(path_str):
            if "kalshi_market_discovery.json" in str(path_str):
                return mock_path_config
            elif "latest_kalshi_market_snapshot.json" in str(path_str):
                return mock_path_latest
            return MagicMock()
            
        mock_path.side_effect = path_side_effect
        
        # Mock discovery returning empty
        mock_client.discover_temperature_markets.return_value = {
            "candidate_markets": [],
            "endpoint_attempts": [],
            "total_raw_markets_seen": 0
        }
        
        # Mock open to return a valid snapshot when reading latest
        m_open = mock_open(read_data=json.dumps({
            "selected_temperature_markets": [{"ticker": "KXHIGHMIA-99DEC31-T80"}]
        }))
        
        with patch('builtins.open', m_open):
            try:
                main()
            except SystemExit:
                pass
                
        # Verify that it attempted to fetch orderbooks for the preserved ticker
        mock_client.get_orderbook.assert_called_with("KXHIGHMIA-99DEC31-T80")
        
        # Verify that it did NOT overwrite latest (did not call save_market_snapshot)
        mock_client.save_market_snapshot.assert_not_called()

    @patch('market_data.update_kalshi_snapshots.Path')
    @patch('builtins.open', new_callable=mock_open)
    def test_empty_fetch_no_previous(self, mock_file, mock_path):
        """Test that empty fetch with no previous valid snapshot writes status: EMPTY."""
        mock_client = MagicMock()
        mock_client_class.reset_mock()
        mock_client_class.return_value = mock_client
        
        # Mock config loading
        mock_file.return_value.read.return_value = "{}"
        
        # Mock paths
        mock_path_inst = MagicMock()
        mock_path_inst.exists.return_value = False # neither config nor latest exists
        mock_path.return_value = mock_path_inst
        
        # Mock discovery returning empty
        mock_client.discover_temperature_markets.return_value = {
            "candidate_markets": [],
            "endpoint_attempts": [],
            "total_raw_markets_seen": 0
        }
        
        mock_client.save_market_snapshot.return_value = "mock_path"
        
        try:
            main()
        except SystemExit:
            pass
            
        # Verify that save_market_snapshot was called with status "EMPTY"
        args, kwargs = mock_client.save_market_snapshot.call_args
        snapshot = args[0]
        self.assertEqual(snapshot["status"], "EMPTY")
        self.assertEqual(len(snapshot["selected_temperature_markets"]), 0)

    @patch('market_data.update_kalshi_snapshots.Path')
    def test_orderbook_fallback(self, mock_path):
        """Test that empty orderbook + market snapshot prices produces fallback fields."""
        mock_client = MagicMock()
        mock_client_class.reset_mock()
        mock_client_class.return_value = mock_client
        # Mock paths
        mock_path_inst = MagicMock()
        mock_path_inst.exists.return_value = False
        mock_path.return_value = mock_path_inst
        
        # Mock discovery returning a market with prices
        mock_client.discover_temperature_markets.return_value = {
            "candidate_markets": [
                {
                    "ticker": "MOCK-FALLBACK",
                    "title": "Miami High Temperature",
                    "subtitle": "Will it be high?",
                    "yes_bid_dollars": "0.08",
                    "yes_ask_dollars": "0.10",
                    "no_bid_dollars": "0.90",
                    "no_ask_dollars": "0.92",
                    "yes_bid_size_fp": "100",
                    "yes_ask_size_fp": "200",
                    "no_bid_size_fp": "300",
                    "no_ask_size_fp": "400",
                    "last_price_dollars": "0.09"
                }
            ],
            "endpoint_attempts": [],
            "total_raw_markets_seen": 1
        }
        # Mock get_orderbook to fail (forcing empty orderbook)
        mock_client.get_orderbook.side_effect = Exception("API Error")
        
        # Mock save_market_snapshot
        mock_client.save_market_snapshot.return_value = "mock_path"
        
        m_open = mock_open()
        m_open.return_value.read.return_value = "{}"
        m_write = MagicMock()
        m_open.return_value.write = m_write
        
        with patch('builtins.open', m_open):
            try:
                main()
            except SystemExit:
                pass
                
        # Now check what was written!
        calls = m_write.call_args_list
        found_fallback = False
        for call in calls:
            content = call[0][0]
            if "top_yes_bid_dollars" in content:
                found_fallback = True
                data = json.loads(content)
                ob = data["orderbooks"]["MOCK-FALLBACK"]
                self.assertEqual(ob["top_yes_bid_dollars"], 0.08)
                self.assertEqual(ob["top_yes_ask_dollars"], 0.10)
                self.assertEqual(ob["top_no_bid_dollars"], 0.90)
                self.assertEqual(ob["top_no_ask_dollars"], 0.92)
                self.assertEqual(ob["last_price_dollars"], 0.09)
                self.assertEqual(ob["yes_bid_size"], 100)
                self.assertEqual(ob["yes_ask_size"], 200)
                self.assertEqual(ob["no_bid_size"], 300)
                self.assertEqual(ob["no_ask_size"], 400)
                self.assertEqual(ob["top_of_book_source"], "market_snapshot_fallback")
                
        self.assertTrue(found_fallback)

if __name__ == '__main__':
    unittest.main()

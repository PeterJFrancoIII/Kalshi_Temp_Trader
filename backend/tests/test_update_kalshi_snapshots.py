import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json
import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import main but we will patch things before calling it
from market_data.update_kalshi_snapshots import main

class TestUpdateKalshiSnapshots(unittest.TestCase):

    @patch('market_data.update_kalshi_snapshots.KalshiPublicClient')
    @patch('market_data.update_kalshi_snapshots.Path')
    @patch('builtins.open', new_callable=mock_open)
    def test_relaxed_filtering(self, mock_file, mock_path, mock_client_class):
        """Test that relaxed Miami high-temperature filtering does not require literal KMIA."""
        # Setup mocks
        mock_client = MagicMock()
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
        
        # Mock save_market_snapshot to avoid writing files
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

    @patch('market_data.update_kalshi_snapshots.KalshiPublicClient')
    @patch('market_data.update_kalshi_snapshots.Path')
    def test_preservation_on_empty_fetch(self, mock_path, mock_client_class):
        """Test that failed/empty fetch preserves previous valid latest snapshot."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock config
        mock_path_config = MagicMock()
        mock_path_config.exists.return_value = False # fallback to default config
        
        # Mock latest snapshot path exists
        mock_path_latest = MagicMock()
        mock_path_latest.exists.return_value = True
        
        # Mock open for reading previous snapshot
        # This is tricky because we need to return different things for different paths
        # We'll mock Path objects to return specific mocks
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
        mock_client.get_market.return_value = None
        mock_client.get_markets_for_series.return_value = []
        
        # Mock open to return a valid snapshot when reading latest
        m_open = mock_open(read_data=json.dumps({
            "selected_temperature_markets": [{"ticker": "PRESERVED-1"}]
        }))
        
        with patch('builtins.open', m_open):
            try:
                main()
            except SystemExit:
                pass
                
        # Verify that it attempted to fetch orderbooks for the preserved ticker
        mock_client.get_orderbook.assert_called_with("PRESERVED-1")
        
        # Verify that it did NOT overwrite latest (did not call save_market_snapshot)
        mock_client.save_market_snapshot.assert_not_called()

    @patch('market_data.update_kalshi_snapshots.KalshiPublicClient')
    @patch('market_data.update_kalshi_snapshots.Path')
    @patch('builtins.open', new_callable=mock_open)
    def test_empty_fetch_no_previous(self, mock_file, mock_path, mock_client_class):
        """Test that empty fetch with no previous valid snapshot writes status: EMPTY."""
        mock_client = MagicMock()
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
        mock_client.get_market.return_value = None
        mock_client.get_markets_for_series.return_value = []
        
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

if __name__ == '__main__':
    unittest.main()

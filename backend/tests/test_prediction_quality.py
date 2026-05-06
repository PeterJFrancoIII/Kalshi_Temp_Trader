import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import os
import sys

# Add src to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "backend" / "src"))

from paper_trading.prediction_quality import generate_report

class TestPredictionQuality(unittest.TestCase):

    @patch("paper_trading.prediction_quality.load_json")
    @patch("paper_trading.prediction_quality.get_latest_file")
    @patch("paper_trading.prediction_quality.Path.exists")
    @patch("paper_trading.prediction_quality.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_quality_good(self, mock_open, mock_mkdir, mock_exists, mock_latest, mock_load):
        # Setup: GOOD scenario
        mock_exists.return_value = True
        mock_latest.side_effect = [Path("status.json"), Path("forecast.md")]
        
        def load_side_effect(path):
            if "latest_paper_signal.json" in str(path):
                return {"best_signal": {"market_ticker": "TEST-1"}, "safety": {"no_real_trading": True}}
            if "latest_kalshi_market_snapshot.json" in str(path):
                return {"markets_found": 1}
            if "manual_data_corrections.json" in str(path):
                return {"dates": {}}
            if "status.json" in str(path):
                return {"forecast": {"best_single_number": 85, "top_probability_bin": "85-87"}}
            return {}
            
        mock_load.side_effect = load_side_effect
        
        report = generate_report()
        
        self.assertEqual(report["prediction_quality"], "GOOD")
        self.assertTrue(report["safety"]["no_real_trading"])
        self.assertEqual(report["kalshi_markets_found"], 1)
        self.assertEqual(report["best_paper_signal"], "TEST-1")

    @patch("paper_trading.prediction_quality.load_json")
    @patch("paper_trading.prediction_quality.get_latest_file")
    @patch("paper_trading.prediction_quality.Path.exists")
    @patch("paper_trading.prediction_quality.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_quality_watch_missing_markets(self, mock_open, mock_mkdir, mock_exists, mock_latest, mock_load):
        # Setup: WATCH scenario (Kalshi markets missing)
        mock_exists.return_value = True
        mock_latest.side_effect = [Path("status.json"), Path("forecast.md")]
        
        def load_side_effect(path):
            if "latest_kalshi_market_snapshot.json" in str(path):
                return {"markets_found": 0}
            if "manual_data_corrections.json" in str(path):
                return {"dates": {}}
            if "status.json" in str(path):
                return {"forecast": {"best_single_number": 85}}
            return {}
            
        mock_load.side_effect = load_side_effect
        
        report = generate_report()
        
        self.assertEqual(report["prediction_quality"], "WATCH")
        self.assertIn("No Kalshi markets found", report["main_risk"])

    @patch("paper_trading.prediction_quality.load_json")
    @patch("paper_trading.prediction_quality.get_latest_file")
    @patch("paper_trading.prediction_quality.Path.exists")
    @patch("paper_trading.prediction_quality.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_quality_review_missing_files(self, mock_open, mock_mkdir, mock_exists, mock_latest, mock_load):
        # Setup: REVIEW scenario (Missing forecast/status)
        mock_exists.return_value = True
        mock_latest.return_value = None # No files found
        mock_load.return_value = {} # Ensure it returns dict, not MagicMock
        
        report = generate_report()
        
        self.assertEqual(report["prediction_quality"], "REVIEW")
        self.assertIn("Missing required files", report["main_risk"])

    @patch("paper_trading.prediction_quality.load_json")
    @patch("paper_trading.prediction_quality.get_latest_file")
    @patch("paper_trading.prediction_quality.Path.exists")
    @patch("paper_trading.prediction_quality.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_quality_review_manual_correction(self, mock_open, mock_mkdir, mock_exists, mock_latest, mock_load):
        # Setup: REVIEW scenario (Manual correction for today)
        mock_exists.return_value = True
        mock_latest.side_effect = [Path("status.json"), Path("forecast.md")]
        
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        def load_side_effect(path):
            if "manual_data_corrections.json" in str(path):
                return {"dates": {today: {"notes": ["Today is weird"]}}}
            return {}
            
        mock_load.side_effect = load_side_effect
        
        report = generate_report()
        
        self.assertEqual(report["prediction_quality"], "REVIEW")
        self.assertTrue(report["manual_corrections_active"])
        self.assertIn("Manual correction active", report["main_risk"])

    @patch("paper_trading.prediction_quality.load_json")
    @patch("paper_trading.prediction_quality.get_latest_file")
    @patch("paper_trading.prediction_quality.Path.exists")
    @patch("paper_trading.prediction_quality.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_special_date_warnings(self, mock_open, mock_mkdir, mock_exists, mock_latest, mock_load):
        # Setup: Check May 5 and May 7 special logic
        mock_exists.return_value = True
        mock_latest.side_effect = [Path("status.json"), Path("forecast.md")]
        
        def load_side_effect(path):
            if "manual_data_corrections.json" in str(path):
                return {
                    "dates": {
                        "2026-05-05": {"exclude_from_learning": True},
                        "2026-05-07": {"market_open_time_et": "11:00"}
                    }
                }
            return {}
            
        mock_load.side_effect = load_side_effect
        
        report = generate_report()
        
        self.assertIn("May 5 is excluded from learning.", report["data_quality_warnings"])
        self.assertIn("May 7 market open time exists: 11:00 ET", report["notes"])

    @patch("paper_trading.prediction_quality.load_json")
    def test_missing_files_no_crash(self, mock_load):
        # If load_json returns None (e.g. file missing or empty), it should not crash
        mock_load.return_value = None
        
        # We need to mock other things to avoid actual file IO
        with patch("paper_trading.prediction_quality.get_latest_file", return_value=None):
            with patch("paper_trading.prediction_quality.Path.exists", return_value=False):
                with patch("paper_trading.prediction_quality.Path.mkdir"):
                    with patch("builtins.open", new_callable=MagicMock):
                        report = generate_report()
                        self.assertIsNotNone(report)
                        self.assertEqual(report["prediction_quality"], "REVIEW")

if __name__ == "__main__":
    unittest.main()

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import unittest
from paper_trading.signal_generator import generate_paper_signal, parse_forecast_bins_from_md

# NO REAL TRADING EXECUTION

class TestPaperSignalGenerator(unittest.TestCase):

    def test_parse_forecast_bins(self):
        temp_md = Path("test_forecast.md")
        temp_md.write_text("""
## Probability Bins
| Bin | Probability |
| :--- | :--- |
| <=78 | 5.0% |
| 79-80 | 10.0% |
| 81-82 | 85.0% |
""")
        try:
            bins = parse_forecast_bins_from_md(temp_md)
            self.assertEqual(bins["<=78"], 0.05)
            self.assertEqual(bins["79-80"], 0.10)
            self.assertEqual(bins["81-82"], 0.85)
        finally:
            if temp_md.exists():
                temp_md.unlink()

    def test_generate_signal_logic(self):
        """Verify that signals are generated when forecast and markets align."""
        temp_dir = Path(__file__).resolve().parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # 1. Create Mock Forecast
        md_path = temp_dir / "kmia_forecast_mock_rules_v2_climatology.md"
        md_content = """
# Forecast
## Probability Bins
| >=87 | 40.0% |
| 85-86 | 30.0% |
"""
        md_path.write_text(md_content)
        
        # 2. Create Mock Snapshot
        snapshot_path = temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY07-B86.5",
                    "title": "Will it be hot?",
                    "subtitle": "86.5 degrees or above",
                    "yes_ask_dollars": "0.1000",
                    "yes_bid_dollars": "0.0800",
                    "status": "open",
                    "close_time": "2026-05-07T00:00:00Z",
                    "strike_type": "greater",
                    "floor_strike": 86.5
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
            
        import paper_trading.signal_generator as sg
        original_reports = sg.REPORTS_DIR
        original_snapshot = sg.SNAPSHOT_FILE
        sg.REPORTS_DIR = temp_dir
        sg.SNAPSHOT_FILE = snapshot_path
        
        try:
            report_path = sg.generate_paper_signal()
            with open(report_path, "r") as f:
                report = json.load(f)
                
            self.assertTrue(len(report["signals"]) > 0, f"No signals generated. Report: {report}")
            sig = report["signals"][0]
            self.assertEqual(sig["market_ticker"], "KXHIGHMIA-26MAY07-B86.5")
            # 86.5+ matches >=87 bin exactly
            self.assertAlmostEqual(sig["model_probability"], 0.4)
            self.assertAlmostEqual(sig["market_probability"], 0.10)
            self.assertTrue(sig["edge"] >= 0.3)
            self.assertEqual(sig["paper_action"], "PAPER BUY CANDIDATE")
        finally:
            sg.REPORTS_DIR = original_reports
            sg.SNAPSHOT_FILE = original_snapshot

    def test_generate_signal_safety_and_skipping(self):
        """Verify safety field and price-based skipping."""
        temp_dir = Path(__file__).resolve().parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # 1. Create Mock Forecast
        md_path = temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.md"
        md_path.write_text("## Probability Bins\n| 85-86 | 50.0% |\n| >=87 | 10.0% |")
        
        # 2. Create Mock Snapshot
        snapshot_path = temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY07-B86.5",
                    "title": "Above 86.5",
                    "subtitle": "86.5 or above",
                    "yes_ask_dollars": "0.10",
                    "status": "open",
                    "strike_type": "greater",
                    "floor_strike": 86.5
                },
                {
                    "ticker": "KXHIGHMIA-26MAY07-B85.5",
                    "title": "Bad",
                    "subtitle": "85.5 or above",
                    "yes_ask": None,
                    "last_price": None,
                    "status": "open",
                    "strike_type": "greater",
                    "floor_strike": 85.5
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
            
        import paper_trading.signal_generator as sg
        original_reports = sg.REPORTS_DIR
        original_snapshot = sg.SNAPSHOT_FILE
        sg.REPORTS_DIR = temp_dir
        sg.SNAPSHOT_FILE = snapshot_path
        
        try:
            report_path = sg.generate_paper_signal()
            with open(report_path, "r") as f:
                report = json.load(f)
                
            self.assertEqual(len(report["signals"]), 1)
            self.assertEqual(report["signals"][0]["market_ticker"], "KXHIGHMIA-26MAY07-B86.5")
            # 86.5+ matches >=87 (0.10)
            self.assertAlmostEqual(report["signals"][0]["model_probability"], 0.10)
            self.assertTrue(any("KXHIGHMIA-26MAY07-B85.5" in w for w in report["warnings"]))
            self.assertTrue(report["safety"]["no_real_trading"])
            self.assertIn("NO REAL TRADING", report["safety"]["disclaimer"])
        finally:
            sg.REPORTS_DIR = original_reports
            sg.SNAPSHOT_FILE = original_snapshot

    def test_generate_signal_empty_markets(self):
        """Verify that empty markets produce NO_SIGNAL status."""
        temp_dir = Path(__file__).resolve().parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # 1. Create Mock Forecast
        md_path = temp_dir / "kmia_forecast_mock_rules_v2_climatology.md"
        md_path.write_text("## Probability Bins\n| 85-86 | 50.0% |")
        
        # 2. Create Mock Snapshot (Empty)
        snapshot_path = temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {"selected_temperature_markets": []}
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
            
        import paper_trading.signal_generator as sg
        original_reports = sg.REPORTS_DIR
        original_snapshot = sg.SNAPSHOT_FILE
        sg.REPORTS_DIR = temp_dir
        sg.SNAPSHOT_FILE = snapshot_path
        
        try:
            report_path = sg.generate_paper_signal()
            with open(report_path, "r") as f:
                report = json.load(f)
                
            self.assertEqual(report["status"], "NO_SIGNAL")
            self.assertIsNone(report["best_signal"])
            self.assertTrue(any("No active KXHIGHMIA markets" in w for w in report["warnings"]))
        finally:
            sg.REPORTS_DIR = original_reports
            sg.SNAPSHOT_FILE = original_snapshot

    def test_generate_signal_stale_ticker(self):
        """Verify that stale tickers are marked as NO SIGNAL."""
        temp_dir = Path(__file__).resolve().parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # 1. Create Mock Forecast (Targeting 2026-05-08)
        md_path = temp_dir / "kmia_forecast_2026-05-08_rules_v2_climatology_120000.md"
        md_path.write_text("## Probability Bins\n| 85-86 | 50.0% |")
        
        # 2. Create Mock Snapshot with stale ticker (2026-05-07)
        snapshot_path = temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY07-B86.5",
                    "title": "Above 86.5",
                    "subtitle": "86.5 or above",
                    "yes_ask_dollars": "0.10",
                    "status": "open",
                    "strike_type": "greater",
                    "floor_strike": 86.5
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
            
        import paper_trading.signal_generator as sg
        original_reports = sg.REPORTS_DIR
        original_snapshot = sg.SNAPSHOT_FILE
        sg.REPORTS_DIR = temp_dir
        sg.SNAPSHOT_FILE = snapshot_path
        
        try:
            report_path = sg.generate_paper_signal()
            with open(report_path, "r") as f:
                report = json.load(f)
                
            self.assertEqual(len(report["signals"]), 1)
            self.assertEqual(report["signals"][0]["paper_action"], "NO SIGNAL")
            self.assertTrue(report["signals"][0]["stale"])
            self.assertIsNone(report["best_signal"])
        finally:
            sg.REPORTS_DIR = original_reports
            sg.SNAPSHOT_FILE = original_snapshot

if __name__ == "__main__":
    unittest.main()

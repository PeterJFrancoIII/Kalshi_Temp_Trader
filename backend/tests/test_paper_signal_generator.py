import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import unittest
import sys
import shutil
from datetime import datetime, timezone, timedelta

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from paper_trading.signal_generator import generate_paper_signal, parse_forecast_bins_from_md

class MockBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def dict(self):
        return self.__dict__
    def model_dump(self):
        return self.__dict__
    def get(self, key, default=None):
        return getattr(self, key, default)

pydantic_mock = MagicMock()
pydantic_mock.BaseModel = MockBaseModel
pydantic_mock.Field = MagicMock()
pydantic_mock.field_validator = MagicMock()
pydantic_mock.model_validator = MagicMock()

mocks = {
    'requests': MagicMock(),
    'pydantic': pydantic_mock,
    'beautifulsoup4': MagicMock(),
    'sqlalchemy': MagicMock()
}

# Patch sys.modules for this class to avoid contamination during execution
@patch.dict('sys.modules', mocks)
class TestPaperSignalGenerator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(__file__).resolve().parent / "temp_test_dir"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Save original module variables
        import paper_trading.signal_generator as sg
        self.orig_nws_snapshot_file = sg.NWS_SNAPSHOT_FILE

    def tearDown(self):
        # Restore original module variables
        import paper_trading.signal_generator as sg
        sg.NWS_SNAPSHOT_FILE = self.orig_nws_snapshot_file
        
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_parse_forecast_bins(self):
        temp_md = self.temp_dir / "test_forecast.md"
        temp_md.write_text("""
## Probability Bins
| Bin | Probability |
| :--- | :--- |
| <=78 | 5.0% |
| 79-80 | 10.0% |
| 81-82 | 85.0% |
""")
        bins = parse_forecast_bins_from_md(temp_md)
        self.assertEqual(bins["<=78"], 0.05)
        self.assertEqual(bins["79-80"], 0.10)
        self.assertEqual(bins["81-82"], 0.85)

    def test_generate_signal_logic(self):
        """Verify that signals are generated when forecast and markets align."""
        import paper_trading.signal_generator as sg
        
        # 1. Create Mock Forecast
        md_path = self.temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.md"
        md_content = "## Probability Bins\n| >=87 | 40.0% |\n| 85-86 | 30.0% |\n| <=84 | 30.0% |"
        md_path.write_text(md_content)
        
        # 2. Create Mock Snapshot
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-07T12:00:00Z",
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY07-B86.5",
                    "title": "Will it be hot?",
                    "subtitle": "86.5 degrees or above",
                    "yes_ask_dollars": "0.10",
                    "status": "open",
                    "close_time": "2026-05-07T00:00:00Z",
                    "strike_type": "greater",
                    "floor_strike": 86.5
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)

        # 3. Create fresh NWS snapshot
        nws_path = self.temp_dir / "latest_nws_kmia_snapshot.json"
        nws_data = {
            "latest_observation_time": "2026-05-07T11:00:00Z"
        }
        with open(nws_path, "w") as f:
            json.dump(nws_data, f)
        sg.NWS_SNAPSHOT_FILE = nws_path

        # Mock prediction date to May 7
        test_now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)

        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=md_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)

        self.assertEqual(len(report["signals"]), 1)
        self.assertEqual(report["signals"][0]["market_ticker"], "KXHIGHMIA-26MAY07-B86.5")
        self.assertIn("model_probability", report["signals"][0])

    def test_generate_signal_safety_and_skipping(self):
        """Verify safety field and price-based skipping."""
        import paper_trading.signal_generator as sg
        
        # 1. Create Mock Forecast
        md_path = self.temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.md"
        md_path.write_text("## Probability Bins\n| 85-86 | 50.0% |\n| >=87 | 10.0% |")
        
        # 2. Create Mock Snapshot
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-07T12:00:00Z",
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

        # 3. Create NWS snapshot
        nws_path = self.temp_dir / "latest_nws_kmia_snapshot.json"
        with open(nws_path, "w") as f:
            json.dump({"latest_observation_time": "2026-05-07T12:00:00Z"}, f)
        sg.NWS_SNAPSHOT_FILE = nws_path
        
        # Mock prediction date to May 7
        test_now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)

        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=md_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)
            
        self.assertEqual(len(report["signals"]), 1)
        self.assertEqual(report["signals"][0]["market_ticker"], "KXHIGHMIA-26MAY07-B86.5")

    def test_generate_signal_empty_markets(self):
        """Verify that empty markets produce NO_SIGNAL status."""
        md_path = self.temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.md"
        md_path.write_text("## Probability Bins\n| 85-86 | 50.0% |")
        
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-07T12:00:00Z",
            "selected_temperature_markets": []
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
            
        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=md_path,
            snapshot_path=snapshot_path,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)
            
        self.assertEqual(report["status"], "NO_SIGNAL")

    def test_generate_signal_stale_ticker(self):
        """Verify that stale tickers are marked as NO SIGNAL."""
        md_path = self.temp_dir / "kmia_forecast_2026-05-08_rules_v2_climatology_120000.md"
        md_path.write_text("## Probability Bins\n| 85-86 | 50.0% |")
        
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-08T12:00:00Z",
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
            
        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=md_path,
            snapshot_path=snapshot_path,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)
            
        self.assertEqual(len(report["signals"]), 0)
        self.assertEqual(report["status"], "NO_SIGNAL")

    def test_generate_signal_missing_prob_warning(self):
        """Verify that current ticker with missing probability still emits mapping warning."""
        import paper_trading.signal_generator as sg
        md_path = self.temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.md"
        md_path.write_text("## Probability Bins\n| 81-82 | 50.0% |")
        
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-07T12:00:00Z",
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

        nws_path = self.temp_dir / "latest_nws_kmia_snapshot.json"
        with open(nws_path, "w") as f:
            json.dump({"latest_observation_time": "2026-05-07T12:00:00Z"}, f)
        sg.NWS_SNAPSHOT_FILE = nws_path
        
        # Mock prediction date to May 7
        test_now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)

        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=md_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)
            
        self.assertTrue(any("Probability for bin" in w for w in report["warnings"]))

    def test_generate_signal_matching_date(self):
        """Verify that matching forecast date accepts current market."""
        import paper_trading.signal_generator as sg
        md_path = self.temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.md"
        md_path.write_text("## Probability Bins\n| >=87 | 50.0% |")
        
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-07T12:00:00Z",
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

        nws_path = self.temp_dir / "latest_nws_kmia_snapshot.json"
        with open(nws_path, "w") as f:
            json.dump({"latest_observation_time": "2026-05-07T12:00:00Z"}, f)
        sg.NWS_SNAPSHOT_FILE = nws_path
        
        # Mock prediction date to May 7
        test_now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)

        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=md_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)
            
        self.assertEqual(len(report["signals"]), 1)
        self.assertEqual(report["status"], "OK")

    def test_dynamic_probabilities_full_coverage(self):
        """Verify that dynamic_contract_probabilities contains all contracts, including those without price."""
        import paper_trading.signal_generator as sg
        md_path = self.temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.md"
        md_path.write_text("## Probability Bins\n| >=87 | 50.0% |\n| >=85 | 10.0% |")
    
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-07T12:00:00Z",
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY07-B86.5",
                    "title": "Above 86.5",
                    "subtitle": "86.5 or above",
                    "yes_ask_dollars": "0.10",
                    "status": "open",
                    "strike_type": "greater",
                    "floor_strike": 86.5,
                    "contract_bin": {"label": ">=87"}
                },
                {
                    "ticker": "KXHIGHMIA-26MAY07-B84.5",
                    "title": "Above 84.5",
                    "subtitle": "84.5 or above",
                    "yes_ask_dollars": "0.00", # No price!
                    "status": "open",
                    "strike_type": "greater",
                    "floor_strike": 84.5,
                    "contract_bin": {"label": "<85"}
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
    
        nws_path = self.temp_dir / "latest_nws_kmia_snapshot.json"
        with open(nws_path, "w") as f:
            json.dump({"latest_observation_time": "2026-05-07T12:00:00Z"}, f)
        sg.NWS_SNAPSHOT_FILE = nws_path
    
        # Mock prediction date to May 7
        test_now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    
        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=md_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)
    
        # The market with no price should be skipped for signal generation
        self.assertEqual(len(report["signals"]), 1)
        
        # But BOTH should be in dynamic_contract_probabilities!
        self.assertIn(">=87", report["dynamic_contract_probabilities"])
        self.assertIn(">=85", report["dynamic_contract_probabilities"])
        self.assertEqual(report["dynamic_contract_probabilities"][">=87"], 0.5)
        self.assertEqual(report["dynamic_contract_probabilities"][">=85"], 0.1)

if __name__ == "__main__":
    unittest.main()

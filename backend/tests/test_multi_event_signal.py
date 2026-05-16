import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import unittest
from datetime import datetime, timezone
import shutil

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

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
    'pydantic': pydantic_mock,
    'beautifulsoup4': MagicMock(),
}

@patch.dict('sys.modules', mocks)
class TestMultiEventSignal(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(__file__).resolve().parent / "temp_multi_event_test"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_multi_event_separation(self):
        """Verify that May 15 and May 16 events are processed with separate forecasts."""
        reports_dir = self.temp_dir / "reports"
        reports_dir.mkdir()
        
        # Forecast for May 15
        f15_path = reports_dir / "kmia_forecast_2026-05-15_rules_v2_climatology_000000.json"
        with open(f15_path, "w") as f:
            json.dump({
                "date": "2026-05-15",
                "generated_at_utc": "2026-05-15T00:00:00Z",
                "probability_bins": {">=93": 0.8}
            }, f)
            
        # Forecast for May 16
        f16_path = reports_dir / "kmia_forecast_2026-05-16_rules_v2_climatology_000000.json"
        with open(f16_path, "w") as f:
            json.dump({
                "date": "2026-05-16",
                "generated_at_utc": "2026-05-16T00:00:00Z",
                "probability_bins": {">=93": 0.2}
            }, f)
            
        # Mock snapshot with both dates
        snapshot_path = self.temp_dir / "snapshot.json"
        with open(snapshot_path, "w") as f:
            json.dump({
                "generated_at_utc": "2026-05-15T12:00:00Z",
                "selected_temperature_markets": [
                    {
                        "ticker": "KXHIGHMIA-26MAY15-T92",
                        "title": ">92",
                        "yes_ask_dollars": "0.50",
                        "event_ticker": "KXHIGHMIA-26MAY15",
                        "status": "open"
                    },
                    {
                        "ticker": "KXHIGHMIA-26MAY16-T92",
                        "title": ">92",
                        "yes_ask_dollars": "0.50",
                        "event_ticker": "KXHIGHMIA-26MAY16",
                        "status": "open"
                    }
                ]
            }, f)
            
        # Mocking
        with patch("paper_trading.signal_generator.REPORTS_DIR", reports_dir), \
             patch("paper_trading.signal_generator.SNAPSHOT_FILE", snapshot_path), \
             patch("paper_trading.signal_generator.OUTPUT_DIR", self.temp_dir), \
             patch("paper_trading.signal_generator.LATEST_KALSHI_ORDERBOOKS", str(self.temp_dir / "nonexistent.json")), \
             patch("paper_trading.signal_generator.NWS_SNAPSHOT_FILE", self.temp_dir / "nws.json"):
            
            # Create a dummy NWS snapshot
            with open(self.temp_dir / "nws.json", "w") as f:
                json.dump({"latest_observation_time": "2026-05-15T11:00:00Z"}, f)

            from paper_trading.signal_generator import generate_paper_signal
            now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
            signal_path = generate_paper_signal(
                prediction_timestamp=now,
                latest_path_override=str(self.temp_dir / "latest_signal.json")
            )
            
            with open(signal_path, "r") as f:
                report = json.load(f)
                
            self.assertIn("events_by_date", report)
            self.assertIn("2026-05-15", report["events_by_date"])
            self.assertIn("2026-05-16", report["events_by_date"])
            
            # Verify p15
            p15 = report["events_by_date"]["2026-05-15"]["dynamic_contract_probabilities"]
            self.assertAlmostEqual(p15.get(">=93"), 0.8)
            
            # Verify p16
            p16 = report["events_by_date"]["2026-05-16"]["dynamic_contract_probabilities"]
            self.assertAlmostEqual(p16.get(">=93"), 0.2)
            
            # Verify flattened signals
            self.assertEqual(len(report["signals"]), 2)
            
            # Verify primary_event_date
            self.assertEqual(report["primary_event_date"], "2026-05-15")

    def test_missing_future_forecast(self):
        """Verify that May 16 correctly reports NO_SIGNAL if its forecast is missing while May 15 works."""
        reports_dir = self.temp_dir / "reports_missing"
        reports_dir.mkdir()
        
        # Forecast ONLY for May 15
        f15_path = reports_dir / "kmia_forecast_2026-05-15_rules_v2_climatology_000000.json"
        with open(f15_path, "w") as f:
            json.dump({
                "date": "2026-05-15",
                "generated_at_utc": "2026-05-15T00:00:00Z",
                "probability_bins": {">=93": 0.8}
            }, f)
            
        # Mock snapshot with both dates
        snapshot_path = self.temp_dir / "snapshot_missing.json"
        with open(snapshot_path, "w") as f:
            json.dump({
                "generated_at_utc": "2026-05-15T12:00:00Z",
                "selected_temperature_markets": [
                    {
                        "ticker": "KXHIGHMIA-26MAY15-T92",
                        "event_ticker": "KXHIGHMIA-26MAY15",
                        "status": "open"
                    },
                    {
                        "ticker": "KXHIGHMIA-26MAY16-T92",
                        "event_ticker": "KXHIGHMIA-26MAY16",
                        "status": "open"
                    }
                ]
            }, f)
            
        with patch("paper_trading.signal_generator.REPORTS_DIR", reports_dir), \
             patch("paper_trading.signal_generator.SNAPSHOT_FILE", snapshot_path), \
             patch("paper_trading.signal_generator.OUTPUT_DIR", self.temp_dir), \
             patch("paper_trading.signal_generator.LATEST_KALSHI_ORDERBOOKS", str(self.temp_dir / "nonexistent.json")), \
             patch("paper_trading.signal_generator.NWS_SNAPSHOT_FILE", self.temp_dir / "nws.json"):
            
            with open(self.temp_dir / "nws.json", "w") as f:
                json.dump({"latest_observation_time": "2026-05-15T11:00:00Z"}, f)

            from paper_trading.signal_generator import generate_paper_signal
            now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
            signal_path = generate_paper_signal(
                prediction_timestamp=now,
                latest_path_override=str(self.temp_dir / "latest_signal_missing.json")
            )
            
            with open(signal_path, "r") as f:
                report = json.load(f)
                
            self.assertEqual(report["events_by_date"]["2026-05-15"]["status"], "OK")
            self.assertEqual(report["events_by_date"]["2026-05-16"]["status"], "NO_SIGNAL")
            self.assertIn("No forecast artifact found for 2026-05-16", report["events_by_date"]["2026-05-16"]["warnings"][0])

if __name__ == "__main__":
    unittest.main()

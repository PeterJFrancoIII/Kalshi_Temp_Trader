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
        self.orig_orderbooks_file = sg.LATEST_KALSHI_ORDERBOOKS
        self.orig_snapshot_file = sg.LATEST_KALSHI_MARKET_SNAPSHOT

    def tearDown(self):
        # Restore original module variables
        import paper_trading.signal_generator as sg
        sg.NWS_SNAPSHOT_FILE = self.orig_nws_snapshot_file
        sg.LATEST_KALSHI_ORDERBOOKS = self.orig_orderbooks_file
        sg.LATEST_KALSHI_MARKET_SNAPSHOT = self.orig_snapshot_file
        
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_valid_nws_snapshot(self, path, date_str, obs_time_str="11:30:00+00:00", fetched_time_str="12:00:00+00:00"):
        nws_data = {
            "station": "KMIA",
            "fetched_at_utc": f"{date_str}T{fetched_time_str}",
            "latest_observation_time": f"{date_str}T{obs_time_str}",
            "current_temp_f": 85.0,
            "observed_max_so_far_f": 85.0,
            "forecast_high_f": 85.0,
            "recent_observations_table": [
                {
                    "timestamp_utc": f"{date_str}T{obs_time_str}",
                    "temperature_f": 85.0
                }
            ],
            "stale_data": False,
            "stale_fallback": False,
            "endpoint_status": "OK",
            "safety": {
                "no_real_trading": True
            }
        }
        with open(path, "w") as f:
            json.dump(nws_data, f)
        return nws_data

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
        self._create_valid_nws_snapshot(nws_path, "2026-05-07")
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
        self._create_valid_nws_snapshot(nws_path, "2026-05-07")
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
        self._create_valid_nws_snapshot(nws_path, "2026-05-07")
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
        self._create_valid_nws_snapshot(nws_path, "2026-05-07")
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
        self._create_valid_nws_snapshot(nws_path, "2026-05-07")
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

    def test_stale_when_forecast_older_than_ticker(self):
        """C1-B regression: forecast dated May 7, ticker for May 8 → stale.
        The signal generator must not apply an older forecast to newer contracts."""
        import paper_trading.signal_generator as sg

        # Forecast is for May 7
        forecast_path = self.temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.json"
        forecast_data = {
            "date": "2026-05-07",
            "probability_bins": {">=87": 0.50, "85-86": 0.30, "83-84": 0.20},
            "integer_distribution": {str(t): 0.02 for t in range(60, 110)},
            "forecast_high_f": 87,
            "generated_at_utc": "2026-05-07T12:00:00Z"
        }
        with open(forecast_path, "w") as f:
            json.dump(forecast_data, f)

        # But the active contract is for May 8
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-08T12:00:00Z",
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY08-B86.5",
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
        self._create_valid_nws_snapshot(nws_path, "2026-05-08")
        sg.NWS_SNAPSHOT_FILE = nws_path

        test_now = datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=forecast_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)

        # All signals must be stale → filtered out → NO_SIGNAL
        self.assertEqual(report["status"], "NO_SIGNAL",
            "Forecast from May 7 must NOT produce active signals for May 8 contracts")

    def test_evening_rollover_does_not_mark_same_day_stale(self):
        """Verify that UTC rollover doesn't mark ET same-day contracts as stale."""
        import paper_trading.signal_generator as sg
        from zoneinfo import ZoneInfo
        
        # Simulate: 
        # UTC: 2026-05-15 01:00:00 (May 15)
        # ET: 2026-05-14 21:00:00 (May 14)
        # Forecast is for May 14
        forecast_path = self.temp_dir / "kmia_forecast_2026-05-14_rules_v2_climatology_210000.json"
        forecast_data = {
            "date": "2026-05-14",
            "probability_bins": {">=87": 0.50, "85-86": 0.50},
            "integer_distribution": {str(t): 0.02 for t in range(60, 110)},
            "forecast_high_f": 87,
            "generated_at_utc": "2026-05-14T21:00:00Z"
        }
        with open(forecast_path, "w") as f:
            json.dump(forecast_data, f)
            
        # Snapshot has May 14 contract
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-15T01:00:00Z",
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY14-B86.5",
                    "yes_ask_dollars": "0.10",
                    "status": "active"
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
            
        nws_path = self.temp_dir / "latest_nws_kmia_snapshot.json"
        self._create_valid_nws_snapshot(nws_path, "2026-05-15", obs_time_str="00:30:00+00:00", fetched_time_str="01:00:00+00:00")
        sg.NWS_SNAPSHOT_FILE = nws_path
        
        # Prediction timestamp is May 15 01:00 UTC
        test_now = datetime(2026, 5, 15, 1, 0, 0, tzinfo=timezone.utc)
        
        # We need to patch datetime.now in signal_generator because it's called with ZoneInfo
        with patch('paper_trading.signal_generator.datetime') as mock_datetime:
            # Set up mock_now to return correct values based on tz
            def mock_now(tz=None):
                if tz and "Eastern" in str(tz):
                    return datetime(2026, 5, 14, 21, 0, 0, tzinfo=tz)
                # For default now(), return the UTC mock time
                return datetime(2026, 5, 15, 1, 0, 0, tzinfo=tz if tz else timezone.utc)
            
            mock_datetime.now.side_effect = mock_now
            # Mock other used datetime methods
            mock_datetime.fromisoformat = datetime.fromisoformat
            mock_datetime.strptime = datetime.strptime
            
            latest_path = self.temp_dir / "latest_paper_signal.json"
            report_path = generate_paper_signal(
                forecast_path=forecast_path,
                snapshot_path=snapshot_path,
                prediction_timestamp=test_now,
                output_dir=self.temp_dir,
                latest_path_override=str(latest_path)
            )
            
            with open(report_path, "r") as f:
                report = json.load(f)
                
            # VERIFY: status is OK and signals are generated (not stale)
            self.assertEqual(report["status"], "OK")
            self.assertTrue(len(report["signals"]) > 0)
            self.assertFalse(report["signals"][0].get("stale", True), "Signal should NOT be stale")
            self.assertEqual(report["signals"][0]["market_ticker"], "KXHIGHMIA-26MAY14-B86.5")

    def test_forecast_date_mismatch_warning(self):
        """C1-B regression: forecast date field doesn't match any active contract date.
        The signal generator must emit a warning about the mismatch."""
        import paper_trading.signal_generator as sg

        # Forecast JSON has date: 2026-05-07
        forecast_path = self.temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.json"
        forecast_data = {
            "date": "2026-05-07",
            "probability_bins": {">=87": 0.50, "85-86": 0.50},
            "integer_distribution": {str(t): 0.02 for t in range(60, 110)},
            "forecast_high_f": 87,
            "generated_at_utc": "2026-05-07T12:00:00Z"
        }
        with open(forecast_path, "w") as f:
            json.dump(forecast_data, f)

        # Active contract is for May 9 (two days ahead, clear mismatch)
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-09T12:00:00Z",
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY09-B86.5",
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
        self._create_valid_nws_snapshot(nws_path, "2026-05-09")
        sg.NWS_SNAPSHOT_FILE = nws_path

        test_now = datetime(2026, 5, 9, 12, 0, 0, tzinfo=timezone.utc)
        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=forecast_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)

        # Must have a date-mismatch warning
        self.assertTrue(
            any("does not match" in w or "mismatch" in w.lower() for w in report.get("warnings", [])),
            f"Expected date-mismatch warning in: {report.get('warnings')}"
        )

    def test_same_date_forecast_and_ticker_still_works(self):
        """Regression guard: matching dates must still produce signals normally."""
        import paper_trading.signal_generator as sg

        forecast_path = self.temp_dir / "kmia_forecast_2026-05-07_rules_v2_climatology_120000.json"
        forecast_data = {
            "date": "2026-05-07",
            "probability_bins": {">=87": 0.50, "85-86": 0.50},
            "integer_distribution": {str(t): 0.02 for t in range(60, 110)},
            "forecast_high_f": 87,
            "generated_at_utc": "2026-05-07T12:00:00Z"
        }
        with open(forecast_path, "w") as f:
            json.dump(forecast_data, f)

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
        self._create_valid_nws_snapshot(nws_path, "2026-05-07")
        sg.NWS_SNAPSHOT_FILE = nws_path

        test_now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
        latest_path = self.temp_dir / "latest_paper_signal.json"
        report_path = generate_paper_signal(
            forecast_path=forecast_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        with open(report_path, "r") as f:
            report = json.load(f)

        self.assertEqual(report["status"], "OK")
        self.assertEqual(len(report["signals"]), 1)
        # No date-mismatch warning
        self.assertFalse(
            any("does not match" in w for w in report.get("warnings", [])),
            f"Should NOT have date-mismatch warning: {report.get('warnings')}"
        )

    def test_orderbook_price_priority(self):
        """Verify that orderbook prices override stale snapshot prices."""
        import paper_trading.signal_generator as sg
        
        # 1. Mock Forecast (May 15)
        forecast_path = self.temp_dir / "kmia_forecast_2026-05-15_rules_v2_climatology_120000.json"
        forecast_data = {
            "date": "2026-05-15",
            "probability_bins": {">=93": 1.0},
            "integer_distribution": {"93": 1.0, "94": 0.0},
            "generated_at_utc": "2026-05-15T12:00:00Z"
        }
        with open(forecast_path, "w") as f:
            json.dump(forecast_data, f)
            
        # 2. Mock Snapshot with STALE prices (0.27) and PREVIOUS fields
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-15T00:37:00Z",
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY15-T92",
                    "yes_ask_dollars": 0.27,
                    "yes_bid_dollars": 0.26,
                    "last_price_dollars": 0.26,
                    "previous_yes_ask_dollars": 0.27, # Should be ignored
                    "status": "active",
                    "contract_bin": {"label": ">=93"}
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
        sg.LATEST_KALSHI_MARKET_SNAPSHOT = snapshot_path

        # 3. Mock Orderbook with FRESH prices (1.00)
        ob_path = self.temp_dir / "latest_kalshi_orderbooks.json"
        ob_data = {
            "orderbooks": {
                "KXHIGHMIA-26MAY15-T92": {
                    "top_yes_ask_dollars": 1.0,
                    "top_yes_bid_dollars": 0.99,
                    "last_price_dollars": 0.99
                }
            }
        }
        with open(ob_path, "w") as f:
            json.dump(ob_data, f)
        sg.LATEST_KALSHI_ORDERBOOKS = ob_path

        # 4. Mock NWS
        nws_path = self.temp_dir / "latest_nws_kmia_snapshot.json"
        self._create_valid_nws_snapshot(nws_path, "2026-05-15")
        sg.NWS_SNAPSHOT_FILE = nws_path
        
        test_now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        latest_path = self.temp_dir / "latest_paper_signal.json"
        
        report_path = generate_paper_signal(
            forecast_path=forecast_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        
        with open(report_path, "r") as f:
            report = json.load(f)
            
        self.assertEqual(len(report["signals"]), 1)
        sig = report["signals"][0]
        self.assertEqual(sig["market_ticker"], "KXHIGHMIA-26MAY15-T92")
        
        # ASSERT: Orderbook price used, NOT snapshot price
        self.assertEqual(sig["yes_ask"], 1.0)
        self.assertEqual(sig["yes_bid"], 0.99)
        self.assertEqual(sig["market_probability"], 1.0) # 1.0/1.0 = 1.0

    def test_orderbook_missing_fallback(self):
        """Verify that signal generator falls back to snapshot if orderbook is missing."""
        import paper_trading.signal_generator as sg
        
        forecast_path = self.temp_dir / "kmia_forecast_2026-05-15_rules_v2_climatology_120000.json"
        forecast_data = {"date": "2026-05-15", "probability_bins": {">=93": 0.5}, "generated_at_utc": "2026-05-15T12:00:00Z"}
        with open(forecast_path, "w") as f:
            json.dump(forecast_data, f)
            
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-15T12:00:00Z",
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY15-T92",
                    "yes_ask_dollars": 0.45,
                    "status": "active",
                    "contract_bin": {"label": ">=93"}
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
        sg.LATEST_KALSHI_MARKET_SNAPSHOT = snapshot_path

        # Orderbook is MISSING
        sg.LATEST_KALSHI_ORDERBOOKS = self.temp_dir / "non_existent_ob.json"

        nws_path = self.temp_dir / "latest_nws_kmia_snapshot.json"
        self._create_valid_nws_snapshot(nws_path, "2026-05-15")
        sg.NWS_SNAPSHOT_FILE = nws_path
        
        test_now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        latest_path = self.temp_dir / "latest_paper_signal.json"
        
        generate_paper_signal(
            forecast_path=forecast_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        
        with open(latest_path, "r") as f:
            report = json.load(f)
            
        # ASSERT: Used snapshot price 0.45
        self.assertEqual(report["signals"][0]["yes_ask"], 0.45)

    def test_missing_nws_snapshot_blocks_recommendations(self):
        """Verify that a missing NWS snapshot file completely blocks paper recommendations."""
        import paper_trading.signal_generator as sg
        
        forecast_path = self.temp_dir / "kmia_forecast_2026-05-15_rules_v2_climatology_120000.json"
        forecast_data = {
            "date": "2026-05-15",
            "probability_bins": {">=93": 0.95},
            "generated_at_utc": "2026-05-15T12:00:00Z"
        }
        with open(forecast_path, "w") as f:
            json.dump(forecast_data, f)
            
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-15T12:00:00Z",
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY15-T93",
                    "title": "Will KMIA reach 93 or above?",
                    "subtitle": "93 degrees or above",
                    "yes_ask_dollars": 0.45,
                    "status": "active"
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
            
        # Point to a non-existent NWS snapshot
        sg.NWS_SNAPSHOT_FILE = self.temp_dir / "does_not_exist_nws.json"
        
        test_now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        latest_path = self.temp_dir / "latest_paper_signal.json"
        
        generate_paper_signal(
            forecast_path=forecast_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        
        with open(latest_path, "r") as f:
            report = json.load(f)
            
        # Top-level fields
        self.assertFalse(report["allow_paper_recommendations"])
        self.assertEqual(report["weather_gate"]["allow_paper_recommendations"], False)
        self.assertIn("missing or None", report["no_trade_reason"])
        
        # Per-signal fields
        self.assertEqual(len(report["signals"]), 1)
        sig = report["signals"][0]
        self.assertEqual(sig["weather_gate_status"], "MISSING")
        self.assertEqual(sig["risk_decision"], "BLOCK")
        self.assertEqual(sig["paper_action"], "NO TRADE")
        self.assertIn("missing or None", sig["no_trade_reason"])
        
        # Diagnostic fields preserved
        self.assertEqual(sig["model_probability"], 0.95)
        self.assertEqual(sig["yes_ask"], 0.45)
        self.assertAlmostEqual(sig["edge"], 0.4827, places=4)

    def test_stale_nws_snapshot_blocks_recommendations(self):
        """Verify that a stale NWS snapshot file completely blocks paper recommendations."""
        import paper_trading.signal_generator as sg
        
        forecast_path = self.temp_dir / "kmia_forecast_2026-05-15_rules_v2_climatology_120000.json"
        forecast_data = {
            "date": "2026-05-15",
            "probability_bins": {">=93": 0.95},
            "generated_at_utc": "2026-05-15T12:00:00Z"
        }
        with open(forecast_path, "w") as f:
            json.dump(forecast_data, f)
            
        snapshot_path = self.temp_dir / "latest_kalshi_market_snapshot.json"
        snapshot_data = {
            "generated_at_utc": "2026-05-15T12:00:00Z",
            "selected_temperature_markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY15-T93",
                    "title": "Will KMIA reach 93 or above?",
                    "subtitle": "93 degrees or above",
                    "yes_ask_dollars": 0.45,
                    "status": "active"
                }
            ]
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)
            
        # Point to a STALE NWS snapshot (e.g. 3 hours old observation, past the limit)
        nws_path = self.temp_dir / "latest_nws_kmia_snapshot.json"
        self._create_valid_nws_snapshot(
            nws_path, 
            "2026-05-15", 
            obs_time_str="09:00:00+00:00", 
            fetched_time_str="09:05:00+00:00"
        )
        sg.NWS_SNAPSHOT_FILE = nws_path
        
        test_now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        latest_path = self.temp_dir / "latest_paper_signal.json"
        
        generate_paper_signal(
            forecast_path=forecast_path,
            snapshot_path=snapshot_path,
            prediction_timestamp=test_now,
            output_dir=self.temp_dir,
            latest_path_override=str(latest_path)
        )
        
        with open(latest_path, "r") as f:
            report = json.load(f)
            
        # Top-level fields
        self.assertFalse(report["allow_paper_recommendations"])
        self.assertEqual(report["weather_gate"]["allow_paper_recommendations"], False)
        self.assertIn("stale", report["no_trade_reason"].lower())
        
        # Per-signal fields
        self.assertEqual(len(report["signals"]), 1)
        sig = report["signals"][0]
        self.assertEqual(sig["weather_gate_status"], "STALE")
        self.assertEqual(sig["risk_decision"], "BLOCK")
        self.assertEqual(sig["paper_action"], "NO TRADE")
        self.assertIn("stale", sig["no_trade_reason"].lower())

if __name__ == "__main__":
    unittest.main()

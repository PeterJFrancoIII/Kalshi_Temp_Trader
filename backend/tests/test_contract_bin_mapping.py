import unittest
import sys
import os
import json
from unittest.mock import MagicMock
from datetime import datetime, timezone

# Mock pydantic before importing anything that uses it
pydantic_mock = MagicMock()
class BaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def model_dump(self):
        return self.__dict__
pydantic_mock.BaseModel = BaseModel
pydantic_mock.Field = MagicMock()
pydantic_mock.field_validator = lambda *args, **kwargs: lambda f: f
pydantic_mock.model_validator = lambda *args, **kwargs: lambda f: f

sys.modules['pydantic'] = pydantic_mock

# Add backend and src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

class TestContractBinMapping(unittest.TestCase):

    def test_structured_greater_contract(self):
        from market_data.kalshi_contract_mapper import market_to_contract_bin
        
        market = {
            "ticker": "KXHIGHMIA-26MAY11-T93",
            "strike_type": "greater",
            "floor_strike": 93,
            "title": "Will the high temperature be above 93?",
            "subtitle": "94° or above"
        }
        
        cb = market_to_contract_bin(market)
        self.assertEqual(cb.condition_type, "above")
        self.assertEqual(cb.label, ">93")
        self.assertEqual(cb.lower_f, 94)
        self.assertIsNone(cb.upper_f)
        self.assertTrue(cb.contains(94))
        self.assertFalse(cb.contains(93))

    def test_structured_less_contract(self):
        from market_data.kalshi_contract_mapper import market_to_contract_bin
        
        market = {
            "ticker": "KXHIGHMIA-26MAY11-T86",
            "strike_type": "less",
            "cap_strike": 86,
            "title": "Will the high temperature be below 86?",
            "subtitle": "85° or below"
        }
        
        cb = market_to_contract_bin(market)
        self.assertEqual(cb.condition_type, "below")
        self.assertEqual(cb.label, "<86")
        self.assertIsNone(cb.lower_f)
        self.assertEqual(cb.upper_f, 85)
        self.assertTrue(cb.contains(85))
        self.assertFalse(cb.contains(86))

    def test_structured_between_contract(self):
        from market_data.kalshi_contract_mapper import market_to_contract_bin
        
        market = {
            "ticker": "KXHIGHMIA-26MAY11-B92.5",
            "strike_type": "between",
            "floor_strike": 92,
            "cap_strike": 93,
            "title": "Will the high temperature be 92-93?"
        }
        
        cb = market_to_contract_bin(market)
        self.assertEqual(cb.condition_type, "between")
        self.assertEqual(cb.label, "92-93")
        self.assertEqual(cb.lower_f, 92)
        self.assertEqual(cb.upper_f, 93)
        self.assertTrue(cb.contains(92))
        self.assertTrue(cb.contains(93))
        self.assertFalse(cb.contains(94))

    def test_fallback_parsing(self):
        from market_data.kalshi_contract_mapper import market_to_contract_bin
        
        m1 = {"title": "<86"}
        cb1 = market_to_contract_bin(m1)
        self.assertEqual(cb1.condition_type, "below")
        self.assertEqual(cb1.upper_f, 85)
        
        m2 = {"title": "<=89"}
        cb2 = market_to_contract_bin(m2)
        self.assertEqual(cb2.condition_type, "below")
        self.assertEqual(cb2.upper_f, 89)
        
        m3 = {"title": "91-92"}
        cb3 = market_to_contract_bin(m3)
        self.assertEqual(cb3.condition_type, "between")
        self.assertEqual(cb3.lower_f, 91)
        self.assertEqual(cb3.upper_f, 92)
        
        m4 = {"title": "92 to 93"}
        cb4 = market_to_contract_bin(m4)
        self.assertEqual(cb4.condition_type, "between")
        self.assertEqual(cb4.lower_f, 92)
        self.assertEqual(cb4.upper_f, 93)
        
        m5 = {"title": ">93"}
        cb5 = market_to_contract_bin(m5)
        self.assertEqual(cb5.condition_type, "above")
        self.assertEqual(cb5.lower_f, 94)
        
        m6 = {"title": ">=95"}
        cb6 = market_to_contract_bin(m6)
        self.assertEqual(cb6.condition_type, "above")
        self.assertEqual(cb6.lower_f, 95)

    def test_serialization(self):
        from shared.types import ContractBin
        
        cb = ContractBin(
            ticker="TEST",
            label="91-92",
            condition_type="between",
            lower_f=91,
            upper_f=92
        )
        
        dumped = cb.model_dump()
        self.assertEqual(dumped["ticker"], "TEST")
        self.assertEqual(dumped["label"], "91-92")
        self.assertEqual(dumped["condition_type"], "between")
        self.assertEqual(dumped["lower_f"], 91)
        self.assertEqual(dumped["upper_f"], 92)

    def test_parse_kalshi_markets_compatibility(self):
        from market_data.kalshi_contract_mapper import parse_kalshi_markets
        
        raw_markets = {
            "markets": [{
                "ticker": "KXHIGHMIA-26MAY11-T93",
                "strike_type": "greater",
                "floor_strike": 93,
                "title": "Will the high temperature be above 93?",
                "status": "open"
            }]
        }
        
        import tempfile
        from pathlib import Path
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump(raw_markets, f)
            temp_path = Path(f.name)
            
        try:
            parsed = parse_kalshi_markets(temp_path)
            self.assertEqual(len(parsed), 1)
            self.assertIn("contract_mapping", parsed[0])
            self.assertIn("contract_bin", parsed[0])
            self.assertIsInstance(parsed[0]["contract_bin"], dict)
        finally:
            temp_path.unlink()

    def test_paper_signal_logic(self):
        import paper_trading.signal_generator
        import market_data.kalshi_contract_mapper
        
        # Save original functions to restore later
        orig_get_latest_file = paper_trading.signal_generator.get_latest_file
        orig_parse_markets = market_data.kalshi_contract_mapper.parse_kalshi_markets
        
        import tempfile
        from pathlib import Path
        
        # Create a dummy forecast file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump({"probability_bins": {"91-92": 0.5}}, f)
            temp_forecast = Path(f.name)
            
        try:
            # Mock get_latest_file to return our temp forecast file
            paper_trading.signal_generator.get_latest_file = MagicMock(return_value=temp_forecast)
            
            # Mock parse_kalshi_markets in the source module
            market_data.kalshi_contract_mapper.parse_kalshi_markets = MagicMock(return_value=[{
                "ticker": "TEST-1",
                "contract_bin": {"label": "91-92"},
                "yes_ask_dollars": 0.4,
                "status": "open"
            }])
            
            # Run generate_paper_signal
            path = paper_trading.signal_generator.generate_paper_signal()
            
            # Read the generated file
            with open(path, "r") as f:
                report = json.load(f)
                
            signals = report["signals"]
            self.assertEqual(len(signals), 1)
            self.assertEqual(signals[0]["market_ticker"], "TEST-1")
            self.assertEqual(signals[0]["model_probability"], 0.5)
            
            # Clean up the generated files!
            os.unlink(path)
            
        finally:
            # Restore original functions
            paper_trading.signal_generator.get_latest_file = orig_get_latest_file
            market_data.kalshi_contract_mapper.parse_kalshi_markets = orig_parse_markets
            # Clean up temp forecast file
            temp_forecast.unlink()

    def test_paper_signal_with_integer_distribution(self):
        import paper_trading.signal_generator
        import market_data.kalshi_contract_mapper
        
        # Save original functions to restore later
        orig_get_latest_file = paper_trading.signal_generator.get_latest_file
        orig_parse_markets = market_data.kalshi_contract_mapper.parse_kalshi_markets
        
        import tempfile
        from pathlib import Path
        
        # Create a dummy forecast file with integer_distribution
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump({
                "probability_bins": {},
                "integer_distribution": {
                    "92": 0.0133,
                    "93": 0.0144
                }
            }, f)
            temp_forecast = Path(f.name)
            
        try:
            # Mock get_latest_file to return our temp forecast file
            paper_trading.signal_generator.get_latest_file = MagicMock(return_value=temp_forecast)
            
            # Mock map_distribution_to_bins to prevent ImportError
            from unittest.mock import patch
            mock_map = MagicMock(return_value={"92-93": 0.0277})
            patcher = patch("forecasting.rules_model_v2.map_distribution_to_bins", mock_map, create=True)
            patcher.start()
            
            # Mock parse_kalshi_markets in the source module
            market_data.kalshi_contract_mapper.parse_kalshi_markets = MagicMock(return_value=[{
                "ticker": "TEST-2",
                "contract_bin": {"label": "92-93"},
                "yes_ask_dollars": 0.4,
                "status": "open"
            }])
            
            # Run generate_paper_signal
            path = paper_trading.signal_generator.generate_paper_signal()
            
            # Read the generated file
            with open(path, "r") as f:
                report = json.load(f)
                
            signals = report["signals"]
            self.assertEqual(len(signals), 1)
            self.assertEqual(signals[0]["market_ticker"], "TEST-2")
            # 0.0133 + 0.0144 = 0.0277
            self.assertAlmostEqual(signals[0]["model_probability"], 0.0277)
            
            # Clean up the generated files!
            os.unlink(path)
            
        finally:
            # Restore original functions
            paper_trading.signal_generator.get_latest_file = orig_get_latest_file
            market_data.kalshi_contract_mapper.parse_kalshi_markets = orig_parse_markets
            # Clean up temp forecast file
            temp_forecast.unlink()
            try:
                patcher.stop()
            except RuntimeError:
                pass

    def test_paper_signal_no_signal_fallback(self):
        import paper_trading.signal_generator
        import market_data.kalshi_contract_mapper
        
        # Save original functions to restore later
        orig_get_latest_file = paper_trading.signal_generator.get_latest_file
        orig_parse_markets = market_data.kalshi_contract_mapper.parse_kalshi_markets
        
        import tempfile
        from pathlib import Path
        
        # Create a dummy forecast file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump({"probability_bins": {}}, f)
            temp_forecast = Path(f.name)
            
        try:
            # Mock get_latest_file to return our temp forecast file
            paper_trading.signal_generator.get_latest_file = MagicMock(return_value=temp_forecast)
            
            # Mock parse_kalshi_markets to return a market that won't match any bin
            market_data.kalshi_contract_mapper.parse_kalshi_markets = MagicMock(return_value=[{
                "ticker": "TEST-FALLBACK",
                "contract_bin": {"label": "99-100"},
                "yes_ask_dollars": 0.4,
                "status": "open"
            }])
            
            # Run generate_paper_signal
            path = paper_trading.signal_generator.generate_paper_signal()
            
            # Read the generated file
            with open(path, "r") as f:
                report = json.load(f)
                
            signals = report["signals"]
            self.assertEqual(len(signals), 1)
            self.assertEqual(signals[0]["market_ticker"], "TEST-FALLBACK")
            self.assertIsNone(signals[0]["model_probability"])
            self.assertEqual(signals[0]["paper_action"], "NO SIGNAL")
            self.assertIn("warnings", signals[0])
            
            # Clean up the generated files!
            os.unlink(path)
            
        finally:
            # Restore original functions
            paper_trading.signal_generator.get_latest_file = orig_get_latest_file
            market_data.kalshi_contract_mapper.parse_kalshi_markets = orig_parse_markets
            # Clean up temp forecast file
            temp_forecast.unlink()

    def test_generate_signal_logic_debug(self):
        """Verify that signals are generated when forecast and markets align."""
        import tempfile
        from pathlib import Path
        
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
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
                    
                print(f"DEBUG REPORT: {report}")
                
                self.assertGreater(len(report["signals"]), 0)
                sig = report["signals"][0]
                self.assertEqual(sig["market_ticker"], "KXHIGHMIA-26MAY07-B86.5")
                self.assertAlmostEqual(sig["model_probability"], 0.4)
                
            finally:
                sg.REPORTS_DIR = original_reports
                sg.SNAPSHOT_FILE = original_snapshot
                
        finally:
            import shutil
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    unittest.main()


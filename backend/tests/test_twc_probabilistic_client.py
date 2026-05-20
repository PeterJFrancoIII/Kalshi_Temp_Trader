import unittest
from unittest.mock import patch, MagicMock
import json
import os
from pathlib import Path
import sys
import tempfile

# Ensure backend/src is in path for imports if needed
# But we expect to run with PYTHONPATH or pytest handling it via pyproject.toml

from weather import twc_probabilistic_client

class TestTWCProbabilisticClient(unittest.TestCase):

    def setUp(self):
        # Clear environment variables
        self.old_key = os.environ.get("TWC_API_KEY")
        self.old_wc_key = os.environ.get("WEATHER_COMPANY_API_KEY")
        if "TWC_API_KEY" in os.environ:
            del os.environ["TWC_API_KEY"]
        if "WEATHER_COMPANY_API_KEY" in os.environ:
            del os.environ["WEATHER_COMPANY_API_KEY"]
            
    def tearDown(self):
        if self.old_key:
            os.environ["TWC_API_KEY"] = self.old_key
        if self.old_wc_key:
            os.environ["WEATHER_COMPANY_API_KEY"] = self.old_wc_key
            
    def test_missing_credentials_returns_unavailable(self):
        snapshot = twc_probabilistic_client.fetch_twc_probabilistic_forecast(25.79540, -80.29010)
        self.assertEqual(snapshot["api_status"], "missing_credentials")
        self.assertIn("TWC_API_KEY", snapshot["warnings"])
        self.assertIsNone(snapshot["parsed_percentiles"])
        
    def test_checks_weather_company_api_key(self):
        os.environ["WEATHER_COMPANY_API_KEY"] = "fake_wc_key"
        key = twc_probabilistic_client.get_twc_api_key()
        self.assertEqual(key, "fake_wc_key")
        
    @patch('weather.twc_probabilistic_client.requests.get')
    def test_successful_parse(self, mock_get):
        os.environ["TWC_API_KEY"] = "fake_key"
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "percentiles": [10, 50, 90],
            "pdf": {"point": "value"}
        }
        mock_get.return_value = mock_resp
        
        snapshot = twc_probabilistic_client.fetch_twc_probabilistic_forecast(25.79540, -80.29010)
        
        self.assertEqual(snapshot["api_status"], "success")
        self.assertEqual(snapshot["parsed_percentiles"], [10, 50, 90])
        self.assertEqual(snapshot["parsed_pdf_or_probability_fields"], {"point": "value"})
        
    @patch('weather.twc_probabilistic_client.requests.get')
    def test_unauthorized_response(self, mock_get):
        os.environ["TWC_API_KEY"] = "fake_key"
        
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_get.return_value = mock_resp
        
        snapshot = twc_probabilistic_client.fetch_twc_probabilistic_forecast(25.79540, -80.29010)
        
        self.assertEqual(snapshot["api_status"], "unauthorized")
        self.assertIn("401", snapshot["warnings"])
        
    def test_parse_missing_fields_does_not_crash(self):
        raw_data = {} # Missing fields
        parsed = twc_probabilistic_client.parse_twc_response(raw_data)
        self.assertEqual(parsed["api_status"], "success")
        self.assertIsNone(parsed["parsed_percentiles"])
        self.assertIsNone(parsed["parsed_pdf_or_probability_fields"])
        
    def test_snapshot_write_path_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = twc_probabilistic_client.PROCESSED_DIR
            twc_probabilistic_client.PROCESSED_DIR = Path(tmpdir)
            
            snapshot = twc_probabilistic_client.build_unavailable_snapshot("test", "test")
            twc_probabilistic_client.save_snapshots(snapshot)
            
            latest_path = Path(tmpdir) / "latest_twc_probabilistic_kmia_snapshot.json"
            self.assertTrue(latest_path.exists())
            
            # Restore
            twc_probabilistic_client.PROCESSED_DIR = old_dir

    def test_missing_credentials_does_not_overwrite_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = twc_probabilistic_client.PROCESSED_DIR
            twc_probabilistic_client.PROCESSED_DIR = Path(tmpdir)
            
            # Write a valid latest snapshot first
            valid_snapshot = twc_probabilistic_client.build_unavailable_snapshot("success", "")
            valid_snapshot["api_status"] = "success"
            twc_probabilistic_client.save_snapshots(valid_snapshot)
            
            latest_path = Path(tmpdir) / "latest_twc_probabilistic_kmia_snapshot.json"
            self.assertTrue(latest_path.exists())
            
            # Attempt to save a missing credentials snapshot
            missing_snapshot = twc_probabilistic_client.build_unavailable_snapshot("missing_credentials", "No key")
            twc_probabilistic_client.save_snapshots(missing_snapshot)
            
            # Verify latest snapshot is unchanged and is still the success one
            with open(latest_path, "r") as f:
                saved = json.load(f)
            self.assertEqual(saved["api_status"], "success")
            
            # Verify unavailable snapshot was written to the separate file
            unavail_path = Path(tmpdir) / "unavailable_twc_probabilistic_kmia_snapshot.json"
            self.assertTrue(unavail_path.exists())
            with open(unavail_path, "r") as f:
                saved_unavail = json.load(f)
            self.assertEqual(saved_unavail["api_status"], "missing_credentials")
            
            # Restore
            twc_probabilistic_client.PROCESSED_DIR = old_dir
            
if __name__ == '__main__':
    unittest.main()

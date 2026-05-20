import unittest
from dashboard.report_generator import KMIAForecastReport

class TestKMIAForecastReport(unittest.TestCase):
    def setUp(self):
        self.sample_data = {
            "station": "KMIA",
            "date": "2026-05-03",
            "metric": "daily_max_temperature_f",
            "best_single_number_f": 84,
            "probability_bins": {
                "<=78": 0.00,
                "79-80": 0.05,
                "81-82": 0.20,
                "83-84": 0.55,
                "85-86": 0.15,
                ">=87": 0.05
            },
            "observed_max_so_far_f": 83,
            "current_temp_f": 82,
            "forecast_high_f": 84,
            "confidence": "high",
            "main_drivers": ["Onshore flow", "Clear skies"],
            "warnings": ["Late shower potential"]
        }

    def test_report_validation(self):
        """Verify that the report generator catches missing fields."""
        incomplete_data = {"station": "KMIA"}
        with self.assertRaisesRegex(ValueError, "Missing required field"):
            KMIAForecastReport(incomplete_data)

    def test_markdown_output(self):
        """Verify that all required bins and data appear in Markdown."""
        report = KMIAForecastReport(self.sample_data)
        output = report.to_markdown()
        
        # Check bins
        for bin_name in KMIAForecastReport.REQUIRED_BINS:
            self.assertIn(bin_name, output)
            
        # Check key fields
        self.assertIn("KMIA", output)
        self.assertIn("84°F", output)
        self.assertIn("83°F", output)
        self.assertIn("HIGH", output)
        self.assertIn("Late shower potential", output)

    def test_html_output(self):
        """Verify that all required bins and data appear in HTML."""
        report = KMIAForecastReport(self.sample_data)
        output = report.to_html()
        
        # Check bins
        for bin_name in KMIAForecastReport.REQUIRED_BINS:
            self.assertIn(bin_name, output)
            
        # Check basic HTML structure
        self.assertIn("<!DOCTYPE html>", output)
        self.assertIn("<h1>KMIA Forecast Dashboard</h1>", output)
        self.assertIn("84°F", output)
        self.assertIn("Late shower potential", output)


class TestJSONLoadersSuffixRestriction(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_json_loaders_only_parse_json(self):
        from pathlib import Path
        # import from backend src
        from console.data_helpers import load_json as load_json_helpers, latest_file as latest_file_helpers
        import importlib
        weather_module = importlib.import_module("pages.1_Weather_Providers_NWS_vs_TWC")
        load_json_weather = weather_module.load_json
        latest_file_weather = weather_module.latest_file
        
        from paper_trading.learning import load_json as load_json_learning
        from paper_trading.prediction_quality import load_json as load_json_pred
        
        # Create .json, .md, .log files in temp_dir
        valid_json = Path(self.temp_dir) / "test_file_2026-05-20_120000.json"
        with open(valid_json, "w") as f:
            f.write('{"api_status": "ok", "timestamp": "2026-05-20T12:00:00Z"}')
            
        invalid_md = Path(self.temp_dir) / "test_file_2026-05-20_120000.md"
        with open(invalid_md, "w") as f:
            f.write("# Some Markdown Title\nNot JSON")
            
        invalid_log = Path(self.temp_dir) / "test_file_2026-05-20_120000.log"
        with open(invalid_log, "w") as f:
            f.write("2026-05-20 12:00:00 - Log Message")
            
        # Test load_json functions with non-JSON paths
        self.assertIsNone(load_json_helpers(invalid_md))
        self.assertIsNone(load_json_helpers(invalid_log))
        
        self.assertEqual(load_json_weather(invalid_md), {})
        self.assertEqual(load_json_weather(invalid_log), {})
        
        self.assertEqual(load_json_learning(invalid_md), {})
        self.assertEqual(load_json_learning(invalid_log), {})
        
        self.assertIsNone(load_json_pred(invalid_md))
        self.assertIsNone(load_json_pred(invalid_log))
        
        # Test load_json with valid JSON path
        self.assertEqual(load_json_helpers(valid_json), {"api_status": "ok", "timestamp": "2026-05-20T12:00:00Z"})
        self.assertEqual(load_json_weather(valid_json), {"api_status": "ok", "timestamp": "2026-05-20T12:00:00Z"})
        self.assertEqual(load_json_learning(valid_json), {"api_status": "ok", "timestamp": "2026-05-20T12:00:00Z"})
        self.assertEqual(load_json_pred(valid_json), {"api_status": "ok", "timestamp": "2026-05-20T12:00:00Z"})

        # Test latest_file only parses JSON file embedded timestamp, skips calling extract_embedded_timestamp on .md/.log
        latest_helper = latest_file_helpers(Path(self.temp_dir), "test_file_*.json")
        self.assertEqual(latest_helper, valid_json)
        
        latest_md = latest_file_helpers(Path(self.temp_dir), "test_file_*.md")
        self.assertEqual(latest_md, invalid_md)


if __name__ == "__main__":
    unittest.main()

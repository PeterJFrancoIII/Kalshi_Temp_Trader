import unittest
from backend.src.dashboard.report_generator import KMIAForecastReport

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

if __name__ == "__main__":
    unittest.main()

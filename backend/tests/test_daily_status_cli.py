import os
import unittest
from unittest.mock import patch, MagicMock
from status.daily_status import write_status_report

class TestDailyStatusCLI(unittest.TestCase):
    def test_write_status_report_paths(self):
        """Verify that write_status_report generates deterministic paths."""
        mock_status = {
            "date": "2026-05-03",
            "system_status": "OK",
            "station": "KMIA",
            "metric": "daily_max_temperature_f",
            "safety": {"real_trading_enabled": False, "note": "Safe"},
            "forecast": {"latest_v2_report": None, "latest_v1_report": None, "latest_comparison_report": None, "summary": "Test"},
            "aggregate_calibration": {"settled_days": 0, "v1_avg_brier": None, "v2_avg_brier": None, "v2_win_rate_by_brier": None},
            "workflow_log": {"latest_log_path": None, "contains_error": False, "contains_warning": False, "contains_traceback": False, "tail": ""},
            "paper_trading": {"available": False, "summary": "Test"},
            "warnings": []
        }
        
        output_dir = "test_status_dir"
        
        with patch("os.makedirs"):
            with patch("builtins.open", MagicMock()):
                paths = write_status_report(mock_status, output_dir)
                
                expected_json = os.path.join(output_dir, "kmia_daily_status_2026-05-03.json")
                expected_md = os.path.join(output_dir, "kmia_daily_status_2026-05-03.md")
                
                self.assertIn(expected_json, paths)
                self.assertIn(expected_md, paths)

if __name__ == "__main__":
    unittest.main()

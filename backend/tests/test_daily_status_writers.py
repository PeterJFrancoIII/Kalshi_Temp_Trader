import os
import json
import shutil
import tempfile
import unittest
from status.daily_status import write_daily_status_json, write_daily_status_markdown

class TestDailyStatusWriters(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.status = {
            "date": "2026-05-03",
            "station": "KMIA",
            "system_status": "OK",
            "workflow_log": {
                "contains_error": False,
                "contains_traceback": False,
                "latest_log_path": "logs/test.log"
            },
            "forecast": {
                "latest_v2_report": "reports/v2.md",
                "latest_v1_report": "reports/v1.md",
                "latest_comparison_report": "reports/comp.md"
            },
            "aggregate_calibration": {
                "settled_days": 10,
                "v2_win_rate_by_brier": 0.7
            },
            "warnings": ["Test warning"],
            "safety": {
                "note": "No real trading execution is implemented."
            }
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_write_json(self):
        path = os.path.join(self.test_dir, "nested/status.json")
        write_daily_status_json(self.status, path)
        
        self.assertTrue(os.path.exists(path))
        with open(path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["date"], "2026-05-03")
        self.assertEqual(data["system_status"], "OK")

    def test_write_markdown(self):
        path = os.path.join(self.test_dir, "nested/status.md")
        write_daily_status_markdown(self.status, path)
        
        self.assertTrue(os.path.exists(path))
        with open(path, 'r') as f:
            content = f.read()
        
        self.assertIn("# KMIA Daily Status Report", content)
        self.assertIn("Date**: 2026-05-03", content)
        self.assertIn("Overall**: OK", content)
        self.assertIn("V2 Win Rate (Brier)**: 70.0%", content)
        self.assertIn("No real trading execution is implemented.", content)
        self.assertIn("⚠️ Test warning", content)

if __name__ == "__main__":
    unittest.main()

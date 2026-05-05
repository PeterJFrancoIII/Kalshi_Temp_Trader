import unittest
import os
import json
from datetime import datetime
from scheduler.generate_daily_status import get_daily_status, write_json_status, write_markdown_status, STATUS_DIR

class TestDailyStatus(unittest.TestCase):
    def test_get_daily_status_runs(self):
        status = get_daily_status()
        self.assertIn("date", status)
        self.assertIn("safety_status", status)
        self.assertEqual(status["safety_status"], "SECURE")
        
    def test_write_reports(self):
        status = {
            "date": "2026-01-01",
            "timestamp": datetime.now().isoformat(),
            "safety_status": "SECURE",
            "forecasts": {"v1": "test_v1.md"},
            "comparison": "test_comp.md",
            "calibration": {"v1_avg_brier": 0.25, "settled_days": 10},
            "workflow": {"status": "SUCCESS", "last_log": "test.log"},
            "paper_trading": {"available": False, "record_count": 0},
            "warnings": ["Test warning"]
        }
        
        json_path = write_json_status(status)
        md_path = write_markdown_status(status)
        
        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(md_path))
        
        with open(json_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["date"], "2026-01-01")
            
        with open(md_path, 'r') as f:
            content = f.read()
            self.assertIn("# KMIA Daily Status Report - 2026-01-01", content)
            self.assertIn("Test warning", content)
            
        # Cleanup
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(md_path):
            os.remove(md_path)

if __name__ == "__main__":
    unittest.main()

import unittest
import tempfile
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
from console import data_helpers

PAGE_PATH = Path(__file__).resolve().parents[1] / "src" / "pages" / "1_Weather_Providers_NWS_vs_TWC.py"

def load_page_module():
    spec = importlib.util.spec_from_file_location("weather_providers_page", PAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

class TestEmbeddedTimestampSelection(unittest.TestCase):

    def test_data_helpers_latest_file_prefers_embedded_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create three files with different mtimes but inverted embedded timestamps
            file_old_ts = tmpdir_path / "status_old.json"
            file_new_ts = tmpdir_path / "status_new.json"
            file_no_ts = tmpdir_path / "status_none.json"
            
            # "new" timestamp is 2026-05-19T20:00:00Z
            new_ts_str = "2026-05-19T20:00:00Z"
            # "old" timestamp is 2026-05-19T10:00:00Z
            old_ts_str = "2026-05-19T10:00:00Z"
            
            with open(file_old_ts, "w") as f:
                json.dump({"timestamp": old_ts_str}, f)
            with open(file_new_ts, "w") as f:
                json.dump({"timestamp": new_ts_str}, f)
            with open(file_no_ts, "w") as f:
                json.dump({"no_time_field": "val"}, f)
                
            # Set filesystem mtimes to be opposite of embedded timestamps
            # file_old_ts has a newer filesystem mtime
            os.utime(file_old_ts, (1700000000, 1800000000))
            # file_new_ts has an older filesystem mtime
            os.utime(file_new_ts, (1700000000, 1700000000))
            
            # Select latest_file using data_helpers (which parses embedded timestamp)
            selected = data_helpers.latest_file(tmpdir_path, "status_*.json")
            self.assertEqual(selected, file_new_ts)
            
            # Test that invalid or missing embedded timestamps are excluded
            selected_none = data_helpers.latest_file(tmpdir_path, "status_none.json")
            self.assertIsNone(selected_none)

    def test_weather_page_latest_file_prefers_embedded_timestamp(self):
        page_module = load_page_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            file_old_ts = tmpdir_path / "nws_old.json"
            file_new_ts = tmpdir_path / "nws_new.json"
            
            # "new" timestamp is 2026-05-19T22:00:00Z
            new_ts_str = "2026-05-19T22:00:00Z"
            # "old" timestamp is 2026-05-19T12:00:00Z
            old_ts_str = "2026-05-19T12:00:00Z"
            
            with open(file_old_ts, "w") as f:
                json.dump({"fetched_at_utc": old_ts_str}, f)
            with open(file_new_ts, "w") as f:
                json.dump({"fetched_at_utc": new_ts_str}, f)
                
            os.utime(file_old_ts, (1700000000, 1800000000))
            os.utime(file_new_ts, (1700000000, 1700000000))
            
            selected = page_module.latest_file(tmpdir_path, "nws_*.json")
            self.assertEqual(selected, file_new_ts)

    def test_weather_page_file_age_seconds(self):
        page_module = load_page_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            file_path = tmpdir_path / "nws_snapshot.json"
            now_utc = datetime.now(timezone.utc)
            # Embed a timestamp that is exactly 500 seconds ago
            ts_str = (now_utc - timedelta(seconds=500)).isoformat()
            
            with open(file_path, "w") as f:
                json.dump({"fetched_at_utc": ts_str}, f)
                
            age = page_module.file_age_seconds(file_path)
            self.assertIsNotNone(age)
            # Should be roughly 500 seconds (allow tiny delta for test run time)
            self.assertAlmostEqual(age, 500.0, delta=5.0)

            # Missing or invalid embedded timestamp should return None
            file_no_ts = tmpdir_path / "nws_no_ts.json"
            with open(file_no_ts, "w") as f:
                json.dump({"invalid_key": "val"}, f)
            self.assertIsNone(page_module.file_age_seconds(file_no_ts))

if __name__ == "__main__":
    unittest.main()

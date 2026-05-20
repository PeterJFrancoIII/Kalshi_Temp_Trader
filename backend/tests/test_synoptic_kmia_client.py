import unittest
from unittest.mock import patch, MagicMock
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from dateutil import tz

from weather import synoptic_kmia_client


class TestSynopticKMIAClient(unittest.TestCase):

    def setUp(self):
        # Clear environment variables
        self.old_token = os.environ.get("SYNOPTIC_TOKEN")
        self.old_api_token = os.environ.get("SYNOPTIC_API_TOKEN")
        if "SYNOPTIC_TOKEN" in os.environ:
            del os.environ["SYNOPTIC_TOKEN"]
        if "SYNOPTIC_API_TOKEN" in os.environ:
            del os.environ["SYNOPTIC_API_TOKEN"]

    def tearDown(self):
        if self.old_token:
            os.environ["SYNOPTIC_TOKEN"] = self.old_token
        if self.old_api_token:
            os.environ["SYNOPTIC_API_TOKEN"] = self.old_api_token

    def test_missing_credentials_returns_unavailable(self):
        snapshot = synoptic_kmia_client.fetch_synoptic_observations()
        self.assertEqual(snapshot["endpoint_status"], "MISSING_CREDENTIALS")
        self.assertIn("Synoptic API token not set", snapshot["warnings"][0])
        self.assertEqual(snapshot["recent_observations_table"], [])

    def test_checks_synoptic_api_token_fallback(self):
        os.environ["SYNOPTIC_API_TOKEN"] = "fallback_token"
        token = synoptic_kmia_client.get_synoptic_token()
        self.assertEqual(token, "fallback_token")

    def test_checks_synoptic_token_primary(self):
        os.environ["SYNOPTIC_TOKEN"] = "primary_token"
        os.environ["SYNOPTIC_API_TOKEN"] = "fallback_token"
        token = synoptic_kmia_client.get_synoptic_token()
        self.assertEqual(token, "primary_token")

    @patch('weather.synoptic_kmia_client.requests.get')
    def test_unauthorized_response(self, mock_get):
        os.environ["SYNOPTIC_TOKEN"] = "fake_token"
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_get.return_value = mock_resp

        snapshot = synoptic_kmia_client.fetch_synoptic_observations()
        self.assertEqual(snapshot["endpoint_status"], "ERROR")
        self.assertIn("401", snapshot["warnings"][0])

    @patch('weather.synoptic_kmia_client.requests.get')
    def test_failed_api_response_code(self, mock_get):
        os.environ["SYNOPTIC_TOKEN"] = "fake_token"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "SUMMARY": {
                "RESPONSE_CODE": 2,
                "RESPONSE_MESSAGE": "Invalid station ID"
            }
        }
        mock_get.return_value = mock_resp

        snapshot = synoptic_kmia_client.fetch_synoptic_observations()
        self.assertEqual(snapshot["endpoint_status"], "ERROR")
        self.assertIn("Invalid station ID", snapshot["warnings"][0])

    def test_parse_valid_response(self):
        # Build a realistic mock API response in America/New_York
        tz_et = tz.gettz("America/New_York")
        now_et = datetime.now(tz_et)
        today_str = now_et.date().isoformat()

        # Let's create timestamps: one yesterday, two today
        t1_utc = datetime(now_et.year, now_et.month, now_et.day, 2, 0, tzinfo=tz_et).astimezone(timezone.utc).isoformat()
        t2_utc = datetime(now_et.year, now_et.month, now_et.day, 13, 0, tzinfo=tz_et).astimezone(timezone.utc).isoformat()
        # Yesterday:
        t_yest_utc = datetime(now_et.year, now_et.month, now_et.day, 13, 0, tzinfo=tz_et).astimezone(timezone.utc)
        from datetime import timedelta
        t0_utc = (t_yest_utc - timedelta(days=1)).isoformat()

        mock_raw = {
            "UNITS": {
                "air_temp": "Fahrenheit",
                "wind_speed": "mph"
            },
            "STATION": [
                {
                    "STID": "KMIA",
                    "MNET_ID": "1",
                    "OBSERVATIONS": {
                        "date_time": [t0_utc, t1_utc, t2_utc],
                        "air_temp_set_1": [85.0, 78.0, 82.0],
                        "dew_point_temperature_set_1": [65.0, 70.0, 68.0],
                        "wind_speed_set_1": [10.0, 5.0, 15.0],
                        "wind_direction_set_1": [90, 120, 180],
                        "relative_humidity_set_1": [60.0, 80.0, 70.0],
                        "altimeter_set_1": [30.12, 30.15, 30.11]
                    },
                    "QC": {
                        "air_temp_set_1": [None, [1, 1], None]
                    }
                }
            ],
            "SUMMARY": {
                "RESPONSE_CODE": 1,
                "RESPONSE_MESSAGE": "OK"
            }
        }

        parsed = synoptic_kmia_client.parse_synoptic_response(mock_raw)
        self.assertEqual(parsed["endpoint_status"], "OK")
        self.assertEqual(parsed["provider"], "synoptic")
        self.assertEqual(parsed["station"], "KMIA")
        self.assertEqual(parsed["current_temp_f"], 82.0)
        self.assertEqual(parsed["dew_point_f"], 68.0)
        self.assertEqual(parsed["raw_temp_c"], 27.78)
        self.assertEqual(parsed["raw_dewpoint_c"], 20.0)
        # Max temp observed "today" (t1_utc and t2_utc) should be max(78, 82) = 82.0. t0_utc is yesterday and excluded.
        self.assertEqual(parsed["observed_max_so_far_f"], 82.0)
        # Max of the entire window should be max(85, 78, 82) = 85.0
        self.assertEqual(parsed["recent_window_max_temp_f"], 85.0)

        # Check metadata fields
        self.assertEqual(parsed["source_product"], "synoptic_timeseries")
        self.assertEqual(parsed["underlying_feed"], "ASOS/METAR-derived station timeseries")
        self.assertFalse(parsed["raw_sensor_feed"])
        self.assertFalse(parsed["thirty_second_temperature_feed"])
        self.assertEqual(parsed["feed_label"], "synoptic_kmia_feed")
        self.assertEqual(parsed["temporal_resolution_claim"], "1-minute/HF-ASOS")
        self.assertEqual(parsed["endpoint_metadata"]["station_id"], "KMIA")
        self.assertEqual(parsed["endpoint_metadata"]["mnet_id"], "1")
        self.assertEqual(parsed["endpoint_metadata"]["network_name"], "ASOS/AWOS")
        self.assertEqual(parsed["cadence_observed_minutes"], 720.0)
        self.assertIsNotNone(parsed["latency_minutes"])
        self.assertIsInstance(parsed["latency_minutes"], float)

        # Check rows (should be reversed, newest-first)
        rows = parsed["recent_observations_table"]
        self.assertEqual(len(rows), 3)
        
        # Newest: t2_utc
        self.assertEqual(rows[0]["air_temp_f"], 82.0)
        self.assertEqual(rows[0]["dew_point_f"], 68.0)
        self.assertEqual(rows[0]["raw_temp_c"], 27.78)
        self.assertEqual(rows[0]["raw_dewpoint_c"], 20.0)
        self.assertIsNone(rows[0]["qc_flags"])

        # Middle: t1_utc
        self.assertEqual(rows[1]["air_temp_f"], 78.0)
        self.assertEqual(rows[1]["dew_point_f"], 70.0)
        self.assertEqual(rows[1]["raw_temp_c"], 25.56)
        self.assertEqual(rows[1]["raw_dewpoint_c"], 21.11)
        self.assertEqual(rows[1]["qc_flags"], {"air_temp_set_1": [1, 1]})

        # Oldest: t0_utc
        self.assertEqual(rows[2]["air_temp_f"], 85.0)
        self.assertEqual(rows[2]["dew_point_f"], 65.0)
        self.assertEqual(rows[2]["raw_temp_c"], 29.44)
        self.assertEqual(rows[2]["raw_dewpoint_c"], 18.33)
        self.assertIsNone(rows[2]["qc_flags"])

        # Check timezone formatting on dates
        for r in rows:
            self.assertTrue(r["time_utc"].endswith("+00:00") or r["time_utc"].endswith("Z"))


    def test_missing_credentials_does_not_overwrite_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = synoptic_kmia_client.Path(tmpdir)
            
            # Monkeypatch constants or function
            with patch('shared.artifact_paths.WEATHER_SYNOPTIC_DIR', Path(tmpdir)), \
                 patch('shared.artifact_paths.LATEST_SYNOPTIC_KMIA_SNAPSHOT', Path(tmpdir) / "latest_synoptic_kmia_snapshot.json"):
                
                # Write a valid latest snapshot first
                valid_snapshot = synoptic_kmia_client.build_unavailable_snapshot("OK", "")
                valid_snapshot["endpoint_status"] = "OK"
                synoptic_kmia_client.save_snapshots(valid_snapshot, output_dir=Path(tmpdir))
                
                latest_path = Path(tmpdir) / "latest_synoptic_kmia_snapshot.json"
                self.assertTrue(latest_path.exists())
                
                # Attempt to save a missing credentials snapshot
                missing_snapshot = synoptic_kmia_client.build_unavailable_snapshot("MISSING_CREDENTIALS", "No key")
                synoptic_kmia_client.save_snapshots(missing_snapshot, output_dir=Path(tmpdir))
                
                # Verify latest snapshot is unchanged and is still the OK one
                with open(latest_path, "r") as f:
                    saved = json.load(f)
                self.assertEqual(saved["endpoint_status"], "OK")
                
                # Verify unavailable snapshot was written to the separate file
                unavail_path = Path(tmpdir) / "unavailable_synoptic_kmia_snapshot.json"
                self.assertTrue(unavail_path.exists())
                with open(unavail_path, "r") as f:
                    saved_unavail = json.load(f)
                self.assertEqual(saved_unavail["endpoint_status"], "MISSING_CREDENTIALS")


if __name__ == '__main__':
    unittest.main()

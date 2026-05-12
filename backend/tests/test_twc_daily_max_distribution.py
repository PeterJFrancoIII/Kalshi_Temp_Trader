import unittest
import os
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from forecasting.twc_daily_max_distribution import (
    load_latest_twc_snapshot,
    convert_hourly_to_daily_max,
    build_cdf,
    normalize_probability_mass,
    validate_distribution,
    write_distribution_snapshot
)

class TestTWCDailyMaxDistribution(unittest.TestCase):

    def setUp(self):
        self.test_output_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_unavailable_snapshot(self):
        """Unavailable TWC snapshot returns unavailable distribution with warning."""
        res = load_latest_twc_snapshot("non_existent_file.json")
        self.assertEqual(res["status"], "unavailable")
        
        dist = convert_hourly_to_daily_max(res)
        self.assertIn("TWC source data unavailable or missing credentials", dist["warnings"])
        self.assertEqual(dist["integer_probs"], {})

    def test_missing_fields(self):
        """Missing probability/PDF fields does not crash."""
        res = {
            "station": "KMIA",
            "fetched_at_utc": "2026-05-11T22:25:49.627791+00:00",
            "parsed_pdf_or_probability_fields": None
        }
        dist = convert_hourly_to_daily_max(res)
        self.assertIn("Missing probability/PDF fields", dist["warnings"])
        self.assertEqual(dist["integer_probs"], {})

    def test_conversion_with_fixture(self):
        """Simple fixture-like hourly PDFs convert into normalized integer daily-max probability distribution."""
        fixture_data = {
            "station": "KMIA",
            "fetched_at_utc": "2026-05-11T22:25:49.627791+00:00",
            "parsed_pdf_or_probability_fields": [
                {
                    "hour": "2026-05-11T12:00:00Z",
                    "probabilities": {"80": 0.5, "81": 0.5}
                },
                {
                    "hour": "2026-05-11T13:00:00Z",
                    "probabilities": {"81": 0.5, "82": 0.5}
                }
            ]
        }
        
        dist = convert_hourly_to_daily_max(fixture_data)
        
        self.assertEqual(dist["station"], "KMIA")
        self.assertEqual(dist["target_date"], "2026-05-11")
        self.assertTrue(len(dist["integer_probs"]) > 0)
        self.assertAlmostEqual(sum(dist["integer_probs"].values()), 1.0, places=3)
        self.assertIn("Scaffold approximation: assumed independent hourly distributions. Requires calibration.", dist["warnings"])

    def test_cdf_monotonicity(self):
        """CDF is monotonic and ends near 1.0."""
        probs = {80: 0.1, 81: 0.2, 82: 0.4, 83: 0.2, 84: 0.1}
        cdf = build_cdf(probs)
        
        # Monotonicity
        temps = sorted(cdf.keys())
        for i in range(1, len(temps)):
            self.assertTrue(cdf[temps[i]] >= cdf[temps[i-1]])
            
        # Ends near 1.0
        self.assertAlmostEqual(cdf[temps[-1]], 1.0, places=3)

    def test_snapshot_write(self):
        """Snapshot write path creation works."""
        dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {82: 1.0}
        }
        
        write_distribution_snapshot(dist, output_dir=self.test_output_dir)
        
        # Check files exist
        files = os.listdir(self.test_output_dir)
        self.assertTrue(any("latest_kmia_daily_max_distribution.json" in f for f in files))
        self.assertTrue(any("kmia_daily_max_distribution_2026-05-11_" in f for f in files))

    def test_no_fixed_kalshi_bins(self):
        """No fixed Kalshi bins are used."""
        fixture_data = {
            "station": "KMIA",
            "fetched_at_utc": "2026-05-11T22:25:49.627791+00:00",
            "parsed_pdf_or_probability_fields": [
                {
                    "hour": "2026-05-11T12:00:00Z",
                    "probabilities": {"80": 1.0}
                }
            ]
        }
        dist = convert_hourly_to_daily_max(fixture_data)
        
        for k in dist["integer_probs"].keys():
            self.assertIsInstance(k, int)

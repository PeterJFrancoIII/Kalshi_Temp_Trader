import unittest
import os
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from forecasting.kmia_distribution_blender import (
    blend_distributions,
    write_blended_distribution_snapshot
)

class TestKMIADistributionBlender(unittest.TestCase):

    def setUp(self):
        self.test_output_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_twc_only_valid(self):
        """TWC-only valid distribution passes through as blended output."""
        twc_dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {"80": 0.5, "81": 0.5}
        }
        
        res = blend_distributions(twc_dist=twc_dist)
        
        self.assertEqual(res["status"], "OK")
        self.assertEqual(res["source_primary"], "RAW_TWC")
        self.assertEqual(res["integer_probs"], {80: 0.5, 81: 0.5})

    def test_corrected_preferred_over_raw(self):
        """Corrected NWS/KMIA distribution is preferred over raw TWC."""
        twc_dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {"80": 1.0}
        }
        corrected_dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {"81": 1.0}
        }
        
        res = blend_distributions(twc_dist=twc_dist, corrected_twc_dist=corrected_dist)
        
        self.assertEqual(res["status"], "OK")
        self.assertEqual(res["source_primary"], "CORRECTED_TWC")
        self.assertEqual(res["integer_probs"], {81: 1.0})

    def test_nbm_blending(self):
        """NBM-like anchor blends with TWC and normalizes."""
        twc_dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {"80": 1.0}
        }
        nbm_dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {"81": 1.0}
        }
        
        res = blend_distributions(twc_dist=twc_dist, nbm_dist=nbm_dist)
        
        self.assertEqual(res["status"], "OK")
        # Expected: 0.7 * 80 + 0.3 * 81
        self.assertAlmostEqual(res["integer_probs"][80], 0.7, places=2)
        self.assertAlmostEqual(res["integer_probs"][81], 0.3, places=2)

    def test_hrrr_sea_breeze(self):
        """HRRR sea-breeze regime applies conservative cooling/tail adjustment with warning."""
        twc_dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {"80": 1.0}
        }
        hrrr_features = {"regime": "sea_breeze"}
        
        res = blend_distributions(twc_dist=twc_dist, hrrr_features=hrrr_features)
        
        self.assertEqual(res["status"], "OK")
        self.assertEqual(res["integer_probs"], {79: 1.0}) # Shifted by -1
        self.assertTrue(any("sea-breeze" in r for r in res["blend_reasons"]))

    def test_hrrr_offshore(self):
        """HRRR offshore/westerly regime applies conservative warming/tail adjustment with warning."""
        twc_dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {"80": 1.0}
        }
        hrrr_features = {"regime": "offshore"}
        
        res = blend_distributions(twc_dist=twc_dist, hrrr_features=hrrr_features)
        
        self.assertEqual(res["status"], "OK")
        self.assertEqual(res["integer_probs"], {81: 1.0}) # Shifted by +1
        self.assertTrue(any("offshore" in r for r in res["blend_reasons"]))

    def test_missing_all_sources(self):
        """Missing all sources outputs UNAVAILABLE and does not fake probabilities."""
        res = blend_distributions()
        self.assertEqual(res["status"], "UNAVAILABLE")
        self.assertEqual(res["integer_probs"], {})

    def test_cdf_monotonicity(self):
        """CDF is monotonic and probability mass sums near 1.0."""
        twc_dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {"80": 0.5, "81": 0.5}
        }
        res = blend_distributions(twc_dist=twc_dist)
        
        self.assertEqual(res["status"], "OK")
        self.assertAlmostEqual(res["probability_mass_sum"], 1.0, places=3)
        
        cdf = res["cdf"]
        temps = sorted(cdf.keys())
        for i in range(1, len(temps)):
            self.assertTrue(cdf[temps[i]] >= cdf[temps[i-1]])

    def test_no_fixed_kalshi_bins(self):
        """No fixed Kalshi bins are used."""
        twc_dist = {
            "station": "KMIA",
            "target_date": "2026-05-11",
            "integer_probs": {"80": 1.0}
        }
        res = blend_distributions(twc_dist=twc_dist)
        
        for k in res["integer_probs"].keys():
            self.assertIsInstance(k, int)

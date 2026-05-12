import unittest
from datetime import datetime
from dateutil import tz
from forecasting.kmia_observation_bias_corrector import correct_distribution


class TestKmiaObservationBiasCorrector(unittest.TestCase):

    def test_observed_max_truncation(self):
        """Probabilities below observed max are zeroed and renormalized."""
        dist = {
            "integer_probs": {85: 0.2, 86: 0.3, 87: 0.5},
            "cdf": {},
            "warnings": []
        }
        nws = {
            "observed_max_so_far_f": 86.4,  # Should zero temps < 86
            "stale_data": False,
            "wind_direction_compass": "N",
            "wind_speed_mph": 5.0,
            "current_temp_f": 86.0
        }
        dt = datetime(2026, 5, 11, 14, 0, tzinfo=tz.gettz("America/New_York"))

        corrected = correct_distribution(dist, nws, dt)

        self.assertEqual(corrected["integer_probs"][85], 0.0)
        # Remaining mass: 0.3 + 0.5 = 0.8  →  86: 0.375, 87: 0.625
        self.assertAlmostEqual(corrected["integer_probs"][86], 0.375, places=3)
        self.assertAlmostEqual(corrected["integer_probs"][87], 0.625, places=3)
        self.assertTrue(any("Truncated" in r for r in corrected["correction_reasons"]))

    def test_stale_observation_skips_heuristics(self):
        """Stale NWS data skips all speculative regime shifts."""
        dist = {
            "integer_probs": {85: 0.2, 86: 0.8},
            "warnings": []
        }
        nws = {
            "stale_data": True,
            "wind_direction_compass": "W",  # Would normally trigger +1F
            "wind_speed_mph": 10.0,
            "current_temp_f": 80.0
        }
        corrected = correct_distribution(dist, nws)

        self.assertEqual(corrected["integer_probs"][85], 0.2)
        self.assertEqual(corrected["integer_probs"][86], 0.8)
        self.assertTrue(any("Stale data flagged" in r for r in corrected["correction_reasons"]))
        self.assertIn("Stale NWS observations. Confidence downgraded.", corrected["warnings"])

    def test_sea_breeze_cooling_shift(self):
        """East wind above 8 mph applies -1F cooling shift."""
        dist = {
            "integer_probs": {85: 0.2, 86: 0.8},
            "warnings": []
        }
        nws = {
            "stale_data": False,
            "wind_direction_compass": "E",
            "wind_speed_mph": 10.0,
            "current_temp_f": 80.0
        }
        corrected = correct_distribution(dist, nws)

        self.assertIn(84, corrected["integer_probs"])
        self.assertAlmostEqual(corrected["integer_probs"][84], 0.2)
        self.assertAlmostEqual(corrected["integer_probs"][85], 0.8)
        self.assertNotIn(86, corrected["integer_probs"])
        self.assertTrue(any("sea-breeze cooling shift" in r for r in corrected["correction_reasons"]))

    def test_offshore_warming_shift(self):
        """West/southwest wind applies +1F warming shift."""
        dist = {
            "integer_probs": {85: 0.2, 86: 0.8},
            "warnings": []
        }
        nws = {
            "stale_data": False,
            "wind_direction_compass": "WSW",
            "wind_speed_mph": 10.0,
            "current_temp_f": 80.0
        }
        corrected = correct_distribution(dist, nws)

        self.assertIn(86, corrected["integer_probs"])
        self.assertAlmostEqual(corrected["integer_probs"][86], 0.2)
        self.assertAlmostEqual(corrected["integer_probs"][87], 0.8)
        self.assertNotIn(85, corrected["integer_probs"])
        self.assertTrue(any("offshore/westerly warming shift" in r for r in corrected["correction_reasons"]))

    def test_warm_ramp_morning(self):
        """High morning temperature (>=85 before 11h ET) applies +1F warm ramp."""
        dist = {
            "integer_probs": {85: 0.2, 86: 0.8},
            "warnings": []
        }
        nws = {
            "stale_data": False,
            "wind_direction_compass": "N",
            "wind_speed_mph": 5.0,
            "current_temp_f": 85.5
        }
        dt = datetime(2026, 5, 11, 10, 30, tzinfo=tz.gettz("America/New_York"))
        corrected = correct_distribution(dist, nws, dt)

        self.assertIn(86, corrected["integer_probs"])
        self.assertAlmostEqual(corrected["integer_probs"][86], 0.2)
        self.assertAlmostEqual(corrected["integer_probs"][87], 0.8)
        self.assertTrue(any("warm ramp shift" in r for r in corrected["correction_reasons"]))


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime
from forecasting.climatology_model import climatology_prior_for_date
from forecasting.rules_model_v2 import forecast_target_distribution, forecast_daily_high_bins_v2, apply_weather_suppression

class TestRulesModelV2(unittest.TestCase):

    def setUp(self):
        self.dummy_records = [
            {"date": "2020-05-01", "tmax_f": 82},
            {"date": "2020-05-02", "tmax_f": 85},
            {"date": "2021-05-01", "tmax_f": 81},
            {"date": "2021-05-02", "tmax_f": 87},
        ]

    def test_climatology_prior_structure(self):
        res = climatology_prior_for_date(self.dummy_records, "2026-05-01")
        bins = res["probability_bins"]
        self.assertEqual(len(bins), 6)
        self.assertAlmostEqual(sum(bins.values()), 1.0, places=3)

    def test_forecast_target_distribution_82(self):
        dist = forecast_target_distribution(82)
        # 82 is in "81-82"
        self.assertEqual(dist["81-82"], 0.55)
        # adjacent "79-80" and "83-84" should be 0.20
        self.assertEqual(dist["79-80"], 0.20)
        self.assertEqual(dist["83-84"], 0.20)
        self.assertAlmostEqual(sum(dist.values()), 1.0, places=3)

    def test_forecast_target_distribution_85(self):
        dist = forecast_target_distribution(85)
        # 85 is in "85-86"
        self.assertEqual(dist["85-86"], 0.55)
        self.assertAlmostEqual(sum(dist.values()), 1.0, places=3)

    def test_observed_max_zeroing_82(self):
        input_features = {
            "target_date": "2026-05-01",
            "observed_max_so_far_f": 82,
            "forecast_high_f": 84
        }
        res = forecast_daily_high_bins_v2(input_features, self.dummy_records)
        bins = res["probability_bins"]
        self.assertEqual(bins["<=78"], 0.0)
        self.assertEqual(bins["79-80"], 0.0)
        self.assertGreater(bins["81-82"], 0.0)
        self.assertAlmostEqual(sum(bins.values()), 1.0, places=3)

    def test_observed_max_zeroing_85(self):
        input_features = {
            "target_date": "2026-05-01",
            "observed_max_so_far_f": 85,
            "forecast_high_f": 84
        }
        res = forecast_daily_high_bins_v2(input_features, self.dummy_records)
        bins = res["probability_bins"]
        self.assertEqual(bins["<=78"], 0.0)
        self.assertEqual(bins["79-80"], 0.0)
        self.assertEqual(bins["81-82"], 0.0)
        self.assertEqual(bins["83-84"], 0.0)
        self.assertGreater(bins["85-86"], 0.0)

    def test_thunderstorm_suppression(self):
        base_bins = {b: 1.0/6.0 for b in ["<=78", "79-80", "81-82", "83-84", "85-86", ">=87"]}
        storm_bins = apply_weather_suppression(base_bins, False, True, False)
        # Thunderstorm moves mass from >=87, 85-86, 83-84
        self.assertLess(storm_bins[">=87"], base_bins[">=87"])
        self.assertLess(storm_bins["85-86"], base_bins["85-86"])
        self.assertLess(storm_bins["83-84"], base_bins["83-84"])
        self.assertAlmostEqual(sum(storm_bins.values()), 1.0, places=3)

    def test_missing_forecast_high(self):
        input_features = {
            "target_date": "2026-05-01",
            "observed_max_so_far_f": 75
        }
        res = forecast_daily_high_bins_v2(input_features, self.dummy_records)
        # Check if any warning contains the substring
        self.assertTrue(any("forecast_high_f is missing" in w for w in res["warnings"]))
        self.assertEqual(len(res["probability_bins"]), 6)
        self.assertAlmostEqual(sum(res["probability_bins"].values()), 1.0, places=3)

    def test_missing_history(self):
        input_features = {
            "target_date": "2026-05-01",
            "observed_max_so_far_f": 75,
            "forecast_high_f": 82
        }
        res = forecast_daily_high_bins_v2(input_features, [])
        self.assertTrue(any("Climatology lead unavailable" in w for w in res["warnings"]))
        self.assertEqual(len(res["probability_bins"]), 6)
        self.assertAlmostEqual(sum(res["probability_bins"].values()), 1.0, places=3)

    def test_model_version_string(self):
        input_features = {
            "target_date": "2026-05-01",
            "observed_max_so_far_f": 75,
            "forecast_high_f": 82
        }
        res = forecast_daily_high_bins_v2(input_features, self.dummy_records)
        self.assertEqual(res["model_version"], "rules_v2_climatology")

    def test_probability_sum_always_one(self):
        # Stress test with various inputs
        for f in [75, 82, 90]:
            for obs in [0, 80, 88]:
                input_features = {
                    "target_date": "2026-05-01",
                    "observed_max_so_far_f": obs,
                    "forecast_high_f": f,
                    "thunderstorm_flag": True
                }
                res = forecast_daily_high_bins_v2(input_features, self.dummy_records)
                self.assertAlmostEqual(sum(res["probability_bins"].values()), 1.0, places=2)

if __name__ == '__main__':
    unittest.main()

import unittest
from forecasting.distribution_utils import (
    build_integer_distribution,
    integer_dist_to_fixed_bins,
    zero_impossible_temps,
    shift_distribution,
    apply_weather_suppression_integer,
    normalize_probability_mass,
    build_cdf,
    compute_percentile,
)


class TestDistributionUtils(unittest.TestCase):

    # ------------------------------------------------------------------
    # build_integer_distribution
    # ------------------------------------------------------------------

    def test_build_integer_distribution_sums_to_one(self):
        dist = build_integer_distribution(center_f=85)
        self.assertAlmostEqual(sum(dist.values()), 1.0, places=4)

    def test_build_integer_distribution_keys_are_integers(self):
        dist = build_integer_distribution(center_f=82)
        for k in dist.keys():
            self.assertIsInstance(k, int)

    def test_build_integer_distribution_center_has_highest_mass(self):
        center = 83
        dist = build_integer_distribution(center_f=center, std_f=2.0)
        peak = max(dist, key=dist.get)
        self.assertEqual(peak, center)

    def test_build_integer_distribution_respects_temp_range(self):
        dist = build_integer_distribution(center_f=80, temp_range=(78, 84))
        self.assertTrue(all(78 <= t <= 84 for t in dist.keys()))

    def test_build_integer_distribution_non_empty(self):
        dist = build_integer_distribution(center_f=90)
        self.assertGreater(len(dist), 0)

    # ------------------------------------------------------------------
    # integer_dist_to_fixed_bins
    # ------------------------------------------------------------------

    def test_integer_dist_to_fixed_bins_all_labels_present(self):
        dist = {82: 0.5, 83: 0.5}
        bins = integer_dist_to_fixed_bins(dist)
        expected_labels = {"<=78", "79-80", "81-82", "83-84", "85-86", ">=87"}
        self.assertEqual(set(bins.keys()), expected_labels)

    def test_integer_dist_to_fixed_bins_correct_buckets(self):
        dist = {78: 0.2, 80: 0.3, 82: 0.2, 84: 0.1, 86: 0.1, 90: 0.1}
        bins = integer_dist_to_fixed_bins(dist)
        self.assertAlmostEqual(bins["<=78"], 0.2, places=5)
        self.assertAlmostEqual(bins["79-80"], 0.3, places=5)
        self.assertAlmostEqual(bins["81-82"], 0.2, places=5)
        self.assertAlmostEqual(bins["83-84"], 0.1, places=5)
        self.assertAlmostEqual(bins["85-86"], 0.1, places=5)
        self.assertAlmostEqual(bins[">=87"], 0.1, places=5)

    def test_integer_dist_to_fixed_bins_preserves_total_mass(self):
        dist = build_integer_distribution(center_f=84, std_f=3.0)
        bins = integer_dist_to_fixed_bins(dist)
        self.assertAlmostEqual(sum(bins.values()), sum(dist.values()), places=3)

    def test_integer_dist_to_fixed_bins_boundary_78(self):
        """Temperature 78 falls in <=78 bin."""
        bins = integer_dist_to_fixed_bins({78: 1.0})
        self.assertAlmostEqual(bins["<=78"], 1.0, places=5)

    def test_integer_dist_to_fixed_bins_boundary_87(self):
        """Temperature 87 falls in >=87 bin."""
        bins = integer_dist_to_fixed_bins({87: 1.0})
        self.assertAlmostEqual(bins[">=87"], 1.0, places=5)

    # ------------------------------------------------------------------
    # zero_impossible_temps
    # ------------------------------------------------------------------

    def test_zero_impossible_temps_removes_below_min(self):
        dist = {80: 0.2, 82: 0.3, 85: 0.5}
        result = zero_impossible_temps(dist, observed_min_f=82)
        self.assertEqual(result[80], 0.0)
        self.assertGreater(result[82], 0.0)
        self.assertGreater(result[85], 0.0)

    def test_zero_impossible_temps_renormalizes(self):
        dist = {80: 0.5, 85: 0.5}
        result = zero_impossible_temps(dist, observed_min_f=85)
        self.assertAlmostEqual(sum(result.values()), 1.0, places=4)
        self.assertAlmostEqual(result[85], 1.0, places=4)

    def test_zero_impossible_temps_no_op_when_min_is_zero(self):
        dist = {80: 0.4, 85: 0.6}
        result = zero_impossible_temps(dist, observed_min_f=0)
        self.assertAlmostEqual(result[80], 0.4, places=4)
        self.assertAlmostEqual(result[85], 0.6, places=4)

    # ------------------------------------------------------------------
    # shift_distribution
    # ------------------------------------------------------------------

    def test_shift_distribution_positive(self):
        dist = {80: 0.4, 82: 0.6}
        shifted = shift_distribution(dist, shift_f=2)
        self.assertIn(82, shifted)
        self.assertIn(84, shifted)
        self.assertAlmostEqual(shifted[82], 0.4, places=5)
        self.assertAlmostEqual(shifted[84], 0.6, places=5)

    def test_shift_distribution_negative(self):
        dist = {85: 1.0}
        shifted = shift_distribution(dist, shift_f=-3)
        self.assertAlmostEqual(shifted[82], 1.0, places=5)

    def test_shift_distribution_zero(self):
        dist = {83: 0.5, 84: 0.5}
        shifted = shift_distribution(dist, shift_f=0)
        self.assertEqual(shifted, dist)

    # ------------------------------------------------------------------
    # apply_weather_suppression_integer
    # ------------------------------------------------------------------

    def test_suppression_thunderstorm_shifts_minus_2(self):
        dist = {85: 1.0}
        result = apply_weather_suppression_integer(
            dist, thunderstorm_flag=True, recent_rain_flag=False, overcast_flag=False
        )
        self.assertAlmostEqual(result[83], 1.0, places=5)

    def test_suppression_rain_shifts_minus_1(self):
        dist = {85: 1.0}
        result = apply_weather_suppression_integer(
            dist, thunderstorm_flag=False, recent_rain_flag=True, overcast_flag=False
        )
        self.assertAlmostEqual(result[84], 1.0, places=5)

    def test_suppression_overcast_shifts_minus_1(self):
        dist = {85: 1.0}
        result = apply_weather_suppression_integer(
            dist, thunderstorm_flag=False, recent_rain_flag=False, overcast_flag=True
        )
        self.assertAlmostEqual(result[84], 1.0, places=5)

    def test_suppression_no_flags_no_change(self):
        dist = {85: 0.6, 86: 0.4}
        result = apply_weather_suppression_integer(
            dist, thunderstorm_flag=False, recent_rain_flag=False, overcast_flag=False
        )
        self.assertEqual(result, dist)

    def test_suppression_thunderstorm_takes_priority(self):
        """Thunderstorm flag overrides rain flag (-2 not -1)."""
        dist = {85: 1.0}
        result = apply_weather_suppression_integer(
            dist, thunderstorm_flag=True, recent_rain_flag=True, overcast_flag=False
        )
        self.assertAlmostEqual(result[83], 1.0, places=5)

    # ------------------------------------------------------------------
    # build_cdf / compute_percentile
    # ------------------------------------------------------------------

    def test_build_cdf_monotonic(self):
        dist = {80: 0.1, 81: 0.2, 82: 0.4, 83: 0.2, 84: 0.1}
        cdf = build_cdf(dist)
        temps = sorted(cdf.keys())
        for i in range(1, len(temps)):
            self.assertGreaterEqual(cdf[temps[i]], cdf[temps[i - 1]])
        self.assertAlmostEqual(cdf[temps[-1]], 1.0, places=3)

    def test_compute_percentile_p50(self):
        dist = {80: 0.5, 81: 0.5}
        cdf = build_cdf(dist)
        p50 = compute_percentile(cdf, 0.50)
        self.assertEqual(p50, 80)

    def test_compute_percentile_p100(self):
        dist = {80: 0.3, 82: 0.7}
        cdf = build_cdf(dist)
        p100 = compute_percentile(cdf, 1.0)
        self.assertEqual(p100, 82)

    # ------------------------------------------------------------------
    # End-to-end: rules_model_v2 integer_distribution field
    # ------------------------------------------------------------------

    def test_rules_model_v2_produces_integer_distribution(self):
        """forecast_daily_high_bins_v2 now includes integer_distribution in output."""
        from forecasting.rules_model_v2 import forecast_daily_high_bins_v2
        result = forecast_daily_high_bins_v2(
            {"target_date": "2026-05-11", "forecast_high_f": 85, "observed_max_so_far_f": 0}
        )
        self.assertIn("integer_distribution", result)
        int_dist = result["integer_distribution"]
        self.assertIsInstance(int_dist, dict)
        self.assertGreater(len(int_dist), 0)
        self.assertAlmostEqual(sum(int_dist.values()), 1.0, places=3)
        for k in int_dist.keys():
            self.assertIsInstance(k, int)

    def test_rules_model_v2_integer_dist_respects_observed_max(self):
        """integer_distribution has zero probability below observed_max_so_far_f."""
        from forecasting.rules_model_v2 import forecast_daily_high_bins_v2
        result = forecast_daily_high_bins_v2(
            {"target_date": "2026-05-11", "forecast_high_f": 85, "observed_max_so_far_f": 84}
        )
        int_dist = result["integer_distribution"]
        for t, p in int_dist.items():
            if t < 84:
                self.assertAlmostEqual(p, 0.0, places=5,
                                       msg=f"Temp {t} should have zero probability (obs max=84)")

    def test_rules_model_v2_thunderstorm_shifts_integer_dist(self):
        """Thunderstorm flag cools the integer distribution."""
        from forecasting.rules_model_v2 import forecast_daily_high_bins_v2
        res_clear = forecast_daily_high_bins_v2(
            {"target_date": "2026-05-11", "forecast_high_f": 86, "thunderstorm_flag": False}
        )
        res_storm = forecast_daily_high_bins_v2(
            {"target_date": "2026-05-11", "forecast_high_f": 86, "thunderstorm_flag": True}
        )
        peak_clear = max(res_clear["integer_distribution"], key=res_clear["integer_distribution"].get)
        peak_storm = max(res_storm["integer_distribution"], key=res_storm["integer_distribution"].get)
        self.assertLess(peak_storm, peak_clear, "Thunderstorm should cool the distribution peak")


if __name__ == "__main__":
    unittest.main()

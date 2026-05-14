import unittest
from forecasting.distribution_utils import (
    shift_distribution_fractional,
    apply_weather_suppression_integer,
    normalize_probability_mass
)

class TestGradedSuppression(unittest.TestCase):

    def test_shift_distribution_fractional_half_degree(self):
        # 100% at 90, shift by -0.5
        dist = {90: 1.0}
        shifted = shift_distribution_fractional(dist, -0.5)
        # Expected: 0.5 at 89, 0.5 at 90
        self.assertAlmostEqual(shifted.get(89, 0.0), 0.5, places=5)
        self.assertAlmostEqual(shifted.get(90, 0.0), 0.5, places=5)
        self.assertEqual(len(shifted), 2)

    def test_shift_distribution_fractional_one_and_half_degree(self):
        # 100% at 90, shift by -1.5
        dist = {90: 1.0}
        shifted = shift_distribution_fractional(dist, -1.5)
        # Expected: 0.5 at 88, 0.5 at 89
        self.assertAlmostEqual(shifted.get(88, 0.0), 0.5, places=5)
        self.assertAlmostEqual(shifted.get(89, 0.0), 0.5, places=5)
        self.assertEqual(len(shifted), 2)

    def test_apply_weather_suppression_slight_chance(self):
        dist = {90: 1.0}
        # Slight chance -> -0.5 shift
        result = apply_weather_suppression_integer(dist, thunderstorm_severity="slight chance")
        self.assertAlmostEqual(result.get(89, 0.0), 0.5, places=5)
        self.assertAlmostEqual(result.get(90, 0.0), 0.5, places=5)

    def test_apply_weather_suppression_chance(self):
        dist = {90: 1.0}
        # Chance -> -1.0 shift
        result = apply_weather_suppression_integer(dist, thunderstorm_severity="chance")
        self.assertAlmostEqual(result.get(89, 0.0), 1.0, places=5)
        self.assertEqual(len(result), 1)

    def test_apply_weather_suppression_likely(self):
        dist = {90: 1.0}
        # Likely -> -2.0 shift
        result = apply_weather_suppression_integer(dist, thunderstorm_severity="likely")
        self.assertAlmostEqual(result.get(88, 0.0), 1.0, places=5)

    def test_apply_weather_suppression_isolated(self):
        dist = {90: 1.0}
        # Isolated -> -0.5 shift (mapped same as slight)
        result = apply_weather_suppression_integer(dist, thunderstorm_severity="isolated thunderstorms")
        self.assertAlmostEqual(result.get(89, 0.0), 0.5, places=5)

    def test_apply_weather_suppression_scattered(self):
        dist = {90: 1.0}
        # Scattered -> -1.0 shift (mapped same as chance)
        result = apply_weather_suppression_integer(dist, thunderstorm_severity="scattered thunderstorms")
        self.assertAlmostEqual(result.get(89, 0.0), 1.0, places=5)

    def test_apply_weather_suppression_fallback_to_rain(self):
        dist = {90: 1.0}
        # No thunderstorm, but rain flag set -> -1.0 shift
        result = apply_weather_suppression_integer(dist, recent_rain_flag=True)
        self.assertAlmostEqual(result.get(89, 0.0), 1.0, places=5)

if __name__ == "__main__":
    unittest.main()

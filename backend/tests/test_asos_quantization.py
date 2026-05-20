import unittest
from datetime import datetime, timezone, timedelta
from forecasting.asos_quantization import (
    is_celsius_quantized_fahrenheit,
    rh_from_temp_dewpoint,
    temperature_from_dewpoint_rh,
    infer_latent_temperature_from_rh,
    apply_latent_observation_adjustment,
    normalize_row
)

class TestASOSQuantization(unittest.TestCase):

    def test_is_celsius_quantized_fahrenheit(self):
        # Celsius whole numbers in Fahrenheit:
        # 31C = 87.8F
        # 30C = 86.0F
        # 29C = 84.2F
        self.assertTrue(is_celsius_quantized_fahrenheit(87.8))
        self.assertTrue(is_celsius_quantized_fahrenheit(86.0))
        self.assertTrue(is_celsius_quantized_fahrenheit(84.2))
        
        # Non-quantized values
        self.assertFalse(is_celsius_quantized_fahrenheit(87.0))
        self.assertFalse(is_celsius_quantized_fahrenheit(87.5))
        self.assertFalse(is_celsius_quantized_fahrenheit(88.0))
        self.assertFalse(is_celsius_quantized_fahrenheit(None))

    def test_psychrometric_conversions(self):
        # T = 86.0F (30C), Td = 68.0F (20C) -> RH ~ 55%
        rh = rh_from_temp_dewpoint(86.0, 68.0)
        self.assertIsNotNone(rh)
        self.assertTrue(54.0 <= rh <= 56.0)
        
        # Recover temperature from dewpoint and RH
        temp = temperature_from_dewpoint_rh(68.0, rh)
        self.assertIsNotNone(temp)
        self.assertTrue(85.8 <= temp <= 86.2)
        
        # Edge cases
        self.assertIsNone(rh_from_temp_dewpoint(None, 68.0))
        self.assertIsNone(temperature_from_dewpoint_rh(None, 55.0))
        self.assertIsNone(temperature_from_dewpoint_rh(68.0, 0.0))

    def test_infer_latent_temperature_no_signal(self):
        # Empty rows
        res = infer_latent_temperature_from_rh([])
        self.assertEqual(res["rh_tiebreaker_signal"], "NO_SIGNAL")
        
        # Temperature not flat
        base_time = datetime(2026, 5, 20, 14, 0, 0, tzinfo=timezone.utc)
        rows = [
            {"time_utc": (base_time - timedelta(minutes=10)).isoformat(), "air_temp_f": 86.0, "relative_humidity_pct": 59.0},
            {"time_utc": (base_time - timedelta(minutes=5)).isoformat(), "air_temp_f": 87.0, "relative_humidity_pct": 57.0},
            {"time_utc": base_time.isoformat(), "air_temp_f": 87.8, "relative_humidity_pct": 55.0}
        ]
        res = infer_latent_temperature_from_rh(rows)
        self.assertEqual(res["rh_tiebreaker_signal"], "NO_SIGNAL")
        
        # Too few observations
        rows_few = [
            {"time_utc": base_time.isoformat(), "air_temp_f": 87.8, "relative_humidity_pct": 55.0}
        ]
        res = infer_latent_temperature_from_rh(rows_few)
        self.assertEqual(res["rh_tiebreaker_signal"], "NO_SIGNAL")

    def test_infer_latent_temperature_warming_signal_no_dewpoint(self):
        # Quantized flat temperature, dropping RH, stable wind/pressure, peak heating
        base_time = datetime(2026, 5, 20, 15, 0, 0, tzinfo=timezone.utc)
        rows = [
            {
                "time_utc": (base_time - timedelta(minutes=15)).isoformat(),
                "temperature_f": 87.8,
                "relative_humidity": 58.89,
                "wind_direction": 90,
                "pressure": 1017.5
            },
            {
                "time_utc": (base_time - timedelta(minutes=10)).isoformat(),
                "temperature_f": 87.8,
                "relative_humidity": 57.0,
                "wind_direction": 95,
                "pressure": 1017.5
            },
            {
                "time_utc": (base_time - timedelta(minutes=5)).isoformat(),
                "temperature_f": 87.8,
                "relative_humidity": 56.0,
                "wind_direction": 92,
                "pressure": 1017.4
            },
            {
                "time_utc": base_time.isoformat(),
                "temperature_f": 87.8,
                "relative_humidity": 55.4,
                "wind_direction": 90,
                "pressure": 1017.5
            }
        ]
        # Run inference in America/New_York (base_time is 15:00 UTC, which is 11:00 AM ET)
        res = infer_latent_temperature_from_rh(rows, station_tz="America/New_York")
        self.assertEqual(res["rh_tiebreaker_signal"], "LIKELY_UPPER_BUCKET_WARMING")
        self.assertEqual(res["confidence"], "medium") # No dewpoint, so medium confidence
        self.assertTrue(res["quantization_warning"])
        self.assertEqual(res["reported_observed_max_f"], 87.8)
        self.assertEqual(res["latent_observed_max_floor_f"], 88.0)
        self.assertEqual(res["latent_observed_max_inferred_f"], 88.3) # Fallback to temp + 0.5 (rounded to 2 decimals)
        self.assertEqual(res["latent_boundary_touch_probability"], 0.35)

    def test_infer_latent_temperature_warming_signal_with_stable_dewpoint(self):
        # Flat temperature at 87.8F (31.0C).
        # Dewpoint is stable at 68.0F (20.0C).
        # RH drops from 58.89% to 55.4%.
        # Let's calculate:
        # T_implied at RH 58.89% & Td 68.0F -> ~83.9F
        # T_implied at RH 55.4% & Td 68.0F -> ~85.8F
        # (This is just a mock setup, let's provide realistic values)
        base_time = datetime(2026, 5, 20, 16, 0, 0, tzinfo=timezone.utc) # 12:00 PM ET
        rows = [
            {
                "time_utc": (base_time - timedelta(minutes=15)).isoformat(),
                "temperature_f": 87.8,
                "dewpoint_f": 70.0,
                "relative_humidity": 58.89,
                "wind_direction": 90,
                "pressure": 1017.5
            },
            {
                "time_utc": base_time.isoformat(),
                "temperature_f": 87.8,
                "dewpoint_f": 70.0,
                "relative_humidity": 55.4,
                "wind_direction": 90,
                "pressure": 1017.5
            }
        ]
        # We need at least min_flat_observations=3. Let's add a middle observation.
        rows.insert(1, {
            "time_utc": (base_time - timedelta(minutes=8)).isoformat(),
            "temperature_f": 87.8,
            "dewpoint_f": 70.0,
            "relative_humidity": 57.0,
            "wind_direction": 92,
            "pressure": 1017.5
        })
        
        res = infer_latent_temperature_from_rh(rows, station_tz="America/New_York")
        self.assertEqual(res["rh_tiebreaker_signal"], "LIKELY_UPPER_BUCKET_WARMING")
        self.assertEqual(res["confidence"], "high") # Stable dewpoint, peak heating -> high confidence
        self.assertTrue(res["latent_observed_max_inferred_f"] > 87.8)
        self.assertEqual(res["latent_boundary_touch_probability"], 0.65)

    def test_infer_latent_temperature_dewpoint_drop_advection(self):
        # Flat temperature, but dewpoint drops significantly (drying, not warming)
        base_time = datetime(2026, 5, 20, 16, 0, 0, tzinfo=timezone.utc)
        rows = [
            {
                "time_utc": (base_time - timedelta(minutes=15)).isoformat(),
                "temperature_f": 87.8,
                "dewpoint_f": 70.0,
                "relative_humidity": 58.89,
                "wind_direction": 90,
                "pressure": 1017.5
            },
            {
                "time_utc": (base_time - timedelta(minutes=8)).isoformat(),
                "temperature_f": 87.8,
                "dewpoint_f": 69.0,
                "relative_humidity": 57.0,
                "wind_direction": 90,
                "pressure": 1017.5
            },
            {
                "time_utc": base_time.isoformat(),
                "temperature_f": 87.8,
                "dewpoint_f": 67.5, # Dewpoint drops by 2.5F
                "relative_humidity": 55.4,
                "wind_direction": 90,
                "pressure": 1017.5
            }
        ]
        res = infer_latent_temperature_from_rh(rows)
        self.assertEqual(res["rh_tiebreaker_signal"], "DEWPOINT_DROP")
        self.assertEqual(res["confidence"], "none")

    def test_apply_latent_observation_adjustment(self):
        # A simple integer distribution centered around 88F
        dist = {
            86: 0.05,
            87: 0.15,
            88: 0.40,
            89: 0.25,
            90: 0.15
        }
        
        # Test shift under LIKELY_UPPER_BUCKET_WARMING with medium confidence (alpha = 0.15)
        inference = {
            "reported_observed_max_f": 87.8,
            "rh_tiebreaker_signal": "LIKELY_UPPER_BUCKET_WARMING",
            "confidence": "medium",
            "latent_boundary_touch_probability": 0.35
        }
        
        # Target boundary = floor(87.8) + 1 = 88.
        # We shift:
        # - 15% of mass from 88 to 89: 0.40 * 0.15 = 0.06 shifted. 88 becomes 0.34, 89 gains 0.06.
        # - 15% of mass from 87 to 88: 0.15 * 0.15 = 0.0225 shifted. 87 becomes 0.1275, 88 gains 0.0225.
        # Total sum of probabilities must remain 1.0.
        adjusted = apply_latent_observation_adjustment(dist, inference)
        self.assertTrue(abs(sum(adjusted.values()) - 1.0) < 1e-6)
        
        # Check specific values
        self.assertAlmostEqual(adjusted[87], 0.1275 / sum(adjusted.values()))
        # 88 should have: (0.40 - 0.06 + 0.0225) / total = 0.3625
        self.assertAlmostEqual(adjusted[88], 0.3625 / sum(adjusted.values()))
        # 89 should have: (0.25 + 0.06) / total = 0.31
        self.assertAlmostEqual(adjusted[89], 0.31 / sum(adjusted.values()))
        
        # Test no shift if signal is missing or different
        inference_none = {
            "reported_observed_max_f": 87.8,
            "rh_tiebreaker_signal": "NO_SIGNAL",
            "confidence": "none"
        }
        self.assertEqual(apply_latent_observation_adjustment(dist, inference_none), dist)

    def test_infer_latent_temperature_stable_rh(self):
        # Flat temperature, stable RH (58.89% throughout)
        base_time = datetime(2026, 5, 20, 16, 0, 0, tzinfo=timezone.utc)
        rows = [
            {"time_utc": (base_time - timedelta(minutes=10)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89},
            {"time_utc": (base_time - timedelta(minutes=5)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89},
            {"time_utc": base_time.isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89}
        ]
        res = infer_latent_temperature_from_rh(rows)
        self.assertIn(res["rh_tiebreaker_signal"], ["NO_SIGNAL", "AMBIGUOUS"])
        self.assertEqual(res["latent_boundary_touch_probability"], 0.0)

    def test_infer_latent_temperature_wind_or_qc_suppression(self):
        base_time = datetime(2026, 5, 20, 16, 0, 0, tzinfo=timezone.utc)
        # Wind shift (90 deg to 180 deg) suppresses the warming signal
        rows_wind = [
            {"time_utc": (base_time - timedelta(minutes=10)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89, "wind_direction": 90, "pressure": 1017.5},
            {"time_utc": (base_time - timedelta(minutes=5)).isoformat(), "temperature_f": 87.8, "relative_humidity": 57.0, "wind_direction": 130, "pressure": 1017.5},
            {"time_utc": base_time.isoformat(), "temperature_f": 87.8, "relative_humidity": 55.4, "wind_direction": 180, "pressure": 1017.5}
        ]
        res_wind = infer_latent_temperature_from_rh(rows_wind)
        self.assertEqual(res_wind["rh_tiebreaker_signal"], "AMBIGUOUS")
        self.assertEqual(res_wind["latent_boundary_touch_probability"], 0.0)

        # QC flag present downgrades confidence to low
        rows_qc = [
            {"time_utc": (base_time - timedelta(minutes=10)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89, "wind_direction": 90, "pressure": 1017.5},
            {"time_utc": (base_time - timedelta(minutes=5)).isoformat(), "temperature_f": 87.8, "relative_humidity": 57.0, "wind_direction": 90, "pressure": 1017.5},
            {"time_utc": base_time.isoformat(), "temperature_f": 87.8, "relative_humidity": 55.4, "wind_direction": 90, "pressure": 1017.5, "qc_flags": ["T_ERR"]}
        ]
        res_qc = infer_latent_temperature_from_rh(rows_qc, station_tz="America/New_York")
        self.assertEqual(res_qc["rh_tiebreaker_signal"], "LIKELY_UPPER_BUCKET_WARMING")
        self.assertEqual(res_qc["confidence"], "low") # Downgraded due to QC issues
        self.assertEqual(res_qc["latent_boundary_touch_probability"], 0.15)

    def test_infer_latent_temperature_flat_rh_example(self):
        # User's flat RH example:
        # - 18:00 UTC: 87.8°F, RH 58.89
        # - 17:55 UTC: 87.8°F, RH 58.89
        # - 17:50 UTC: 87.8°F, RH 58.89
        base_time = datetime(2026, 5, 20, 18, 0, 0, tzinfo=timezone.utc)
        rows = [
            {"time_utc": (base_time - timedelta(minutes=10)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89, "wind_direction": 90, "pressure": 1017.5},
            {"time_utc": (base_time - timedelta(minutes=5)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89, "wind_direction": 90, "pressure": 1017.5},
            {"time_utc": base_time.isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89, "wind_direction": 90, "pressure": 1017.5}
        ]
        res = infer_latent_temperature_from_rh(rows)
        self.assertEqual(res["rh_tiebreaker_signal"], "NO_SIGNAL")
        self.assertEqual(res["latent_boundary_touch_probability"], 0.0)

    def test_infer_latent_temperature_user_warming_example(self):
        # User's warming example:
        # - 17:05 UTC: 87.8°F, RH 58.89
        # - 17:10 UTC: 87.8°F, RH 55.40
        # Let's add a 17:00 UTC baseline observation to satisfy min_flat_observations=3
        base_time = datetime(2026, 5, 20, 17, 10, 0, tzinfo=timezone.utc)
        rows = [
            {"time_utc": (base_time - timedelta(minutes=10)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89, "wind_direction": 90, "pressure": 1017.5},
            {"time_utc": (base_time - timedelta(minutes=5)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89, "wind_direction": 90, "pressure": 1017.5},
            {"time_utc": base_time.isoformat(), "temperature_f": 87.8, "relative_humidity": 55.40, "wind_direction": 90, "pressure": 1017.5}
        ]
        res = infer_latent_temperature_from_rh(rows, station_tz="America/New_York")
        self.assertEqual(res["rh_tiebreaker_signal"], "LIKELY_UPPER_BUCKET_WARMING")
        self.assertTrue(res["latent_boundary_touch_probability"] > 0.0)

    def test_apply_latent_observation_adjustment_local_only(self):
        dist = {
            84: 0.10,
            85: 0.10,
            86: 0.10,
            87: 0.20,
            88: 0.30,
            89: 0.10,
            90: 0.05,
            91: 0.05
        }
        inference = {
            "reported_observed_max_f": 87.8,
            "rh_tiebreaker_signal": "LIKELY_UPPER_BUCKET_WARMING",
            "confidence": "medium",
            "latent_boundary_touch_probability": 0.35
        }
        # Target boundary = 88.
        # Adjusted bins should be localized to target_boundary (88), next (89) and prev (87).
        # Bins far away (84, 85, 86, 90, 91) should remain in the same proportion relative to each other.
        adjusted = apply_latent_observation_adjustment(dist, inference)
        
        # Verify normalization sum is ~1.0
        self.assertAlmostEqual(sum(adjusted.values()), 1.0)
        
        # Check that distant bins are unmodified or only scaled by renormalization
        # Relative ratio between 84 and 85 should remain exactly 1.0
        self.assertAlmostEqual(adjusted[84] / adjusted[85], 1.0)
        self.assertAlmostEqual(adjusted[90] / adjusted[91], 1.0)

    def test_rules_model_v2_integration(self):
        from forecasting.rules_model_v2 import forecast_daily_high_bins_v2
        
        # Define mock inputs
        base_time = datetime(2026, 5, 20, 16, 0, 0, tzinfo=timezone.utc)
        recent_obs = [
            {"time_utc": (base_time - timedelta(minutes=10)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89, "wind_direction": 90, "pressure": 1017.5},
            {"time_utc": (base_time - timedelta(minutes=5)).isoformat(), "temperature_f": 87.8, "relative_humidity": 58.89, "wind_direction": 90, "pressure": 1017.5},
            {"time_utc": base_time.isoformat(), "temperature_f": 87.8, "relative_humidity": 55.4, "wind_direction": 90, "pressure": 1017.5}
        ]
        
        input_features = {
            "observed_max_so_far_f": 87.8,
            "current_temp_f": 87.8,
            "forecast_high_f": 89,
            "target_date": "2026-05-20",
            "recent_observations": recent_obs
        }
        
        res = forecast_daily_high_bins_v2(input_features)
        
        # Verify that latent_inference was run and included in metadata
        self.assertIsNotNone(res.get("latent_inference"))
        self.assertEqual(res["latent_inference"]["rh_tiebreaker_signal"], "LIKELY_UPPER_BUCKET_WARMING")
        
        # Verify driver explanation was added
        self.assertTrue(any("relative humidity tie-breaker" in d for d in res["main_drivers"]))
        self.assertTrue(any("Celsius quantization detected" in w for w in res["warnings"]))

if __name__ == "__main__":
    unittest.main()

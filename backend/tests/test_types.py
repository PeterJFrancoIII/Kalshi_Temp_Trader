import unittest
from datetime import date, datetime
from shared.types import (
    TemperatureBins,
    DailyPrediction,
    ClimiaReport,
    LiveObservation,
    ForecastSnapshot,
    KalshiMarketSnapshot,
    Recommendation,
    WeatherSnapshot,
)
from pydantic import ValidationError

class TestTypes(unittest.TestCase):

    def test_temperature_bins_valid(self):
        valid_bins = {
            "<=78": 0.05,
            "79-80": 0.10,
            "81-82": 0.40,
            "83-84": 0.35,
            "85-86": 0.08,
            ">=87": 0.02
        }
        tb = TemperatureBins(bins=valid_bins)
        self.assertEqual(tb.bins["81-82"], 0.40)

    def test_temperature_bins_missing_required(self):
        invalid_bins = {
            "<=78": 0.05,
            "79-80": 0.10,
            "81-82": 0.40,
            "83-84": 0.35,
            "85-86": 0.10,
        }
        with self.assertRaises(ValidationError) as context:
            TemperatureBins(bins=invalid_bins)
        self.assertIn("Missing required bin: >=87", str(context.exception))

    def test_temperature_bins_invalid_prob(self):
        invalid_bins = {
            "<=78": -0.05,
            "79-80": 0.15,
            "81-82": 0.40,
            "83-84": 0.35,
            "85-86": 0.10,
            ">=87": 0.05
        }
        with self.assertRaises(ValidationError) as context:
            TemperatureBins(bins=invalid_bins)
        self.assertIn("must be between 0 and 1", str(context.exception))

    def test_temperature_bins_invalid_sum(self):
        invalid_bins = {
            "<=78": 0.50,
            "79-80": 0.50,
            "81-82": 0.50,
            "83-84": 0.00,
            "85-86": 0.00,
            ">=87": 0.00
        }
        with self.assertRaises(ValidationError) as context:
            TemperatureBins(bins=invalid_bins)
        self.assertIn("Sum of probabilities must be approximately 1", str(context.exception))

    def test_daily_prediction_valid(self):
        dp = DailyPrediction(
            date=date(2026, 5, 3),
            best_single_number_f=82,
            probability_bins={
                "<=78": 0.0,
                "79-80": 0.0,
                "81-82": 0.5,
                "83-84": 0.5,
                "85-86": 0.0,
                ">=87": 0.0
            },
            observed_max_so_far_f=82,
            current_temp_f=81,
            forecast_high_f=83,
            confidence="high",
            main_drivers=["Looking good"]
        )
        self.assertEqual(dp.station, "KMIA")
        self.assertEqual(dp.metric, "daily_max_temperature_f")

    def test_daily_prediction_invalid_station(self):
        with self.assertRaises(ValidationError) as context:
            DailyPrediction(
                station="JFK",
                date=date(2026, 5, 3),
                best_single_number_f=82,
                probability_bins={
                    "<=78": 0.0, "79-80": 0.0, "81-82": 0.5,
                    "83-84": 0.5, "85-86": 0.0, ">=87": 0.0
                },
                observed_max_so_far_f=82,
                current_temp_f=81,
                forecast_high_f=83,
                confidence="high"
            )
        self.assertIn("Station must be KMIA", str(context.exception))

    def test_daily_prediction_invalid_metric(self):
        with self.assertRaises(ValidationError) as context:
            DailyPrediction(
                metric="daily_min_temperature_f",
                date=date(2026, 5, 3),
                best_single_number_f=82,
                probability_bins={
                    "<=78": 0.0, "79-80": 0.0, "81-82": 0.5,
                    "83-84": 0.5, "85-86": 0.0, ">=87": 0.0
                },
                observed_max_so_far_f=82,
                current_temp_f=81,
                forecast_high_f=83,
                confidence="high"
            )
        self.assertIn("Metric must be daily_max_temperature_f", str(context.exception))

    def test_climia_report(self):
        cr = ClimiaReport(
            date=date(2026, 5, 3),
            observed_max_f=85
        )
        self.assertEqual(cr.station, "KMIA")
        self.assertEqual(cr.observed_max_f, 85)

    def test_live_observation(self):
        lo = LiveObservation(
            timestamp=datetime.now(),
            observed_max_so_far_f=80,
            current_temp_f=79,
            remaining_daylight_hours=4.5
        )
        self.assertEqual(lo.station, "KMIA")

    def test_forecast_snapshot(self):
        fs = ForecastSnapshot(
            date=date(2026, 5, 3),
            forecast_high_f=88
        )
        self.assertEqual(fs.station, "KMIA")

    def test_kalshi_market_snapshot(self):
        km = KalshiMarketSnapshot(
            timestamp=datetime.now(),
            ticker="KXKMIA-260503",
            bin_prices={"81-82": 0.35}
        )
        self.assertEqual(km.ticker, "KXKMIA-260503")

    def test_recommendation(self):
        rec = Recommendation(
            timestamp=datetime.now(),
            suggested_action="BUY",
            rationale="Model prob > market prob",
            target_bins=["81-82"],
            expected_value=0.15
        )
        self.assertEqual(rec.suggested_action, "BUY")

    def test_weather_snapshot(self):
        ws = WeatherSnapshot(
            station="KMIA",
            timestamp=datetime.now(),
            current_temp_f=80,
            overcast_flag=True
        )
        self.assertEqual(ws.station, "KMIA")
        self.assertTrue(ws.overcast_flag)

if __name__ == '__main__':
    unittest.main()

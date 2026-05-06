import unittest
from paper_trading.signal_generator import estimate_contract_probability, calculate_speed_to_roi

class TestPaperSignalEnhanced(unittest.TestCase):
    def setUp(self):
        self.model_bins = {
            "<=78": 0.05,
            "79-80": 0.10,
            "81-82": 0.20,
            "83-84": 0.30,
            "85-86": 0.25,
            ">=87": 0.10
        }

    def test_prob_mapping_above_84(self):
        # above 84 means bins 85-86 and >=87
        mapping = {"condition_type": "above", "threshold_f": 84.0}
        prob, warnings = estimate_contract_probability(mapping, self.model_bins)
        self.assertAlmostEqual(prob, 0.25 + 0.10)
        self.assertEqual(len(warnings), 0)

    def test_prob_mapping_below_81(self):
        # below 81 means bins <=78 and 79-80
        mapping = {"condition_type": "below", "threshold_f": 81.0}
        prob, warnings = estimate_contract_probability(mapping, self.model_bins)
        self.assertAlmostEqual(prob, 0.05 + 0.10)

    def test_prob_mapping_between_81_84(self):
        mapping = {"condition_type": "between", "threshold_f": 81.0, "range_high_f": 84.0}
        prob, warnings = estimate_contract_probability(mapping, self.model_bins)
        self.assertAlmostEqual(prob, 0.20 + 0.30)

    def test_uncertain_mapping(self):
        # Threshold cuts through a bin (e.g. 85.5 is inside 85-86)
        mapping = {"condition_type": "above", "threshold_f": 85.5}
        prob, warnings = estimate_contract_probability(mapping, self.model_bins)
        self.assertIsNone(prob)
        self.assertTrue(any("uncertain" in w.lower() for w in warnings))

    def test_speed_to_roi(self):
        ev = 0.10 # 10 cents edge
        # 100 minutes from now
        from datetime import datetime, timedelta, timezone
        close_time = (datetime.now(timezone.utc) + timedelta(minutes=100)).isoformat()
        score, mins = calculate_speed_to_roi(ev, close_time)
        # (0.1 / 100) * 1000 = 1.0
        self.assertEqual(score, 1.0)
        self.assertAlmostEqual(mins, 100.0, delta=1)

if __name__ == "__main__":
    unittest.main()

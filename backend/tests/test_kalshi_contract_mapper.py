import unittest
from pathlib import Path
from market_data.kalshi_contract_mapper import extract_contract_thresholds

class TestKalshiContractMapper(unittest.TestCase):
    def test_structured_above(self):
        m = {
            "ticker": "KX-T91",
            "title": "Will temp be > 91?",
            "strike_type": "greater",
            "floor_strike": 91
        }
        res = extract_contract_thresholds(m)
        self.assertEqual(res["condition_type"], "above")
        self.assertEqual(res["threshold_f"], 91.0)

    def test_structured_below(self):
        m = {
            "ticker": "KX-T84",
            "strike_type": "less",
            "cap_strike": 84
        }
        res = extract_contract_thresholds(m)
        self.assertEqual(res["condition_type"], "below")
        self.assertEqual(res["threshold_f"], 84.0)

    def test_structured_between(self):
        m = {
            "ticker": "KX-B90-91",
            "strike_type": "between",
            "floor_strike": 90,
            "cap_strike": 91
        }
        res = extract_contract_thresholds(m)
        self.assertEqual(res["condition_type"], "between")
        self.assertEqual(res["threshold_f"], 90.0)
        self.assertEqual(res["range_high_f"], 91.0)

    def test_regex_above(self):
        m = {
            "ticker": "KX-ANY",
            "title": "Will the high be 86.5 or above?",
            "subtitle": "86.5 degrees or above"
        }
        res = extract_contract_thresholds(m)
        self.assertEqual(res["condition_type"], "above")
        self.assertEqual(res["threshold_f"], 86.5)

    def test_regex_range(self):
        m = {
            "ticker": "KX-ANY",
            "subtitle": "88 to 89 degrees"
        }
        res = extract_contract_thresholds(m)
        self.assertEqual(res["condition_type"], "between")
        self.assertEqual(res["threshold_f"], 88.0)
        self.assertEqual(res["range_high_f"], 89.0)

    def test_ticker_fallback(self):
        m = {
            "ticker": "KXHIGHMIA-26MAY06-B84.5"
        }
        res = extract_contract_thresholds(m)
        self.assertEqual(res["condition_type"], "above")
        self.assertEqual(res["threshold_f"], 84.5)

if __name__ == "__main__":
    unittest.main()

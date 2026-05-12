import unittest
from market_data.kalshi_contract_mapper import bin_string_to_range, extract_contract_thresholds
from forecasting.contract_probability_mapper import map_distribution_to_contracts

class TestContractProbabilityMapper(unittest.TestCase):
    
    def test_bin_string_to_range_half_degrees(self):
        # <84.5 means <=84
        self.assertEqual(bin_string_to_range("<84.5"), (-999, 84))
        # >84.5 means >=85
        self.assertEqual(bin_string_to_range(">84.5"), (85, 999))
        # <=89 means <=89
        self.assertEqual(bin_string_to_range("<=89"), (-999, 89))
        # >=95 means >=95
        self.assertEqual(bin_string_to_range(">=95"), (95, 999))
        # <91 means <=90
        self.assertEqual(bin_string_to_range("<91"), (-999, 90))
        # >91 means >=92
        self.assertEqual(bin_string_to_range(">91"), (92, 999))
        
    def test_extract_contract_thresholds_hardened(self):
        # Test half-degree boundary from ticker or text
        market = {
            "ticker": "KXHIGHMIA-26MAY11-B84.5",
            "title": "Miami High above 84.5",
            "subtitle": "",
            "strike_type": "greater",
            "floor_strike": 84.5
        }
        res = extract_contract_thresholds(market)
        self.assertEqual(res["condition_type"], "above")
        self.assertEqual(res["threshold_f"], 84.5)
        self.assertEqual(res["lower_inclusive"], False)
        
        # Test text parsing fallback
        market_fallback = {
            "ticker": "KXHIGHMIA-26MAY11-B84.5",
            "title": "Miami High 84.5 or below",
            "subtitle": "",
            "strike_type": "" # Force fallback
        }
        res = extract_contract_thresholds(market_fallback)
        self.assertEqual(res["condition_type"], "below")
        self.assertEqual(res["threshold_f"], 84.5)
        self.assertEqual(res["upper_inclusive"], True)
        
    def test_map_distribution_to_contracts(self):
        distribution = {
            83: 0.1,
            84: 0.2,
            85: 0.3,
            86: 0.4
        }
        
        contract_ranges = [
            {
                "ticker": "T1",
                "condition_type": "above",
                "threshold_f": 84.5,
                "lower_inclusive": False
            },
            {
                "ticker": "T2",
                "condition_type": "below",
                "threshold_f": 84.5,
                "upper_inclusive": False
            },
            {
                "ticker": "T3",
                "condition_type": "between",
                "threshold_f": 84.0,
                "range_high_f": 85.0,
                "lower_inclusive": True,
                "upper_inclusive": True
            }
        ]
        
        results = map_distribution_to_contracts(distribution, contract_ranges)
        
        # T1: > 84.5 -> 85, 86 -> 0.3 + 0.4 = 0.7
        self.assertAlmostEqual(results["T1"]["probability"], 0.7)
        
        # T2: < 84.5 -> 83, 84 -> 0.1 + 0.2 = 0.3
        self.assertAlmostEqual(results["T2"]["probability"], 0.3)
        
        # T3: 84 <= temp <= 85 -> 84, 85 -> 0.2 + 0.3 = 0.5
        self.assertAlmostEqual(results["T3"]["probability"], 0.5)

if __name__ == "__main__":
    unittest.main()

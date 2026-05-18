import unittest
from market_data.kalshi_contract_mapper import bin_string_to_range, extract_contract_thresholds
from forecasting.contract_probability_mapper import (
    map_distribution_to_contracts,
    map_contract_probability,
    map_market_probabilities
)

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

    def test_map_contract_probability_comprehensive(self):
        # Create a simple fixture distribution:
        # 83: 0.05, 84: 0.10, 85: 0.15, 86: 0.20, 87: 0.15, 88: 0.10, 89: 0.05, 90: 0.05, 91: 0.05, 92: 0.05, 93: 0.03, 94: 0.02
        fixture_dist = {
            83: 0.05, 84: 0.10, 85: 0.15, 86: 0.20, 87: 0.15, 88: 0.10, 89: 0.05, 90: 0.05, 91: 0.05, 92: 0.05, 93: 0.03, 94: 0.02
        }

        # 1. above 86.5 integrates integer keys >=87: 87, 88, 89, 90, 91, 92, 93, 94
        # expected sum = 0.15 + 0.10 + 0.05 + 0.05 + 0.05 + 0.05 + 0.03 + 0.02 = 0.50
        c1 = {
            "ticker": "T_ABOVE_86_5",
            "contract_range": ">86.5",
            "condition_type": "above",
            "threshold_f": 86.5,
            "lower_inclusive": False
        }
        res1 = map_contract_probability(fixture_dist, c1)
        self.assertTrue(res1["tradable"])
        self.assertAlmostEqual(res1["model_probability"], 0.50)

        # 2. below 84.5 integrates integer keys <=84: 83, 84
        # expected sum = 0.05 + 0.10 = 0.15
        c2 = {
            "ticker": "T_BELOW_84_5",
            "contract_range": "<=84.5",
            "condition_type": "below",
            "threshold_f": 84.5,
            "upper_inclusive": True
        }
        res2 = map_contract_probability(fixture_dist, c2)
        self.assertTrue(res2["tradable"])
        self.assertAlmostEqual(res2["model_probability"], 0.15)

        # 3. between 91-92 integrates 91 and 92 only: 91, 92
        # expected sum = 0.05 + 0.05 = 0.10
        c3 = {
            "ticker": "T_BETWEEN_91_92",
            "contract_range": "91-92",
            "condition_type": "between",
            "threshold_f": 91.0,
            "range_high_f": 92.0,
            "lower_inclusive": True,
            "upper_inclusive": True
        }
        res3 = map_contract_probability(fixture_dist, c3)
        self.assertTrue(res3["tradable"])
        self.assertAlmostEqual(res3["model_probability"], 0.10)

        # 4. >=95 integrates 95+. Here 95+ is empty in our fixture_dist, so expected = 0.0
        c4 = {
            "ticker": "T_GE_95",
            "contract_range": ">=95",
            "condition_type": "above",
            "threshold_f": 95.0,
            "lower_inclusive": True
        }
        res4 = map_contract_probability(fixture_dist, c4)
        self.assertTrue(res4["tradable"])
        self.assertAlmostEqual(res4["model_probability"], 0.0)

        # 5. <=89 integrates <=89: 83, 84, 85, 86, 87, 88, 89
        # expected sum = 0.05 + 0.10 + 0.15 + 0.20 + 0.15 + 0.10 + 0.05 = 0.80
        c5 = {
            "ticker": "T_LE_89",
            "contract_range": "<=89",
            "condition_type": "below",
            "threshold_f": 89.0,
            "upper_inclusive": True
        }
        res5 = map_contract_probability(fixture_dist, c5)
        self.assertTrue(res5["tradable"])
        self.assertAlmostEqual(res5["model_probability"], 0.80)

        # 6. ambiguous contract mapping returns tradable=false.
        c6 = {
            "ticker": "T_AMBIGUOUS",
            "contract_range": "unknown",
            "condition_type": "unknown",
            "uncertain": True
        }
        res6 = map_contract_probability(fixture_dist, c6)
        self.assertFalse(res6["tradable"])
        self.assertIsNone(res6["model_probability"])
        self.assertTrue(len(res6["warnings"]) > 0)

        # 7. invalid distribution returns tradable=false.
        # Create an invalid raw distribution (negative probability)
        invalid_dist = {83: -0.5, 84: 0.5}
        res7 = map_contract_probability(invalid_dist, c1)
        self.assertFalse(res7["tradable"])
        self.assertIsNone(res7["model_probability"])
        self.assertTrue(len(res7["warnings"]) > 0)

        # 8. result includes source/schema metadata.
        # Using build_integer_distribution_from_bins to create a canonical distribution
        from forecasting.distribution_utils import build_integer_distribution_from_bins
        legacy_bins = {
            "<=78": 0.1,
            "79-80": 0.2,
            "81-82": 0.3,
            "83-84": 0.2,
            "85-86": 0.1,
            ">=87": 0.1
        }
        canonical_dist = build_integer_distribution_from_bins(
            legacy_bins,
            source="test_source",
            warnings=["prior warning"]
        )
        res8 = map_contract_probability(canonical_dist, c1)
        self.assertEqual(res8["distribution_source"], "test_source")
        self.assertEqual(res8["schema_version"], "1.0.0")
        self.assertTrue("prior warning" in res8["warnings"])

        # 9. market list helper maps multiple markets.
        raw_markets = [
            {
                "ticker": "KXHIGHMIA-26MAY11-B84.5",
                "title": "Miami High above 84.5",
                "subtitle": "",
                "strike_type": "greater",
                "floor_strike": 84.5
            },
            {
                "ticker": "KXHIGHMIA-26MAY11-B91-92",
                "title": "Miami High 91 to 92",
                "subtitle": "",
                "strike_type": "between",
                "floor_strike": 91.0,
                "cap_strike": 92.0
            }
        ]
        results = map_market_probabilities(fixture_dist, raw_markets)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["market_ticker"], "KXHIGHMIA-26MAY11-B84.5")
        self.assertEqual(results[1]["market_ticker"], "KXHIGHMIA-26MAY11-B91-92")
        self.assertTrue(results[0]["tradable"])
        self.assertTrue(results[1]["tradable"])

if __name__ == "__main__":
    unittest.main()

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
        from market_data.kalshi_contract_mapper import mapping_to_bin_string
        self.assertEqual(mapping_to_bin_string(res), ">=92")

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

    def test_t_contract_text_direction_parsing(self):
        # T85 with title containing "<85°"
        m = {
            "ticker": "KXHIGHMIA-26MAY15-T85",
            "title": "Will the high be <85°?",
            "subtitle": "84° or below",
            "strike_type": "less",
            "cap_strike": 85
        }
        res = extract_contract_thresholds(m)
        self.assertEqual(res["condition_type"], "below")
        self.assertEqual(res["threshold_f"], 85.0)
        from market_data.kalshi_contract_mapper import mapping_to_bin_string
        self.assertEqual(mapping_to_bin_string(res), "<=84")

    def test_t_contract_upper_text_direction_parsing(self):
        # T92 with title containing ">92°"
        m = {
            "ticker": "KXHIGHMIA-26MAY15-T92",
            "title": "Will the high be >92°?",
            "subtitle": "93° or above",
            "strike_type": "greater",
            "floor_strike": 92
        }
        res = extract_contract_thresholds(m)
        self.assertEqual(res["condition_type"], "above")
        self.assertEqual(res["threshold_f"], 92.0)
        from market_data.kalshi_contract_mapper import mapping_to_bin_string
        self.assertEqual(mapping_to_bin_string(res), ">=93")

    def test_t_contract_fallback_heuristic(self):
        # Mock one event ladder with at least:
        # KXHIGHMIA-26MAY15-T85, KXHIGHMIA-26MAY15-T92
        m1 = {
            "ticker": "KXHIGHMIA-26MAY15-T85",
            "event_ticker": "KXHIGHMIA-26MAY15",
            "status": "active",
            "title": "Miami High Temp",
            "subtitle": "Temperature Contract"
        }
        m2 = {
            "ticker": "KXHIGHMIA-26MAY15-T92",
            "event_ticker": "KXHIGHMIA-26MAY15",
            "status": "active",
            "title": "Miami High Temp",
            "subtitle": "Temperature Contract"
        }
        
        from market_data.kalshi_contract_mapper import parse_kalshi_markets
        import json
        import os
        from pathlib import Path

        # We need a dummy snapshot file
        snapshot_path = Path(__file__).parent / "dummy_snapshot.json"
        with open(snapshot_path, "w") as f:
            json.dump({"markets": [m1, m2]}, f)
            
        try:
            markets = parse_kalshi_markets(snapshot_path)
            # Find the parsed markets
            p1 = next(m for m in markets if m["ticker"] == m1["ticker"])
            p2 = next(m for m in markets if m["ticker"] == m2["ticker"])
            
            # Lowest T threshold (85) maps to below
            self.assertEqual(p1["contract_mapping"]["condition_type"], "below")
            # Highest T threshold (92) maps to above
            self.assertEqual(p2["contract_mapping"]["condition_type"], "above")
            
            self.assertTrue(p1["contract_mapping"]["fallback_used"])
            self.assertTrue(p2["contract_mapping"]["fallback_used"])
            
            # Check warnings
            self.assertTrue(any("fallback" in w.lower() or "inferred" in w.lower() for w in p1["contract_bin"]["warnings"]))
            self.assertTrue(any("fallback" in w.lower() or "inferred" in w.lower() for w in p2["contract_bin"]["warnings"]))
            
        finally:
            if snapshot_path.exists():
                os.remove(snapshot_path)

    def test_between_contracts_unchanged(self):
        # Ensure B85.5 still maps to 85-86
        m1 = {
            "ticker": "KX-B85.5",
            "strike_type": "between",
            "floor_strike": 85,
            "cap_strike": 86
        }
        res1 = extract_contract_thresholds(m1)
        from market_data.kalshi_contract_mapper import mapping_to_bin_string
        self.assertEqual(mapping_to_bin_string(res1), "85-86")
        
        # Ensure B87.5 still maps to 87-88
        m2 = {
            "ticker": "KX-B87.5",
            "strike_type": "between",
            "floor_strike": 87,
            "cap_strike": 88
        }
        res2 = extract_contract_thresholds(m2)
        self.assertEqual(mapping_to_bin_string(res2), "87-88")

if __name__ == "__main__":
    unittest.main()

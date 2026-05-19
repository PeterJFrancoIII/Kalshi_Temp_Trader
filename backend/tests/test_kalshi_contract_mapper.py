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

    def test_various_regex_formats(self):
        # <=89
        m1 = {"ticker": "KX-1", "title": "Will high be <=89?"}
        res1 = extract_contract_thresholds(m1)
        self.assertEqual(res1["condition_type"], "below")
        self.assertEqual(res1["threshold_f"], 89.0)
        self.assertTrue(res1["upper_inclusive"])
        self.assertEqual(res1["contract_range_label"], "<=89")

        # 90 or below
        m2 = {"ticker": "KX-2", "title": "Will high be 90 or below?"}
        res2 = extract_contract_thresholds(m2)
        self.assertEqual(res2["condition_type"], "below")
        self.assertEqual(res2["threshold_f"], 90.0)
        self.assertTrue(res2["upper_inclusive"])
        self.assertEqual(res2["contract_range_label"], "<=90")

        # 91-92
        m3 = {"ticker": "KX-3", "title": "Will high be 91-92?"}
        res3 = extract_contract_thresholds(m3)
        self.assertEqual(res3["condition_type"], "between")
        self.assertEqual(res3["threshold_f"], 91.0)
        self.assertEqual(res3["range_high_f"], 92.0)
        self.assertEqual(res3["contract_range_label"], "91-92")

        # 93 to 94
        m4 = {"ticker": "KX-4", "title": "Will high be 93 to 94?"}
        res4 = extract_contract_thresholds(m4)
        self.assertEqual(res4["condition_type"], "between")
        self.assertEqual(res4["threshold_f"], 93.0)
        self.assertEqual(res4["range_high_f"], 94.0)
        self.assertEqual(res4["contract_range_label"], "93-94")

        # 91 or 92 (and/or range separators)
        m5 = {"ticker": "KX-5", "title": "Will high be 91 or 92?"}
        res5 = extract_contract_thresholds(m5)
        self.assertEqual(res5["condition_type"], "between")
        self.assertEqual(res5["threshold_f"], 91.0)
        self.assertEqual(res5["range_high_f"], 92.0)
        self.assertEqual(res5["contract_range_label"], "91-92")

        # >=95
        m6 = {"ticker": "KX-6", "title": "Will high be >=95?"}
        res6 = extract_contract_thresholds(m6)
        self.assertEqual(res6["condition_type"], "above")
        self.assertEqual(res6["threshold_f"], 95.0)
        self.assertTrue(res6["lower_inclusive"])
        self.assertEqual(res6["contract_range_label"], ">=95")

        # >95
        m7 = {"ticker": "KX-7", "title": "Will high be >95?"}
        res7 = extract_contract_thresholds(m7)
        self.assertEqual(res7["condition_type"], "above")
        self.assertEqual(res7["threshold_f"], 95.0)
        self.assertFalse(res7["lower_inclusive"])
        self.assertEqual(res7["contract_range_label"], ">=96")

        # 95 or above
        m8 = {"ticker": "KX-8", "title": "Will high be 95 or above?"}
        res8 = extract_contract_thresholds(m8)
        self.assertEqual(res8["condition_type"], "above")
        self.assertEqual(res8["threshold_f"], 95.0)
        self.assertTrue(res8["lower_inclusive"])
        self.assertEqual(res8["contract_range_label"], ">=95")

        # 86.5 or above
        m9 = {"ticker": "KX-9", "title": "Will high be 86.5 or above?"}
        res9 = extract_contract_thresholds(m9)
        self.assertEqual(res9["condition_type"], "above")
        self.assertEqual(res9["threshold_f"], 86.5)
        self.assertTrue(res9["lower_inclusive"])
        self.assertEqual(res9["contract_range_label"], ">=87")

    def test_conflicts_and_ambiguity(self):
        # Title with conflicting patterns
        m1 = {"ticker": "KX-1", "title": "Will high be above 90 or below 85?"}
        res1 = extract_contract_thresholds(m1)
        self.assertEqual(res1["condition_type"], "unknown")
        self.assertTrue(res1["uncertain"])
        self.assertTrue(any("conflicting" in w.lower() for w in res1["parse_warnings"]))

        # Numbers but no recognizable pattern
        m2 = {"ticker": "KX-2", "title": "Miami High 92"}
        res2 = extract_contract_thresholds(m2)
        self.assertEqual(res2["condition_type"], "unknown")
        self.assertTrue(res2["uncertain"])
        self.assertTrue(any("no recognized" in w.lower() for w in res2["parse_warnings"]))

        # Ticker / parsed threshold conflict (e.g. structured says 95, ticker has T92)
        m3 = {
            "ticker": "KXHIGHMIA-26MAY15-T92",
            "strike_type": "greater",
            "floor_strike": 95,
            "title": "Will high be >95?"
        }
        res3 = extract_contract_thresholds(m3)
        self.assertEqual(res3["condition_type"], "unknown")
        self.assertTrue(res3["uncertain"])
        self.assertTrue(any("ticker threshold" in w.lower() for w in res3["parse_warnings"]))

    def test_classify_market_date_eligibility(self):
        from datetime import datetime, timezone
        from market_data.kalshi_contract_mapper import classify_market_date_eligibility
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from dateutil.tz import gettz as ZoneInfo

        # 1. ELIGIBLE_SAME_DAY: market_date is today
        now_et = datetime(2026, 5, 18, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        elig = classify_market_date_eligibility("2026-05-18", now_et)
        self.assertTrue(elig["eligible"])
        self.assertEqual(elig["status"], "ELIGIBLE_SAME_DAY")
        self.assertEqual(elig["market_date"], "2026-05-18")
        self.assertEqual(elig["current_date_et"], "2026-05-18")

        # 2. ELIGIBLE_NEXT_DAY: market_date is tomorrow, time is at or after 10 AM ET (e.g. 10:15 AM)
        now_et_after_10 = datetime(2026, 5, 18, 10, 15, 0, tzinfo=ZoneInfo("America/New_York"))
        elig = classify_market_date_eligibility("2026-05-19", now_et_after_10)
        self.assertTrue(elig["eligible"])
        self.assertEqual(elig["status"], "ELIGIBLE_NEXT_DAY")

        # 3. NOT_YET_OPEN: market_date is tomorrow, time is before 10 AM ET (e.g. 9:45 AM)
        now_et_before_10 = datetime(2026, 5, 18, 9, 45, 0, tzinfo=ZoneInfo("America/New_York"))
        elig = classify_market_date_eligibility("2026-05-19", now_et_before_10)
        self.assertFalse(elig["eligible"])
        self.assertEqual(elig["status"], "NOT_YET_OPEN")

        # 4. DATE_MISMATCH (Past): market_date is in the past
        elig = classify_market_date_eligibility("2026-05-17", now_et)
        self.assertFalse(elig["eligible"])
        self.assertEqual(elig["status"], "DATE_MISMATCH")
        self.assertIn("past date", elig["reason"].lower())

        # 5. DATE_MISMATCH (Future): market_date is more than one day ahead
        elig = classify_market_date_eligibility("2026-05-20", now_et)
        self.assertFalse(elig["eligible"])
        self.assertEqual(elig["status"], "DATE_MISMATCH")
        self.assertIn("future date", elig["reason"].lower())

        # 6. Robustness test: invalid format
        elig = classify_market_date_eligibility("invalid-date", now_et)
        self.assertFalse(elig["eligible"])
        self.assertEqual(elig["status"], "DATE_MISMATCH")
        self.assertIn("invalid market_date format", elig["reason"].lower())

if __name__ == "__main__":
    unittest.main()

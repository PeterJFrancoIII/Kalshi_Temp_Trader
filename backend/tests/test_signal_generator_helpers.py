"""Characterization tests for the helpers extracted from generate_paper_signal.

Phase 4.1 broke the 450-line ``generate_paper_signal`` function into four
focused helpers. These tests lock in the contracts of each helper so a
future change can't silently shift behavior.

NO REAL TRADING EXECUTION.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_trading.signal_generator import (
    _build_contract_probability_payload,
    _decide_paper_action,
    _extract_market_pricing,
    _load_event_forecast,
    _resolve_model_probability_from_bins,
    _resolve_temp_distribution,
)


# --- _extract_market_pricing ---------------------------------------------

class TestExtractMarketPricing(unittest.TestCase):
    def test_dollar_fields_take_priority(self):
        market = {
            "yes_ask_dollars": 0.40,
            "yes_bid_dollars": 0.38,
            "last_price_dollars": 0.39,
            "yes_ask": 50,
            "yes_bid": 50,
            "last_price": 50,
        }
        prices = _extract_market_pricing(market, {})
        self.assertEqual(prices, {"ask": 0.40, "bid": 0.38, "last": 0.39})

    def test_cent_fallback_when_dollars_missing(self):
        market = {"yes_ask": 40, "yes_bid": 38, "last_price": 39}
        prices = _extract_market_pricing(market, {})
        self.assertAlmostEqual(prices["ask"], 0.40)
        self.assertAlmostEqual(prices["bid"], 0.38)
        self.assertAlmostEqual(prices["last"], 0.39)

    def test_orderbook_overrides_snapshot(self):
        market = {"yes_ask_dollars": 0.40, "yes_bid_dollars": 0.38}
        orderbook = {
            "top_yes_ask_dollars": 0.42,
            "top_yes_bid_dollars": 0.41,
            "last_price_dollars": 0.415,
        }
        prices = _extract_market_pricing(market, orderbook)
        self.assertEqual(prices["ask"], 0.42)
        self.assertEqual(prices["bid"], 0.41)
        self.assertEqual(prices["last"], 0.415)

    def test_all_missing_returns_none_fields(self):
        prices = _extract_market_pricing({}, {})
        self.assertEqual(prices, {"ask": None, "bid": None, "last": None})


# --- _resolve_model_probability_from_bins --------------------------------

class TestResolveModelProbabilityFromBins(unittest.TestCase):
    def test_exact_match(self):
        bins = {">=87": 0.6, "85-86": 0.2}
        self.assertEqual(_resolve_model_probability_from_bins(bins, ">=87"), 0.6)

    def test_normalized_match_strips_whitespace_and_trailing_zero(self):
        """normalize_contract_key only strips whitespace and ``.0`` suffixes,
        which is enough for the common ``"86.0 - 87.0"`` vs ``"86-87"`` case."""
        bins = {"86-87": 0.3}
        self.assertEqual(
            _resolve_model_probability_from_bins(bins, "86.0 - 87.0"),
            0.3,
        )

    def test_missing_returns_none(self):
        bins = {">=87": 0.6}
        self.assertIsNone(_resolve_model_probability_from_bins(bins, "<=78"))

    def test_zero_is_distinguishable_from_missing(self):
        """A bin with value 0.0 must return 0.0, not None — callers rely on
        this distinction to detect explicit-zero vs missing."""
        bins = {"<=78": 0.0}
        self.assertEqual(_resolve_model_probability_from_bins(bins, "<=78"), 0.0)

    def test_empty_inputs(self):
        self.assertIsNone(_resolve_model_probability_from_bins({}, ">=87"))
        self.assertIsNone(_resolve_model_probability_from_bins({">=87": 0.5}, None))


# --- _build_contract_probability_payload ---------------------------------

class TestBuildContractProbabilityPayload(unittest.TestCase):
    def test_stub_payload_when_no_distribution(self):
        market = {"ticker": "KX-TEST"}
        mapping = {"condition_type": "above", "threshold_f": 85, "range_high_f": None}
        payload = _build_contract_probability_payload(
            market=market,
            mapping=mapping,
            temp_dist=None,
            model_bins={},
            bin_str=">=85",
            is_stale=False,
        )
        self.assertEqual(payload["tradable"], False)
        self.assertEqual(payload["distribution_source"], "none")
        self.assertEqual(payload["contract_range_label"], ">=85")
        self.assertEqual(payload["condition_type"], "above")
        self.assertIn("No temperature distribution found", payload["warnings"])

    def test_stale_market_forces_zero_probability(self):
        market = {"ticker": "KX-OLD"}
        mapping = {"condition_type": "above", "threshold_f": 80}
        payload = _build_contract_probability_payload(
            market=market,
            mapping=mapping,
            temp_dist=None,
            model_bins={},
            bin_str=">=80",
            is_stale=True,
        )
        self.assertEqual(payload["model_probability"], 0.0)
        self.assertEqual(payload["tradable"], False)
        self.assertIn("Market is stale", payload["warnings"])

    def test_direct_bin_lookup_overrides_distribution(self):
        """If model_bins lists the contract bin explicitly, that wins over
        the distribution mapper's interpolation."""
        market = {"ticker": "KX-OVERRIDE"}
        mapping = {"condition_type": "above", "threshold_f": 87}
        payload = _build_contract_probability_payload(
            market=market,
            mapping=mapping,
            temp_dist=None,
            model_bins={">=87": 0.42},
            bin_str=">=87",
            is_stale=False,
        )
        self.assertEqual(payload["model_probability"], 0.42)


# --- _decide_paper_action ------------------------------------------------

class TestDecidePaperAction(unittest.TestCase):
    GATE_OPEN = {"allow_paper_recommendations": True, "no_trade_reason": None, "status": "OK"}
    GATE_CLOSED = {
        "allow_paper_recommendations": False,
        "no_trade_reason": "NWS snapshot stale",
        "status": "STALE",
    }

    def test_stale_market_returns_no_signal_with_synthesized_block(self):
        result = _decide_paper_action(
            edge=0.10,
            is_stale=True,
            risk_decision={"decision": "PASS", "gates_evaluated": {"foo": True}},
            weather_gate=self.GATE_OPEN,
        )
        self.assertEqual(result["action"], "NO SIGNAL")
        self.assertEqual(result["risk_decision_val"]["decision"], "BLOCK")
        self.assertEqual(result["risk_decision_val"]["reason"], "Market is stale")
        self.assertEqual(result["no_trade_reason_val"], "Market is stale")

    def test_risk_block_returns_no_trade(self):
        risk = {"decision": "BLOCK", "reason": "spread too wide"}
        result = _decide_paper_action(
            edge=0.10, is_stale=False, risk_decision=risk, weather_gate=self.GATE_OPEN,
        )
        self.assertEqual(result["action"], "NO TRADE")
        self.assertEqual(result["no_trade_reason_val"], "spread too wide")

    def test_high_edge_returns_paper_buy_high_confidence(self):
        result = _decide_paper_action(
            edge=0.20, is_stale=False, risk_decision={"decision": "PASS"}, weather_gate=self.GATE_OPEN,
        )
        self.assertEqual(result["action"], "PAPER BUY CANDIDATE")
        self.assertEqual(result["confidence"], "high")

    def test_medium_edge_returns_paper_buy_medium_confidence(self):
        result = _decide_paper_action(
            edge=0.08, is_stale=False, risk_decision={"decision": "PASS"}, weather_gate=self.GATE_OPEN,
        )
        self.assertEqual(result["action"], "PAPER BUY CANDIDATE")
        self.assertEqual(result["confidence"], "medium")

    def test_small_positive_edge_returns_watch(self):
        result = _decide_paper_action(
            edge=0.02, is_stale=False, risk_decision={"decision": "PASS"}, weather_gate=self.GATE_OPEN,
        )
        self.assertEqual(result["action"], "WATCH")

    def test_zero_or_negative_edge_returns_no_edge(self):
        for edge in (0.0, -0.05):
            with self.subTest(edge=edge):
                result = _decide_paper_action(
                    edge=edge, is_stale=False, risk_decision={"decision": "PASS"}, weather_gate=self.GATE_OPEN,
                )
                self.assertEqual(result["action"], "NO EDGE")

    def test_weather_gate_overrides_paper_buy(self):
        """Even a strong edge must be blocked when the weather gate is closed."""
        result = _decide_paper_action(
            edge=0.30, is_stale=False, risk_decision={"decision": "PASS"}, weather_gate=self.GATE_CLOSED,
        )
        self.assertEqual(result["action"], "NO TRADE")
        self.assertEqual(result["risk_decision_val"], "BLOCK")
        self.assertEqual(result["no_trade_reason_val"], "NWS snapshot stale")


# --- _load_event_forecast ------------------------------------------------

class TestLoadEventForecast(unittest.TestCase):
    def test_no_forecast_found_returns_no_signal_status(self):
        with patch(
            "paper_trading.signal_generator.find_forecast_for_date",
            return_value=None,
        ):
            result = _load_event_forecast(
                event_date="2026-07-04",
                override_forecast_path=None,
                override_forecast_date=None,
            )
        self.assertEqual(result["status"], "NO_SIGNAL")
        self.assertIsNone(result["forecast_path"])
        self.assertEqual(result["model_bins"], {})
        self.assertEqual(result["integer_dist"], {})
        self.assertTrue(any("No forecast artifact found" in w for w in result["warnings"]))

    def test_override_forecast_used_when_date_matches(self):
        with tempfile.TemporaryDirectory() as td:
            forecast_path = Path(td) / "kmia_forecast_2026-07-04_rules_v2_climatology_120000.json"
            payload = {
                "date": "2026-07-04",
                "probability_bins": {">=87": 0.4, "85-86": 0.3},
                "integer_distribution": {"86": 0.2, "87": 0.25},
            }
            forecast_path.write_text(json.dumps(payload))

            result = _load_event_forecast(
                event_date="2026-07-04",
                override_forecast_path=forecast_path,
                override_forecast_date="2026-07-04",
            )
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["forecast_path"], forecast_path)
        self.assertEqual(result["model_bins"], {">=87": 0.4, "85-86": 0.3})
        self.assertEqual(result["integer_dist"], {86: 0.2, 87: 0.25})
        self.assertEqual(result["warnings"], [])

    def test_corrupt_forecast_returns_error_status(self):
        with tempfile.TemporaryDirectory() as td:
            forecast_path = Path(td) / "kmia_forecast_2026-07-04_rules_v2_climatology_120000.json"
            forecast_path.write_text("not-valid-json {{{")

            result = _load_event_forecast(
                event_date="2026-07-04",
                override_forecast_path=forecast_path,
                override_forecast_date="2026-07-04",
            )
        self.assertEqual(result["status"], "ERROR_LOADING_FORECAST")
        self.assertTrue(any("Error loading forecast" in w for w in result["warnings"]))

    def test_forecast_date_mismatch_emits_warning(self):
        with tempfile.TemporaryDirectory() as td:
            forecast_path = Path(td) / "kmia_forecast_2026-07-04_rules_v2_climatology_120000.json"
            payload = {"date": "2026-07-03", "probability_bins": {">=87": 0.5}}
            forecast_path.write_text(json.dumps(payload))

            result = _load_event_forecast(
                event_date="2026-07-04",
                override_forecast_path=forecast_path,
                override_forecast_date="2026-07-04",
            )
        self.assertEqual(result["status"], "OK")
        self.assertTrue(any("does not match event date" in w for w in result["warnings"]))

    def test_empty_probability_bins_sets_no_signal(self):
        with tempfile.TemporaryDirectory() as td:
            forecast_path = Path(td) / "kmia_forecast_2026-07-04_rules_v2_climatology_120000.json"
            payload = {"date": "2026-07-04", "probability_bins": {}}
            forecast_path.write_text(json.dumps(payload))

            result = _load_event_forecast(
                event_date="2026-07-04",
                override_forecast_path=forecast_path,
                override_forecast_date="2026-07-04",
            )
        self.assertEqual(result["status"], "NO_SIGNAL")
        self.assertTrue(any("contains no probability bins" in w for w in result["warnings"]))


# --- _resolve_temp_distribution ------------------------------------------

class TestResolveTempDistribution(unittest.TestCase):
    def test_integer_distribution_preferred(self):
        result = _resolve_temp_distribution(
            model_bins={">=87": 0.6},
            integer_dist={86: 0.2, 87: 0.3, 88: 0.5},
            nws_snapshot=None,
            event_date="2026-07-04",
        )
        self.assertEqual(result, {86: 0.2, 87: 0.3, 88: 0.5})

    def test_reconstructed_from_model_bins_when_no_integer_dist(self):
        with patch(
            "paper_trading.signal_generator.build_integer_distribution_from_bins",
            return_value={85: 0.2, 86: 0.3, 87: 0.5},
        ) as mock_build:
            result = _resolve_temp_distribution(
                model_bins={">=87": 0.5, "85-86": 0.5},
                integer_dist={},
                nws_snapshot={"observed_max_so_far_f": 84},
                event_date="2026-07-04",
            )
        mock_build.assert_called_once()
        self.assertEqual(result, {85: 0.2, 86: 0.3, 87: 0.5})

    def test_empty_inputs_returns_none(self):
        result = _resolve_temp_distribution(
            model_bins={},
            integer_dist={},
            nws_snapshot=None,
            event_date="2026-07-04",
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

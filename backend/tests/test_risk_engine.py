import os
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from risk.risk_engine import (
    RiskDecision,
    check_kill_switch,
    check_weather_data_availability,
    check_weather_freshness,
    check_forecast_confidence,
    check_settlement_boundary_risk,
    check_liquidity_and_spread,
    check_fee_adjusted_edge,
    check_daily_loss_limit,
    check_weekly_drawdown_limit,
    check_market_concentration,
    check_forecast_integrity,
    evaluate_risk_gates
)

class TestRiskEngine(unittest.TestCase):

    @patch.dict(os.environ, {"KALSHI_KILL_SWITCH": "true"})
    def test_gate_10_kill_switch_env(self):
        decision = check_kill_switch()
        self.assertFalse(decision.passed)
        self.assertIn("KALSHI_KILL_SWITCH", decision.reason)

    @patch.dict(os.environ, {}, clear=True)
    def test_gate_10_kill_switch_pass(self):
        decision = check_kill_switch()
        self.assertTrue(decision.passed)

    def test_gate_1_data_availability(self):
        decision = check_weather_data_availability({})
        self.assertFalse(decision.passed)
        
        decision = check_weather_data_availability({"warnings": ["Missing credentials for TWC"]})
        self.assertFalse(decision.passed)
        
        decision = check_weather_data_availability({"warnings": [], "probability_bins": {}})
        self.assertTrue(decision.passed)

    def test_gate_2_weather_freshness(self):
        # Fresh
        now_dt = datetime.now(timezone.utc)
        fresh_dt = (now_dt - timedelta(minutes=30)).isoformat()
        self.assertTrue(check_weather_freshness(fresh_dt).passed)
        
        # Stale
        stale_dt = (now_dt - timedelta(minutes=100)).isoformat()
        self.assertFalse(check_weather_freshness(stale_dt).passed)

    def test_gate_3_forecast_confidence(self):
        self.assertFalse(check_forecast_confidence({"warnings": ["Low confidence due to missing HRRR"]}).passed)
        self.assertTrue(check_forecast_confidence({"warnings": ["Just a normal warning"]}).passed)

    def test_gate_4_settlement_boundary_risk(self):
        # 1. Uncertainty buffer (3.0 deg)
        # Prob=0.50, edge=0.15, forecast=84.5, bin="83-84" -> boundary is 84.0. Diff=0.5 < 3.0. BLOCKED.
        self.assertFalse(check_settlement_boundary_risk(0.50, 0.15, 84.5, "83-84").passed)
        
        # Prob=0.50, edge=0.25, forecast=84.5, bin="83-84" -> diff=0.5 < 3.0 but edge > 0.20. PASSED.
        self.assertTrue(check_settlement_boundary_risk(0.50, 0.25, 84.5, "83-84").passed)

        # 2. Hard rounding buffer (1.0 deg)
        # Prob=0.80, edge=0.10, forecast=84.8, bin=">=85" -> boundary is 85.0. Diff=0.2 < 1.0. BLOCKED.
        self.assertFalse(check_settlement_boundary_risk(0.80, 0.10, 84.8, ">=85").passed)
        
        # Prob=0.80, edge=0.20, forecast=84.8, bin=">=85" -> diff=0.2 < 1.0 but edge > 0.15. PASSED.
        self.assertTrue(check_settlement_boundary_risk(0.80, 0.20, 84.8, ">=85").passed)

        # 3. Safe forecast
        # Forecast=80.0, bin="85-86". Boundaries 85, 86. Diff=5.0 > 3.0. PASSED.
        self.assertTrue(check_settlement_boundary_risk(0.80, 0.10, 80.0, "85-86").passed)

    def test_gate_5_liquidity(self):
        self.assertFalse(check_liquidity_and_spread(None, 0.50).passed)
        self.assertFalse(check_liquidity_and_spread(0.70, 0.50).passed) # Spread 0.20
        self.assertTrue(check_liquidity_and_spread(0.55, 0.50).passed) # Spread 0.05

    def test_gate_5_crossed_market_bid_greater_than_ask(self):
        """CM1: bid > ask is a crossed market and must block Gate 5."""
        result = check_liquidity_and_spread(yes_ask=0.45, yes_bid=0.55)
        self.assertFalse(result.passed, "bid > ask must block (crossed market).")
        self.assertIn("Crossed", result.reason)

    def test_gate_5_zero_spread_bid_equals_ask(self):
        """CM1: bid == ask is a zero-spread (degenerate) market and must block Gate 5."""
        result = check_liquidity_and_spread(yes_ask=0.50, yes_bid=0.50)
        self.assertFalse(result.passed, "bid == ask must block (zero-spread market).")
        self.assertIn("Crossed", result.reason)

    def test_gate_5_normal_market_passes(self):
        """CM1: Normal bid < ask with acceptable spread must still pass Gate 5."""
        result = check_liquidity_and_spread(yes_ask=0.55, yes_bid=0.50)
        self.assertTrue(result.passed, "Normal bid < ask with spread 0.05 must pass.")

    def test_gate_5_wide_spread_still_blocks(self):
        """CM1: Wide-spread check is preserved — spread > 0.15 must still block."""
        result = check_liquidity_and_spread(yes_ask=0.70, yes_bid=0.50)
        self.assertFalse(result.passed, "Spread 0.20 > 0.15 must still block.")
        self.assertIn("wide", result.reason.lower())

    def test_gate_6_fee_adjusted_edge(self):
        self.assertFalse(check_fee_adjusted_edge(0.04).passed)
        self.assertTrue(check_fee_adjusted_edge(0.06).passed)

    def test_gate_7_daily_loss(self):
        self.assertFalse(check_daily_loss_limit({"daily_pnl": -55.0}).passed)
        self.assertTrue(check_daily_loss_limit({"daily_pnl": -10.0}).passed)

    def test_gate_8_weekly_drawdown(self):
        self.assertFalse(check_weekly_drawdown_limit({"weekly_pnl": -155.0}).passed)
        self.assertTrue(check_weekly_drawdown_limit({"weekly_pnl": -50.0}).passed)

    def test_gate_9_market_concentration(self):
        self.assertFalse(check_market_concentration({"active_trades_by_date": {"2026-05-11": 3}}, "2026-05-11").passed)
        self.assertTrue(check_market_concentration({"active_trades_by_date": {"2026-05-11": 1}}, "2026-05-11").passed)
        
        # Fail-closed on missing data
        self.assertFalse(check_market_concentration({}, "2026-05-11").passed)
        
    def test_gate_11_forecast_integrity(self):
        # Valid
        data = {"probability_bins": {"<=78": 0.5, ">=87": 0.5}}
        self.assertTrue(check_forecast_integrity(data).passed)
        
        # Invalid sum
        data = {"probability_bins": {"<=78": 0.5, ">=87": 0.6}}
        self.assertFalse(check_forecast_integrity(data).passed)
        
        # Missing probabilities for contracts
        contracts = [{"label": "81-82"}]
        data = {"probability_bins": {"<=78": 1.0}}
        self.assertFalse(check_forecast_integrity(data, contracts).passed)
        
        # Valid with contracts
        contracts = [{"label": "81-82"}]
        data = {"probability_bins": {"81-82": 1.0}}
        self.assertTrue(check_forecast_integrity(data, contracts).passed)

    @patch.dict(os.environ, {}, clear=True)
    def test_evaluate_all_gates(self):
        now_dt = datetime.now(timezone.utc).isoformat()
        
        decision = evaluate_risk_gates(
            forecast_data={"warnings": [], "probability_bins": {"<=78": 0.1, "79-80": 0.1, "81-82": 0.1, "83-84": 0.4, "85-86": 0.2, ">=87": 0.1}},
            latest_obs_time_iso=now_dt,
            model_prob=0.70,
            executable_price=0.50,
            yes_ask=0.52,
            yes_bid=0.48,
            edge=0.15,
            raw_edge=0.20,
            ledger_summary={"daily_pnl": 0, "weekly_pnl": 0, "active_trades_by_date": {}},
            target_date_str="2026-05-11",
            best_high_f=83.5,
            bin_label="83-84",
            contract_bins=[{"label": "83-84"}, {"label": "<=78"}, {"label": "79-80"}, {"label": "81-82"}, {"label": "85-86"}, {"label": ">=87"}]
        )
        self.assertTrue(decision.passed, f"Should pass but failed: {decision.reason}")

if __name__ == "__main__":
    unittest.main()

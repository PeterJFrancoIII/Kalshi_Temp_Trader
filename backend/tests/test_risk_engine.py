import os
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from src.risk.risk_engine import (
    RiskDecision,
    check_kill_switch,
    check_weather_data_availability,
    check_weather_freshness,
    check_forecast_confidence,
    check_near_boundary_settlement,
    check_liquidity_and_spread,
    check_fee_adjusted_edge,
    check_daily_loss_limit,
    check_weekly_drawdown_limit,
    check_market_concentration,
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

    def test_gate_4_near_boundary(self):
        # Edge = 0.05, prob = 0.50 -> BLOCKED
        self.assertFalse(check_near_boundary_settlement(0.50, 0.05).passed)
        
        # Edge = 0.15, prob = 0.50 -> PASSED
        self.assertTrue(check_near_boundary_settlement(0.50, 0.15).passed)
        
        # Edge = 0.05, prob = 0.80 -> PASSED
        self.assertTrue(check_near_boundary_settlement(0.80, 0.05).passed)

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

    @patch.dict(os.environ, {}, clear=True)
    def test_evaluate_all_gates(self):
        now_dt = datetime.now(timezone.utc).isoformat()
        
        decision = evaluate_risk_gates(
            forecast_data={"warnings": []},
            latest_obs_time_iso=now_dt,
            model_prob=0.70,
            executable_price=0.50,
            yes_ask=0.52,
            yes_bid=0.48,
            edge=0.15,
            raw_edge=0.20,
            ledger_summary={},
            target_date_str="2026-05-11"
        )
        self.assertTrue(decision.passed)

if __name__ == "__main__":
    unittest.main()

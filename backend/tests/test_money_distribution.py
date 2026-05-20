import unittest
from datetime import datetime, timezone
from pathlib import Path
import json

from risk.money_distribution import distribute_money, check_exhaustive_and_exclusive
from risk.risk_engine import RiskDecision


class TestMoneyDistribution(unittest.TestCase):
    def setUp(self):
        self.bankroll = 1000.0
        self.target_date = "2026-05-20"
        
        # 1. Standard mock integer distribution (sums to 1.0)
        self.forecast_data = {
            "date": self.target_date,
            "integer_distribution": {
                "83": 0.1,
                "84": 0.1,
                "85": 0.2,
                "86": 0.2,
                "87": 0.2,
                "88": 0.2
            }
        }
        
        # 2. Standard mock weather gate
        self.weather_gate = {
            "allow_paper_recommendations": True,
            "status": "PASS",
            "no_trade_reason": None,
            "latest_observation_time": datetime.now(timezone.utc).isoformat(),
        }
        
        # 3. Standard mock ledger summary
        self.ledger_summary = {
            "account_balance": self.bankroll,
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "active_trades_by_date": {}
        }
        
        # 4. Standard active signals (not an arbitrage, sum of costs > 1.0)
        self.active_signals = [
            {
                "market_ticker": "KX-A",
                "contract_range": "<=84",
                "forecast_bin_label": "<=84",
                "model_probability": 0.20,
                "market_probability": 0.35,
                "executable_price": 0.35,
                "executable_edge": -0.15,
                "yes_ask": 0.35,
                "yes_bid": 0.33,
                "last_price": 0.35,
                "paper_action": "NO TRADE",
                "risk_decision": {"decision": "BLOCK", "reason": "Negative edge"}
            },
            {
                "market_ticker": "KX-B",
                "contract_range": "85-86",
                "forecast_bin_label": "85-86",
                "model_probability": 0.40,
                "market_probability": 0.25,
                "executable_price": 0.25,
                "executable_edge": 0.15,
                "yes_ask": 0.25,
                "yes_bid": 0.23,
                "last_price": 0.25,
                "paper_action": "BUY",
                "risk_decision": {"decision": "ALLOW", "reason": "OK"}
            },
            {
                "market_ticker": "KX-C",
                "contract_range": "87-88",
                "forecast_bin_label": "87-88",
                "model_probability": 0.40,
                "market_probability": 0.25,
                "executable_price": 0.25,
                "executable_edge": 0.15,
                "yes_ask": 0.25,
                "yes_bid": 0.23,
                "last_price": 0.25,
                "paper_action": "BUY",
                "risk_decision": {"decision": "ALLOW", "reason": "OK"}
            },
            {
                "market_ticker": "KX-D",
                "contract_range": ">=89",
                "forecast_bin_label": ">=89",
                "model_probability": 0.00,
                "market_probability": 0.20,
                "executable_price": 0.20,
                "executable_edge": -0.20,
                "yes_ask": 0.20,
                "yes_bid": 0.18,
                "last_price": 0.20,
                "paper_action": "NO TRADE",
                "risk_decision": {"decision": "BLOCK", "reason": "Negative edge"}
            }
        ]

    def test_range_partition_check(self):
        # Valid partition covering [-999, 999]
        valid_ranges = [(-999, 84), (85, 86), (87, 88), (89, 999)]
        self.assertTrue(check_exhaustive_and_exclusive(valid_ranges))
        
        # Gap between 86 and 88
        gap_ranges = [(-999, 84), (85, 86), (88, 999)]
        self.assertFalse(check_exhaustive_and_exclusive(gap_ranges))
        
        # Overlap between 86 and 87
        overlap_ranges = [(-999, 84), (85, 87), (87, 88), (89, 999)]
        self.assertFalse(check_exhaustive_and_exclusive(overlap_ranges))

    def test_guaranteed_profit_returns_false_when_costs_too_high(self):
        # Even though these form a partition, their sum of prices is high (0.35+0.25+0.25+0.20 = 1.05)
        # Adding fees/slippage makes it even higher, so no arbitrage is possible.
        res = distribute_money(
            bankroll=self.bankroll,
            active_signals=self.active_signals,
            forecast_data=self.forecast_data,
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date,
            mode="guarantee_profit"
        )
        self.assertFalse(res["guaranteed_profit_possible"])
        # Should fallback to risk adjusted (which has fallback suffix)
        self.assertTrue(res["allocation_mode"].endswith("fallback_risk_adjusted"))
        # Should contain the warning
        self.assertTrue(any("Guaranteed net-positive allocation not available" in w for w in res["warnings"]))

    def test_guaranteed_profit_returns_true_on_arbitrage_fixture(self):
        # Create an arbitrage fixture: sum of costs is low
        # Contract range partition:
        # A: <=84, B: 85-86, C: 87-88, D: >=89
        # Low prices: A: 0.10, B: 0.10, C: 0.10, D: 0.10
        # Sum price = 0.40. Even with fees/slippage, total cost will be well below 1.0.
        arb_signals = []
        for sig in self.active_signals:
            new_sig = sig.copy()
            new_sig["yes_ask"] = 0.10
            new_sig["executable_price"] = 0.10
            new_sig["last_price"] = 0.10
            new_sig["paper_action"] = "BUY"
            new_sig["risk_decision"] = {"decision": "ALLOW", "reason": "OK"}
            arb_signals.append(new_sig)
            
        res = distribute_money(
            bankroll=self.bankroll,
            active_signals=arb_signals,
            forecast_data=self.forecast_data,
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date,
            mode="guarantee_profit"
        )
        self.assertTrue(res["guaranteed_profit_possible"])
        self.assertEqual(res["allocation_mode"], "guarantee_profit")
        self.assertTrue(res["worst_case_profit"] > 0)
        self.assertTrue(res["total_allocated"] > 0)

    def test_risk_adjusted_allocates_only_to_positive_edge_contracts(self):
        res = distribute_money(
            bankroll=self.bankroll,
            active_signals=self.active_signals,
            forecast_data=self.forecast_data,
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date,
            mode="risk_adjusted"
        )
        self.assertEqual(res["allocation_mode"], "risk_adjusted")
        
        # Only KX-B and KX-C have positive edge and are ALLOWed
        allocations = {row["contract_ticker"]: row["recommended_allocation_dollars"] for row in res["rows"]}
        self.assertTrue(allocations["KX-B"] > 0)
        self.assertTrue(allocations["KX-C"] > 0)
        self.assertEqual(allocations["KX-A"], 0.0)
        self.assertEqual(allocations["KX-D"], 0.0)

    def test_negative_edge_contracts_get_zero_with_no_trade_reason(self):
        res = distribute_money(
            bankroll=self.bankroll,
            active_signals=self.active_signals,
            forecast_data=self.forecast_data,
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date,
            mode="risk_adjusted"
        )
        
        rows = {row["contract_ticker"]: row for row in res["rows"]}
        self.assertEqual(rows["KX-A"]["recommended_allocation_dollars"], 0.0)
        self.assertIsNotNone(rows["KX-A"]["no_trade_reason"])
        
        self.assertEqual(rows["KX-D"]["recommended_allocation_dollars"], 0.0)
        self.assertIsNotNone(rows["KX-D"]["no_trade_reason"])

    def test_kelly_sizing_and_caps(self):
        # We can pass custom config to test caps and kelly sizing
        config = {
            "kelly_fraction": 0.25,
            "per_contract_cap_fraction": 0.05,  # 5% of $1000 = $50 cap
            "per_market_cap_fraction": 0.08,    # 8% of $1000 = $80 cap
        }
        res = distribute_money(
            bankroll=self.bankroll,
            active_signals=self.active_signals,
            forecast_data=self.forecast_data,
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date,
            mode="risk_adjusted",
            config=config
        )
        
        # Individual allocations should be capped by per_contract_cap ($50)
        # And their sum should be capped by per_market_cap ($80), so scaled down
        allocations = {row["contract_ticker"]: row["recommended_allocation_dollars"] for row in res["rows"]}
        self.assertLessEqual(allocations["KX-B"], 50.0)
        self.assertLessEqual(allocations["KX-C"], 50.0)
        self.assertLessEqual(res["total_allocated"], 80.01) # Allow minor float tolerance

    def test_portfolio_pnl_by_outcome_accuracy(self):
        res = distribute_money(
            bankroll=self.bankroll,
            active_signals=self.active_signals,
            forecast_data=self.forecast_data,
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date,
            mode="risk_adjusted"
        )
        
        # PnL by outcome list should cover all active contracts + uncovered (if any)
        outcomes = {o["outcome_bin"]: o for o in res["pnl_by_outcome"]}
        self.assertIn("<=84", outcomes)
        self.assertIn("85-86", outcomes)
        self.assertIn("87-88", outcomes)
        self.assertIn(">=89", outcomes)

    def test_probability_of_profit_calculation(self):
        # If we only allocate to KX-B and KX-C:
        # KX-B represents "85-86", KX-C represents "87-88".
        # Total probability of winning either is 0.40 + 0.40 = 0.80.
        # Let's verify that probability_of_profit matches this.
        res = distribute_money(
            bankroll=self.bankroll,
            active_signals=self.active_signals,
            forecast_data=self.forecast_data,
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date,
            mode="risk_adjusted"
        )
        self.assertGreater(res["probability_of_profit"], 0.79)
        self.assertLessEqual(res["probability_of_profit"], 0.81)

    def test_missing_or_stale_data_blocks_allocation(self):
        # 1. Missing forecast data
        res_no_forecast = distribute_money(
            bankroll=self.bankroll,
            active_signals=self.active_signals,
            forecast_data={},
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date
        )
        self.assertEqual(res_no_forecast["total_allocated"], 0.0)
        self.assertTrue(any("No forecast" in w for w in res_no_forecast["warnings"]))
        
        # 2. Stale weather gate
        stale_gate = self.weather_gate.copy()
        stale_gate["allow_paper_recommendations"] = False
        stale_gate["no_trade_reason"] = "Stale observation"
        from datetime import timedelta
        stale_gate["latest_observation_time"] = (
            datetime.now(timezone.utc) - timedelta(hours=3)
        ).isoformat()
        res_stale = distribute_money(
            bankroll=self.bankroll,
            active_signals=self.active_signals,
            forecast_data=self.forecast_data,
            weather_gate=stale_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date
        )
        self.assertEqual(res_stale["total_allocated"], 0.0)
        self.assertTrue(any("stale" in w.lower() for w in res_stale["warnings"]))

    def test_missing_market_prices_blocks_allocation(self):
        # If all signals have no price data
        signals_no_price = []
        for sig in self.active_signals:
            new_sig = sig.copy()
            new_sig["yes_ask"] = None
            new_sig["last_price"] = None
            new_sig["executable_price"] = None
            signals_no_price.append(new_sig)
            
        res = distribute_money(
            bankroll=self.bankroll,
            active_signals=signals_no_price,
            forecast_data=self.forecast_data,
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date
        )
        self.assertEqual(res["total_allocated"], 0.0)

    def test_safety_metadata_enforced(self):
        res = distribute_money(
            bankroll=self.bankroll,
            active_signals=self.active_signals,
            forecast_data=self.forecast_data,
            weather_gate=self.weather_gate,
            ledger_summary=self.ledger_summary,
            target_date=self.target_date
        )
        self.assertTrue(res["safety"]["no_real_trading"])
        self.assertTrue(res["safety"]["no_order_execution"])
        self.assertEqual(res["safety"]["disclaimer"], "NO REAL TRADING EXECUTION - PAPER ONLY")


if __name__ == "__main__":
    unittest.main()

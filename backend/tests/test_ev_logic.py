import unittest
import time
import sys
import os

# Add backend/src to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from recommendation import ev, gates
from recommendation.types import RecommendationInput, MarketSnapshot, Action
from recommendation.recommender import generate_recommendations

class TestEVLogic(unittest.TestCase):
    def test_ev_math(self):
        # implied probability
        self.assertEqual(ev.calculate_implied_probability(45), 0.45)
        
        # raw edge
        self.assertEqual(ev.calculate_edge(0.60, 0.45), 0.15)
        
        # kalshi fee: 0.07 * p * (1-p)
        # 0.07 * 0.45 * 0.55 = 0.017325 -> rounded to 0.0173
        self.assertEqual(ev.calculate_kalshi_fee(0.45), 0.0173)
        
        # edge after fees
        self.assertEqual(ev.calculate_edge_after_fees(0.15, 0.0173), 0.1327)

    def test_gates(self):
        now = int(time.time())
        
        # staleness
        ok, _ = gates.check_data_staleness(now - 100, now - 50, now, max_age_seconds=300)
        self.assertTrue(ok)
        ok, _ = gates.check_data_staleness(now - 400, now - 50, now, max_age_seconds=300)
        self.assertFalse(ok) # pred stale
        
        # spread
        ok, _ = gates.check_spread(50, 45, max_spread_cents=10)
        self.assertTrue(ok)
        ok, _ = gates.check_spread(60, 45, max_spread_cents=10)
        self.assertFalse(ok) # wide
        
        # liquidity
        ok, _ = gates.check_liquidity(15, min_size=10)
        self.assertTrue(ok)
        ok, _ = gates.check_liquidity(5, min_size=10)
        self.assertFalse(ok)
        
        # confidence
        ok, _ = gates.check_confidence("high")
        self.assertTrue(ok)
        ok, _ = gates.check_confidence("low")
        self.assertFalse(ok)

    def test_recommender_e2e(self):
        now = int(time.time())
        
        # Perfect scenario -> TRADE_CANDIDATE
        # model 0.60, ask 45 (implied 0.45), edge 0.15
        # fee = 0.07 * 0.45 * 0.55 = 0.0173
        # edge_after_fee = 0.15 - 0.0173 = 0.1327
        input_data = RecommendationInput(
            station="KMIA",
            date="2026-05-03",
            model_probabilities={"81-82": 0.60},
            confidence="high",
            prediction_ts=now,
            market_snapshots=[
                MarketSnapshot(bin_name="81-82", yes_ask=45, yes_bid=40, liquidity=100, market_ts=now)
            ]
        )
        res = generate_recommendations(input_data, current_ts=now)
        self.assertEqual(len(res.recommendations), 1)
        rec = res.recommendations[0]
        self.assertEqual(rec.action, Action.TRADE_CANDIDATE)
        self.assertEqual(rec.edge_after_fees, 0.1327)
        self.assertEqual(rec.market_ask_probability, 0.45)
        self.assertEqual(rec.estimated_fee, 0.0173)
        self.assertEqual(rec.spread, 0.05)
        
        # Positive edge but below threshold -> WATCH
        # model 0.50, ask 45 (implied 0.45), edge 0.05
        # fee 0.0173, edge_after_fee = 0.0327 (< 0.05 threshold)
        input_data.model_probabilities = {"81-82": 0.50}
        res = generate_recommendations(input_data, current_ts=now, min_trade_edge=0.05)
        self.assertEqual(res.recommendations[0].action, Action.WATCH)
        
        # Negative edge -> REJECT
        input_data.model_probabilities = {"81-82": 0.40}
        res = generate_recommendations(input_data, current_ts=now)
        self.assertEqual(res.recommendations[0].action, Action.REJECT)
        self.assertIn("No positive edge", res.recommendations[0].reason)

        # Stale data -> REJECT
        input_data.model_probabilities = {"81-82": 0.60} # reset
        input_data.prediction_ts = now - 1000 # stale
        res = generate_recommendations(input_data, current_ts=now)
        self.assertEqual(res.recommendations[0].action, Action.REJECT)
        self.assertIn("stale", res.recommendations[0].reason.lower())

if __name__ == '__main__':
    unittest.main()

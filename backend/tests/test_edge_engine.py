import unittest
from datetime import datetime, timezone, timedelta
from src.trading.edge_engine import (
    calculate_fee_adjusted_breakeven,
    calculate_slippage_adjusted_breakeven,
    calculate_expected_value,
    calculate_speed_to_roi,
    calculate_edge
)

class TestEdgeEngine(unittest.TestCase):
    
    def test_calculate_fee_adjusted_breakeven(self):
        # Fee = 0.07 * p * (1 - p)
        # p = 0.50 => 0.07 * 0.5 * 0.5 = 0.0175
        # Cost = 0.5175
        self.assertAlmostEqual(calculate_fee_adjusted_breakeven(0.50), 0.5175)
        
        # p = 0.99 => 0.07 * 0.99 * 0.01 = 0.000693
        # Cost = 0.9907
        self.assertAlmostEqual(calculate_fee_adjusted_breakeven(0.99), 0.9907)
        
        # Invalid price
        with self.assertRaises(ValueError):
            calculate_fee_adjusted_breakeven(1.1)

    def test_calculate_expected_value(self):
        # EV = (model_prob * 1.0) - cost
        self.assertAlmostEqual(calculate_expected_value(0.60, 0.5175), 0.0825)
        self.assertAlmostEqual(calculate_expected_value(0.40, 0.5175), -0.1175)

    def test_calculate_edge(self):
        # p = 0.50, prob = 0.60, slip = 0.01
        # Fee cost = 0.5175
        # Total cost = 0.5275
        # Edge = 0.60 - 0.5275 = 0.0725
        # Raw Edge = 0.60 - 0.50 = 0.10
        edge, raw, breakeven = calculate_edge(0.60, 0.50, slippage=0.01)
        self.assertAlmostEqual(edge, 0.0725)
        self.assertAlmostEqual(raw, 0.10)
        self.assertAlmostEqual(breakeven, 0.5275)

    def test_calculate_speed_to_roi(self):
        close_time = (datetime.now(timezone.utc) + timedelta(minutes=100)).isoformat()
        score, mins = calculate_speed_to_roi(0.50, close_time)
        # score = (0.50 / 100) * 1000 = 5.0
        self.assertTrue(4.9 <= score <= 5.1)
        self.assertTrue(99 <= mins <= 101)

if __name__ == "__main__":
    unittest.main()

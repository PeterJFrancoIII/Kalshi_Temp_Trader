import unittest
import json
import os
import shutil
from datetime import datetime, timezone
from paper_trading.learning import generate_summary

# NO REAL TRADING EXECUTION

class TestPaperLearning(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_learning"))
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Override paths in learning.py (monkeypatching for test)
        import paper_trading.learning as learning
        self.old_paper_dir = learning.PAPER_DIR
        self.old_learning_dir = learning.LEARNING_DIR
        
        learning.PAPER_DIR = os.path.join(self.test_dir, "paper_trading")
        learning.LEARNING_DIR = os.path.join(self.test_dir, "learning")
        os.makedirs(learning.PAPER_DIR, exist_ok=True)
        os.makedirs(learning.LEARNING_DIR, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        import paper_trading.learning as learning
        learning.PAPER_DIR = self.old_paper_dir
        learning.LEARNING_DIR = self.old_learning_dir

    def test_no_settled_trades_waiting_message(self):
        # Create empty performance file
        perf_path = os.path.join(self.test_dir, "paper_trading", "latest_paper_trading_performance.json")
        with open(perf_path, 'w') as f:
            json.dump({"total_settled_trades": 0}, f)
            
        summary = generate_summary()
        self.assertEqual(summary['model_lesson'], "Waiting for settlement.")
        self.assertTrue(summary['safety']['no_real_trading'])

    def test_positive_win_rate_good_message(self):
        perf_path = os.path.join(self.test_dir, "paper_trading", "latest_paper_trading_performance.json")
        with open(perf_path, 'w') as f:
            json.dump({
                "total_settled_trades": 5,
                "win_rate": 0.8,
                "total_simulated_pnl": 10.0
            }, f)
            
        summary = generate_summary()
        self.assertEqual(summary['model_lesson'], "Current paper strategy is performing well.")

    def test_negative_pnl_caution_message(self):
        perf_path = os.path.join(self.test_dir, "paper_trading", "latest_paper_trading_performance.json")
        with open(perf_path, 'w') as f:
            json.dump({
                "total_settled_trades": 10,
                "win_rate": 0.55,
                "total_simulated_pnl": -5.0
            }, f)
            
        summary = generate_summary()
        self.assertEqual(summary['model_lesson'], "Paper strategy needs caution.")

    def test_review_thresholds_message(self):
        perf_path = os.path.join(self.test_dir, "paper_trading", "latest_paper_trading_performance.json")
        with open(perf_path, 'w') as f:
            json.dump({
                "total_settled_trades": 4,
                "win_rate": 0.25,
                "total_simulated_pnl": 0.0
            }, f)
            
        summary = generate_summary()
        self.assertEqual(summary['model_lesson'], "Review calibration and edge thresholds.")

    def test_summary_file_creation(self):
        generate_summary()
        latest_path = os.path.join(self.test_dir, "learning", "latest_learning_summary.json")
        self.assertTrue(os.path.exists(latest_path))
        
if __name__ == "__main__":
    unittest.main()

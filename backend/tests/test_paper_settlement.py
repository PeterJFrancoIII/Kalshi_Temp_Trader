import unittest
import json
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from paper_trading import settlement

class TestPaperSettlement(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        
        self.ledger_file = self.test_dir / "ledger.jsonl"
        self.history_file = self.test_dir / "history.jsonl"
        self.settlements_file = self.test_dir / "settlements.jsonl"
        self.performance_file = self.test_dir / "performance.json"
        
        # Override paths in settlement module
        self.original_ledger = settlement.LEDGER_FILE
        self.original_history = settlement.HISTORY_FILE
        self.original_settlements = settlement.SETTLEMENTS_FILE
        self.original_performance = settlement.PERFORMANCE_FILE
        
        settlement.LEDGER_FILE = self.ledger_file
        settlement.HISTORY_FILE = self.history_file
        settlement.SETTLEMENTS_FILE = self.settlements_file
        settlement.PERFORMANCE_FILE = self.performance_file

    def tearDown(self):
        settlement.LEDGER_FILE = self.original_ledger
        settlement.HISTORY_FILE = self.original_history
        settlement.SETTLEMENTS_FILE = self.original_settlements
        settlement.PERFORMANCE_FILE = self.original_performance
        
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_parse_ticker_date(self):
        self.assertEqual(settlement.parse_ticker_date("KXHIGHMIA-26MAY06-B84.5"), "2026-05-06")
        self.assertEqual(settlement.parse_ticker_date("KXHIGHMIA-25DEC25-T90"), "2025-12-25")
        self.assertIsNone(settlement.parse_ticker_date("INVALID-TICKER"))

    def test_settle_won_lost(self):
        # 1. Mock History (Date -> TMAX)
        with open(self.history_file, "w") as f:
            f.write(json.dumps({"date": "2026-05-01", "tmax_f": 84}) + "\n") # actual_bin: 83-84
            f.write(json.dumps({"date": "2026-05-02", "tmax_f": 86}) + "\n") # actual_bin: 85-86
        
        # 2. Mock Ledger
        trades = [
            {
                "market_ticker": "KXHIGHMIA-26MAY01-B84.5",
                "forecast_bin": "83-84",
                "simulated_entry_price": 0.20,
                "status": "OPEN",
                "model_probability": 0.4,
                "edge": 0.2
            },
            {
                "market_ticker": "KXHIGHMIA-26MAY02-B82.5",
                "forecast_bin": "81-82",
                "simulated_entry_price": 0.15,
                "status": "OPEN",
                "model_probability": 0.3,
                "edge": 0.15
            }
        ]
        with open(self.ledger_file, "w") as f:
            for t in trades:
                f.write(json.dumps(t) + "\n")
        
        # Run Settlement
        settlement.settle_paper_trades()
        
        # Verify Settlements
        self.assertTrue(self.settlements_file.exists())
        results = []
        with open(self.settlements_file, "r") as f:
            for line in f:
                results.append(json.loads(line))
        
        self.assertEqual(len(results), 2)
        
        # Trade 1: Won (84 falls in 83-84)
        self.assertEqual(results[0]["market_ticker"], "KXHIGHMIA-26MAY01-B84.5")
        self.assertEqual(results[0]["result"], "WON")
        self.assertEqual(results[0]["simulated_pnl"], 0.8) # 1.0 - 0.2
        
        # Trade 2: Lost (86 falls in 85-86, forecast was 81-82)
        self.assertEqual(results[1]["market_ticker"], "KXHIGHMIA-26MAY02-B82.5")
        self.assertEqual(results[1]["result"], "LOST")
        self.assertEqual(results[1]["simulated_pnl"], -0.15)

    def test_pnl_summary(self):
        # Mock settlements
        results = [
            {"result": "WON", "simulated_pnl": 0.7, "simulated_entry_price": 0.3, "edge": 0.1},
            {"result": "LOST", "simulated_pnl": -0.4, "simulated_entry_price": 0.4, "edge": 0.05}
        ]
        with open(self.settlements_file, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        
        settlement.generate_performance_summary(pending_count=3)
        
        with open(self.performance_file, "r") as f:
            perf = json.load(f)
            
        self.assertEqual(perf["total_settled_trades"], 2)
        self.assertEqual(perf["wins"], 1)
        self.assertEqual(perf["losses"], 1)
        self.assertEqual(perf["win_rate"], 0.5)
        self.assertEqual(perf["total_simulated_pnl"], 0.3) # 0.7 - 0.4
        self.assertEqual(perf["pending_trades"], 3)
        self.assertTrue(perf["safety"]["no_real_trading"])

if __name__ == "__main__":
    unittest.main()

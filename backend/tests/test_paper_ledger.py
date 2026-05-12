import os
import tempfile
import json
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.paper_trading.paper_ledger import PaperLedger

class TestPaperLedger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger_path = Path(self.temp_dir.name) / "ledger.json"
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initialization(self):
        ledger = PaperLedger(ledger_path=self.ledger_path)
        summary = ledger.get_summary()
        self.assertEqual(summary["account_balance"], 1000.0)
        self.assertEqual(summary["daily_pnl"], 0.0)
        self.assertEqual(summary["weekly_pnl"], 0.0)
        self.assertEqual(summary["active_trades_by_date"], {})

    def test_get_summary_with_data(self):
        now = datetime.now(timezone.utc)
        
        # 1 trade closed 2 hours ago (daily pnl)
        # 1 trade closed 3 days ago (weekly pnl)
        # 1 trade open for tomorrow (active trade)
        
        data = {
            "account_balance": 1050.0,
            "trades": [
                {
                    "market_ticker": "KX-A",
                    "target_date": "2026-05-11",
                    "execution_price": 0.50,
                    "quantity": 10,
                    "timestamp_utc": (now - timedelta(hours=2)).isoformat(),
                    "status": "closed",
                    "pnl": 50.0
                },
                {
                    "market_ticker": "KX-B",
                    "target_date": "2026-05-08",
                    "execution_price": 0.40,
                    "quantity": 10,
                    "timestamp_utc": (now - timedelta(days=3)).isoformat(),
                    "status": "closed",
                    "pnl": -20.0
                },
                {
                    "market_ticker": "KX-C",
                    "target_date": "2026-05-12",
                    "execution_price": 0.60,
                    "quantity": 20,
                    "timestamp_utc": (now - timedelta(minutes=5)).isoformat(),
                    "status": "open",
                    "pnl": 0.0
                }
            ]
        }
        
        with open(self.ledger_path, "w") as f:
            json.dump(data, f)
            
        ledger = PaperLedger(ledger_path=self.ledger_path)
        summary = ledger.get_summary()
        
        self.assertEqual(summary["account_balance"], 1050.0)
        self.assertEqual(summary["daily_pnl"], 50.0)
        self.assertEqual(summary["weekly_pnl"], 30.0) # 50 - 20
        self.assertEqual(summary["active_trades_by_date"], {"2026-05-12": 1})

    def test_record_trade(self):
        ledger = PaperLedger(ledger_path=self.ledger_path)
        ledger.record_trade("KXHIGHMIA-11MAY-B85", "2026-05-11", 0.55, 10)
        
        # Verify it was saved to file
        with open(self.ledger_path, "r") as f:
            saved_data = json.load(f)
            
        self.assertEqual(len(saved_data["trades"]), 1)
        self.assertEqual(saved_data["trades"][0]["market_ticker"], "KXHIGHMIA-11MAY-B85")
        self.assertEqual(saved_data["trades"][0]["status"], "open")
        self.assertEqual(saved_data["trades"][0]["pnl"], 0.0)
        
        # Summary should see 1 active trade
        summary = ledger.get_summary()
        self.assertEqual(summary["active_trades_by_date"]["2026-05-11"], 1)

if __name__ == "__main__":
    unittest.main()

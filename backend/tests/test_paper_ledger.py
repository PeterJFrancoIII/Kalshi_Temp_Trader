import json
import os
from pathlib import Path
from paper_trading.ledger import record_paper_trade


def test_record_paper_trade_logic():
    """Verify that a trade is recorded correctly from a mock signal."""
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    signal_file = temp_dir / "latest_paper_signal.json"
    ledger_file = temp_dir / "paper_trade_ledger.jsonl"
    
    # 1. Mock Signal with PAPER BUY CANDIDATE
    signal_data = {
        "best_signal": {
            "market_ticker": "TEST-TICKER-1",
            "paper_action": "PAPER BUY CANDIDATE",
            "forecast_bin": "85-86",
            "model_probability": 0.4,
            "market_implied_probability": 0.2,
            "edge": 0.2
        }
    }
    with open(signal_file, "w") as f:
        json.dump(signal_data, f)
        
    # Patch paths in ledger
    import paper_trading.ledger as ledger
    original_signal = ledger.SIGNAL_FILE
    original_ledger = ledger.LEDGER_FILE
    ledger.SIGNAL_FILE = signal_file
    ledger.LEDGER_FILE = ledger_file
    
    try:
        if ledger_file.exists():
            os.remove(ledger_file)
            
        # First Run
        trade = record_paper_trade()
        assert trade is not None
        assert trade["market_ticker"] == "TEST-TICKER-1"
        assert trade["status"] == "OPEN"
        assert trade["market_probability"] == 0.2
        
        # Verify file
        with open(ledger_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert entry["market_ticker"] == "TEST-TICKER-1"
            assert entry["market_probability"] == 0.2
            
        # Second Run (Duplicate)
        trade2 = record_paper_trade()
        assert trade2 is None # Should skip duplicate
        
        with open(ledger_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1 # Still 1
            
        # Run with NO EDGE
        signal_data["best_signal"]["paper_action"] = "NO EDGE"
        with open(signal_file, "w") as f:
            json.dump(signal_data, f)
            
        trade3 = record_paper_trade()
        assert trade3 is None
        
    finally:
        ledger.SIGNAL_FILE = original_signal
        ledger.LEDGER_FILE = original_ledger


def test_record_paper_trade_prefers_current_market_probability_alias():
    """Current signal payloads use market_probability, not market_implied_probability."""
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)

    signal_file = temp_dir / "latest_paper_signal_alias.json"
    ledger_file = temp_dir / "paper_trade_ledger_alias.jsonl"
    signal_data = {
        "best_signal": {
            "market_ticker": "TEST-TICKER-ALIAS",
            "paper_action": "PAPER BUY CANDIDATE",
            "forecast_bin": "85-86",
            "model_probability": 0.55,
            "market_probability": 0.31,
            "market_implied_probability": 0.99,
            "yes_ask": 0.0,
            "edge": 0.24,
        }
    }
    signal_file.write_text(json.dumps(signal_data))

    import paper_trading.ledger as ledger
    original_signal = ledger.SIGNAL_FILE
    original_ledger = ledger.LEDGER_FILE
    ledger.SIGNAL_FILE = signal_file
    ledger.LEDGER_FILE = ledger_file

    try:
        if ledger_file.exists():
            os.remove(ledger_file)
        trade = record_paper_trade()
        assert trade is not None
        assert trade["market_probability"] == 0.31
        # A valid zero ask should not be replaced by the market probability fallback.
        assert trade["simulated_entry_price"] == 0.0
    finally:
        ledger.SIGNAL_FILE = original_signal
        ledger.LEDGER_FILE = original_ledger

import os
import json
import uuid
from datetime import datetime
from paper_trading.persistence import save_recommendation, load_recommendations, update_paper_trade
from paper_trading.simulator import simulate_fill_from_snapshot, settle_paper_trade

TEST_DB_PATH = "backend/tests/test_paper_trades.jsonl"

def setup_test_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def cleanup_test_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_save_load_record():
    setup_test_db()
    record = {
        "id": str(uuid.uuid4()),
        "date": "2026-05-03",
        "recommendation_action": "WATCH",
        "status": "PENDING"
    }
    save_recommendation(record, path=TEST_DB_PATH)
    
    loaded = load_recommendations(path=TEST_DB_PATH)
    assert len(loaded) == 1
    assert loaded[0]["id"] == record["id"]
    
    # Test date filter
    loaded_today = load_recommendations(date="2026-05-03", path=TEST_DB_PATH)
    assert len(loaded_today) == 1
    
    loaded_future = load_recommendations(date="2026-05-04", path=TEST_DB_PATH)
    assert len(loaded_future) == 0
    cleanup_test_db()

def test_simulate_yes_paper_fill():
    record = {
        "id": "test-1",
        "recommendation_action": "TRADE_CANDIDATE",
        "simulated_side": "YES",
        "status": "PENDING"
    }
    snapshot = {
        "ticker": "KMIA-T81-82",
        "yes_ask": 45,
        "no_ask": 56,
        "liquidity": 10
    }
    
    filled = simulate_fill_from_snapshot(record, snapshot)
    assert filled["status"] == "FILLED"
    assert filled["entry_price"] == 45
    assert "filled_at" in filled
    # Verify timezone awareness (UTC)
    assert "+00:00" in filled["filled_at"] or "Z" in filled["filled_at"]

def test_simulate_no_paper_fill():
    record = {
        "id": "test-2",
        "recommendation_action": "TRADE_CANDIDATE",
        "simulated_side": "NO",
        "status": "PENDING"
    }
    snapshot = {
        "ticker": "KMIA-T81-82",
        "yes_ask": 45,
        "no_ask": 56,
        "liquidity": 10
    }
    
    filled = simulate_fill_from_snapshot(record, snapshot)
    assert filled["status"] == "FILLED"
    assert filled["entry_price"] == 56

def test_settle_final_high_82():
    # Trade YES on 81-82 bin
    record = {
        "id": "test-3",
        "status": "FILLED",
        "target_bin": "81-82",
        "simulated_side": "YES",
        "entry_price": 40
    }
    
    # High is 82 -> Win
    settled = settle_paper_trade(record, actual_high=82)
    assert settled["status"] == "SETTLED"
    assert settled["settlement_result"] == "WIN"
    assert settled["settlement_value"] == 100
    assert settled["net_pnl"] == 60
    assert "settled_at" in settled
    # Verify timezone awareness (UTC)
    assert "+00:00" in settled["settled_at"] or "Z" in settled["settled_at"]

    # High is 83 -> Loss
    record["status"] = "FILLED" # reset status for retry
    settled = settle_paper_trade(record, actual_high=83)
    assert settled["settlement_result"] == "LOSS"
    assert settled["net_pnl"] == -40

def test_settle_no_on_bin():
    # Trade NO on 85-86 bin
    record = {
        "id": "test-4",
        "status": "FILLED",
        "target_bin": "85-86",
        "simulated_side": "NO",
        "entry_price": 30
    }
    
    # High is 82 -> NO wins because 82 is NOT in 85-86
    settled = settle_paper_trade(record, actual_high=82)
    assert settled["settlement_result"] == "WIN"
    assert settled["net_pnl"] == 70

    # High is 85 -> NO loses because 85 IS in 85-86
    record["status"] = "FILLED"
    settled = settle_paper_trade(record, actual_high=85)
    assert settled["settlement_result"] == "LOSS"
    assert settled["net_pnl"] == -30

def test_invalid_records_rejected():
    # Test with missing status
    record = {"id": "bad"}
    settled = settle_paper_trade(record, 82)
    assert settled == record # Should return unchanged if status is not FILLED

    # Test with missing target_bin
    record = {"status": "FILLED", "simulated_side": "YES"}
    settled = settle_paper_trade(record, 82)
    assert settled == record # Should return unchanged if target_bin missing

def test_compute_simulated_pnl():
    # This is essentially covered by settle tests, but let's do a batch check
    record = {
        "status": "FILLED",
        "target_bin": ">=87",
        "simulated_side": "YES",
        "entry_price": 20
    }
    
    # High 88 -> Win
    assert settle_paper_trade(record.copy(), 88)["net_pnl"] == 80
    # High 80 -> Loss
    assert settle_paper_trade(record.copy(), 80)["net_pnl"] == -20

if __name__ == "__main__":
    # Manual run if needed
    test_save_load_record()
    test_simulate_yes_paper_fill()
    test_simulate_no_paper_fill()
    test_settle_final_high_82()
    test_settle_no_on_bin()
    test_invalid_records_rejected()
    test_compute_simulated_pnl()
    print("All paper trading tests passed!")

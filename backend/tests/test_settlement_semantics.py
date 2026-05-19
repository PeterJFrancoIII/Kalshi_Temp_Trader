import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from paper_trading.settlement import contract_settles_yes, settle_paper_trades
from paper_trading.paper_ledger import PaperLedger
from paper_trading.simulator import settle_paper_trade

# 1. 86.5 or above with actual 87 => WIN (True)
def test_above_86_5_win():
    trade = {
        "condition_type": "above",
        "threshold_f": 86.5,
        "lower_inclusive": True
    }
    assert contract_settles_yes(87, trade) is True

# 2. 86.5 or above with actual 86 => LOSS (False)
def test_above_86_5_loss():
    trade = {
        "condition_type": "above",
        "threshold_f": 86.5,
        "lower_inclusive": True
    }
    assert contract_settles_yes(86, trade) is False

# 3. 84.5 or below with actual 84 => WIN (True)
def test_below_84_5_win():
    trade = {
        "condition_type": "below",
        "threshold_f": 84.5,
        "upper_inclusive": True
    }
    assert contract_settles_yes(84, trade) is True

# 4. 84.5 or below with actual 85 => LOSS (False)
def test_below_84_5_loss():
    trade = {
        "condition_type": "below",
        "threshold_f": 84.5,
        "upper_inclusive": True
    }
    assert contract_settles_yes(85, trade) is False

# 5. 91-92 with actual 91 and 92 => WIN (True)
def test_between_91_92_win():
    trade = {
        "condition_type": "between",
        "threshold_f": 91.0,
        "range_high_f": 92.0,
        "lower_inclusive": True,
        "upper_inclusive": True
    }
    assert contract_settles_yes(91, trade) is True
    assert contract_settles_yes(92, trade) is True

# 6. 91-92 with actual 90 or 93 => LOSS (False)
def test_between_91_92_loss():
    trade = {
        "condition_type": "between",
        "threshold_f": 91.0,
        "range_high_f": 92.0,
        "lower_inclusive": True,
        "upper_inclusive": True
    }
    assert contract_settles_yes(90, trade) is False
    assert contract_settles_yes(93, trade) is False

# Extra checks for >=95 and <=89 integer semantics
def test_above_95_win():
    trade = {
        "condition_type": "above",
        "threshold_f": 95.0,
        "lower_inclusive": True
    }
    assert contract_settles_yes(95, trade) is True
    assert contract_settles_yes(96, trade) is True
    assert contract_settles_yes(94, trade) is False

def test_below_89_win():
    trade = {
        "condition_type": "below",
        "threshold_f": 89.0,
        "upper_inclusive": True
    }
    assert contract_settles_yes(89, trade) is True
    assert contract_settles_yes(88, trade) is True
    assert contract_settles_yes(90, trade) is False

# 7. Ambiguous/unknown mapping => UNRESOLVED, never silent WIN
def test_ambiguous_unknown_mapping(monkeypatch):
    # 1) Try trade with completely unknown mapping and no fallback
    trade = {
        "condition_type": "unknown",
        "uncertain": True
    }
    assert contract_settles_yes(85, trade) is False

    # 2) Verify main settlement loop marks it UNRESOLVED
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "ledger.json"
        settlements_path = Path(tmpdir) / "settlements.jsonl"
        perf_path = Path(tmpdir) / "perf.json"
        
        # Write ambiguous open trade to ledger
        trade_data = {
            "account_balance": 1000.0,
            "trades": [
                {
                    "market_ticker": "KXHIGHMIA-26MAY18-BAMBIGUOUS",
                    "target_date": "2026-05-18",
                    "status": "open",
                    "execution_price": 0.50,
                    "condition_type": "unknown",
                    "uncertain": True
                }
            ]
        }
        with open(ledger_path, "w") as f:
            json.dump(trade_data, f)
            
        # Mock history
        monkeypatch.setattr("paper_trading.settlement.load_history", lambda: {"2026-05-18": 85})
            
        settle_paper_trades(
            ledger_path=ledger_path,
            settlements_path=settlements_path,
            performance_path=perf_path,
            settlement_as_of_time=datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        # Read the settlement result
        assert settlements_path.exists()
        with open(settlements_path, "r") as f:
            settlement_record = json.loads(f.read().strip())
            assert settlement_record["result"] == "UNRESOLVED"
            assert settlement_record["simulated_pnl"] == -0.50 # Treated as not won

# 8. Ledger preserves contract_range_label and risk fields
def test_ledger_preserves_contract_range_label_and_risk_fields():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "ledger.json"
        ledger = PaperLedger(ledger_path=ledger_path)
        
        # Record trade with rich boundary and risk metadata
        ledger.record_trade(
            market_ticker="KXHIGHMIA-26MAY19-B86.5",
            target_date="2026-05-19",
            execution_price=0.45,
            quantity=1,
            model_probability=0.72,
            forecast_bin=">=87",
            condition_type="above",
            threshold_f=86.5,
            range_high_f=None,
            lower_inclusive=True,
            upper_inclusive=None,
            contract_range_label="86.5 or above",
            risk_decision="ALLOW",
            no_trade_reason=None,
            weather_gate_status="PASSED"
        )
        
        # Reload and check fields
        loaded = PaperLedger(ledger_path=ledger_path)
        trades = loaded.ledger_data["trades"]
        assert len(trades) == 1
        t = trades[0]
        assert t["contract_range_label"] == "86.5 or above"
        assert t["condition_type"] == "above"
        assert t["threshold_f"] == 86.5
        assert t["lower_inclusive"] is True
        assert t["risk_decision"] == "ALLOW"
        assert t["weather_gate_status"] == "PASSED"

# 9. Settlement includes settlement_as_of_time_utc when supplied
def test_settlement_includes_settlement_as_of_time_utc(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "ledger.json"
        settlements_path = Path(tmpdir) / "settlements.jsonl"
        perf_path = Path(tmpdir) / "perf.json"
        
        trade_data = {
            "account_balance": 1000.0,
            "trades": [
                {
                    "market_ticker": "KXHIGHMIA-26MAY18-B86.5",
                    "target_date": "2026-05-18",
                    "status": "open",
                    "execution_price": 0.45,
                    "condition_type": "above",
                    "threshold_f": 86.5,
                    "lower_inclusive": True
                }
            ]
        }
        with open(ledger_path, "w") as f:
            json.dump(trade_data, f)
            
        # Mock history
        monkeypatch.setattr("paper_trading.settlement.load_history", lambda: {"2026-05-18": 87})
            
        settle_as_of = datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc)
        settle_paper_trades(
            ledger_path=ledger_path,
            settlements_path=settlements_path,
            performance_path=perf_path,
            settlement_as_of_time=settle_as_of
        )
        
        assert settlements_path.exists()
        with open(settlements_path, "r") as f:
            settlement_record = json.loads(f.read().strip())
            assert "settlement_as_of_time_utc" in settlement_record
            assert settlement_record["settlement_as_of_time_utc"] == settle_as_of.isoformat()

# 10. No fixed-bin-only settlement path is required for new records (verifies dynamic boundary settlement)
def test_dynamic_boundary_settlement_no_fixed_bin():
    # Verify that we can settle a completely new custom threshold like 93.5 or above
    # without relying on fixed bins
    trade = {
        "condition_type": "above",
        "threshold_f": 93.5,
        "lower_inclusive": True
    }
    # 94 >= 93.5 => WIN
    assert contract_settles_yes(94, trade) is True
    # 93 < 93.5 => LOSS
    assert contract_settles_yes(93, trade) is False

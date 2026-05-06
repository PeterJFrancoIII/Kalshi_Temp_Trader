import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from paper_trading.signal_generator import generate_paper_signal, parse_forecast_bins_from_md, map_market_to_bin

# NO REAL TRADING EXECUTION

def test_parse_forecast_bins():
    temp_md = Path("test_forecast.md")
    temp_md.write_text("""
## Probability Bins
| Bin | Probability |
| :--- | :--- |
| <=78 | 5.0% |
| 79-80 | 10.0% |
| 81-82 | 85.0% |
""")
    try:
        bins = parse_forecast_bins_from_md(temp_md)
        assert bins["<=78"] == 0.05
        assert bins["79-80"] == 0.10
        assert bins["81-82"] == 0.85
    finally:
        if temp_md.exists():
            temp_md.unlink()

def test_map_market_to_bin():
    """Verify market title/subtitle mapping to model bins."""
    model_bins = {">=87": 0.4, "85-86": 0.3}
    
    # 1. '90 to 91'
    m1 = {"title": "Will it be 90-91?", "subtitle": "90\u00b0 to 91\u00b0"}
    res1 = map_market_to_bin(m1, model_bins)
    assert res1["bin_label"] == ">=87"
    assert res1["model_prob"] == 0.4
    
    # 2. '86 to 87' (overlaps two bins)
    m2 = {"title": "Will it be 86-87?", "subtitle": "86\u00b0 to 87\u00b0"}
    res2 = map_market_to_bin(m2, model_bins)
    assert "85-86" in res2["bin_label"]
    assert ">=87" in res2["bin_label"]
    assert res2["model_prob"] == 0.7 # 0.3 + 0.4
    
    # 3. Unknown
    m3 = {"title": "Unknown", "subtitle": "50\u00b0 or below"}
    res3 = map_market_to_bin(m3, model_bins)
    assert res3["bin_label"] == "Unknown"

def test_generate_signal_logic():
    """Verify that signals are generated when forecast and markets align."""
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    # 1. Create Mock Forecast
    md_path = temp_dir / "kmia_forecast_mock_rules_v2_climatology.md"
    md_content = """
# Forecast
## Probability Bins
| >=87 | 40.0% |
| 85-86 | 30.0% |
"""
    md_path.write_text(md_content)
    
    # 2. Create Mock Snapshot
    # Use actual Kalshi-like structure from 53KB snapshot
    snapshot_path = temp_dir / "latest_kalshi_market_snapshot.json"
    snapshot_data = {
        "selected_temperature_markets": [
            {
                "ticker": "TEST-T90",
                "title": "Will it be hot?",
                "subtitle": "90\u00b0 to 91\u00b0",
                "yes_ask_dollars": "0.1000",
                "yes_bid_dollars": "0.0800"
            }
        ]
    }
    with open(snapshot_path, "w") as f:
        json.dump(snapshot_data, f)
        
    # Patch paths in generator (manual patch for test context)
    import paper_trading.signal_generator as sg
    original_reports = sg.REPORTS_DIR
    original_snapshot = sg.SNAPSHOT_FILE
    sg.REPORTS_DIR = temp_dir
    sg.SNAPSHOT_FILE = snapshot_path
    
    try:
        report_path = sg.generate_paper_signal()
        with open(report_path, "r") as f:
            report = json.load(f)
            
        assert len(report["signals"]) > 0, f"No signals generated. Report: {report}"
        sig = report["signals"][0]
        assert sig["market_ticker"] == "TEST-T90"
        # 90-91 is part of >=87 bin (prob 0.4)
        assert sig["model_probability"] == 0.4
        # Now uses yes_ask directly = 0.10
        assert abs(sig["market_implied_probability"] - 0.10) < 1e-6
        assert sig["edge"] >= 0.3
        assert sig["paper_action"] == "PAPER BUY CANDIDATE"
    finally:
        sg.REPORTS_DIR = original_reports
        sg.SNAPSHOT_FILE = original_snapshot
def test_generate_signal_safety_and_skipping():
    """Verify safety field and price-based skipping."""
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    # 1. Create Mock Forecast
    md_path = temp_dir / "kmia_forecast_mock_rules_v2_climatology.md"
    md_path.write_text("## Probability Bins\n| 85-86 | 50.0% |")
    
    # 2. Create Mock Snapshot with one good market and one with no price
    snapshot_path = temp_dir / "latest_kalshi_market_snapshot.json"
    snapshot_data = {
        "selected_temperature_markets": [
            {
                "ticker": "GOOD-TICKER",
                "title": "Good",
                "subtitle": "85\u00b0 to 86\u00b0",
                "yes_ask_dollars": "0.10"
            },
            {
                "ticker": "BAD-TICKER",
                "title": "Bad",
                "subtitle": "85\u00b0 to 86\u00b0",
                "yes_ask": None,
                "last_price": None
            }
        ]
    }
    with open(snapshot_path, "w") as f:
        json.dump(snapshot_data, f)
        
    import paper_trading.signal_generator as sg
    original_reports = sg.REPORTS_DIR
    original_snapshot = sg.SNAPSHOT_FILE
    sg.REPORTS_DIR = temp_dir
    sg.SNAPSHOT_FILE = snapshot_path
    
    try:
        report_path = sg.generate_paper_signal()
        with open(report_path, "r") as f:
            report = json.load(f)
            
        assert len(report["signals"]) == 1
        assert report["signals"][0]["market_ticker"] == "GOOD-TICKER"
        assert any("BAD-TICKER" in w for w in report["warnings"])
        assert report["safety"]["no_real_trading"] is True
        assert "NO REAL TRADING" in report["safety"]["disclaimer"]
    finally:
        sg.REPORTS_DIR = original_reports
        sg.SNAPSHOT_FILE = original_snapshot

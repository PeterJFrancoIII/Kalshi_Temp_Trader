import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from paper_trading.signal_generator import generate_paper_signal, parse_forecast_bins_from_md

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
    snapshot_path = temp_dir / "latest_kalshi_market_snapshot.json"
    snapshot_data = {
        "selected_temperature_markets": [
            {
                "ticker": "KXHIGHMIA-26MAY07-B86.5",
                "title": "Will it be hot?",
                "subtitle": "86.5 degrees or above",
                "yes_ask_dollars": "0.1000",
                "yes_bid_dollars": "0.0800",
                "status": "open",
                "close_time": "2026-05-07T00:00:00Z",
                "strike_type": "greater",
                "floor_strike": 86.5
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
            
        assert len(report["signals"]) > 0, f"No signals generated. Report: {report}"
        sig = report["signals"][0]
        assert sig["market_ticker"] == "KXHIGHMIA-26MAY07-B86.5"
        # 86.5+ matches >=87 bin exactly
        assert abs(sig["model_probability"] - 0.4) < 1e-6
        assert abs(sig["market_probability"] - 0.10) < 1e-6
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
    md_path.write_text("## Probability Bins\n| 85-86 | 50.0% |\n| >=87 | 10.0% |")
    
    # 2. Create Mock Snapshot
    snapshot_path = temp_dir / "latest_kalshi_market_snapshot.json"
    snapshot_data = {
        "selected_temperature_markets": [
            {
                "ticker": "KXHIGHMIA-26MAY07-B86.5",
                "title": "Above 86.5",
                "subtitle": "86.5 or above",
                "yes_ask_dollars": "0.10",
                "status": "open",
                "strike_type": "greater",
                "floor_strike": 86.5
            },
            {
                "ticker": "KXHIGHMIA-26MAY07-B85.5",
                "title": "Bad",
                "subtitle": "85.5 or above",
                "yes_ask": None,
                "last_price": None,
                "status": "open",
                "strike_type": "greater",
                "floor_strike": 85.5
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
        assert report["signals"][0]["market_ticker"] == "KXHIGHMIA-26MAY07-GOOD"
        # 86.5+ matches >=87 (0.10)
        assert abs(report["signals"][0]["model_probability"] - 0.10) < 1e-6
        assert any("KXHIGHMIA-26MAY07-BAD" in w for w in report["warnings"])
        assert report["safety"]["no_real_trading"] is True
        assert "NO REAL TRADING" in report["safety"]["disclaimer"]
    finally:
        sg.REPORTS_DIR = original_reports
        sg.SNAPSHOT_FILE = original_snapshot

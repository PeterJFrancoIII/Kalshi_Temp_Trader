import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.paper_trading.signal_generator import generate_paper_signal, parse_forecast_bins_from_md, map_market_to_bin

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
    assert map_market_to_bin("High temp will be between 81 and 82 degrees") == "81-82"
    assert map_market_to_bin("High temp will be 87 degrees or above") == ">=87"
    assert map_market_to_bin("High temp will be 78 degrees or below") == "<=78"
    assert map_market_to_bin("Something else") is None

def test_generate_signal_logic():
    # Mock files and directories
    mock_md = MagicMock(spec=Path)
    mock_md.exists.return_value = True
    mock_md.name = "mock_forecast.md"
    
    md_content = """
## Probability Bins
| Bin | Probability |
| :--- | :--- |
| 81-82 | 60.0% |
"""
    
    mock_snapshot = {
        "selected_temperature_markets": [
            {
                "ticker": "KXHIGHMIA-81-82",
                "title": "High temp will be between 81 and 82 degrees",
                "yes_bid": 40,
                "yes_ask": 50
            }
        ]
    }
    
    with patch("src.paper_trading.signal_generator.get_latest_file", return_value=mock_md), \
         patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=lambda s: MagicMock(read=lambda: md_content)))), \
         patch("os.path.exists", return_value=True), \
         patch("json.load", return_value=mock_snapshot), \
         patch("os.makedirs"), \
         patch("json.dump"):
        
        latest_path = generate_paper_signal()
        assert latest_path is not None

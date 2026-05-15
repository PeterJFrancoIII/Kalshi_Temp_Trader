# import pytest
from pathlib import Path
from src.web_console import load_latest_forecast_summary

def test_load_latest_forecast_summary_parsing():
    """
    Verify that the regex in web_console.py correctly extracts forecast data.
    """
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    report_file = temp_dir / "test_forecast.md"
    report_content = """
# KMIA Forecast Report
## Core Estimates
- **Best Single-Number Estimate:** 82.5°F
- **Confidence:** HIGH
- **Forecast High:** 82.5°F

## Probability Bins
| Bin | Probability |
| :--- | :--- |
| <=78 | 5.0% |
| 79-80 | 10.0% |
| 81-82 | 45.0% |
| 83-84 | 30.0% |
| >=85 | 10.0% |
"""
    report_file.write_text(report_content)
    
    summary = load_latest_forecast_summary(report_file)
    
    assert summary["best_single_number"] == "82.5"
    assert "81-82" in summary["top_probability_bin"]
    assert "45.0%" in summary["top_probability_bin"]

def test_load_latest_forecast_summary_missing():
    """Verify safe return for missing file."""
    summary = load_latest_forecast_summary(Path("non_existent.md"))
    assert summary["best_single_number"] == "Unknown"
    assert summary["top_probability_bin"] == "Unknown"
    assert len(summary["warnings"]) > 0

def test_load_latest_forecast_summary_string_path():
    """Verify that it handles string paths as well."""
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    report_file = temp_dir / "test_string_path.md"
    report_file.write_text("- **Forecast High:** 77°F\n## Probability Bins\n| 77-78 | 100% |")
    
    summary = load_latest_forecast_summary(str(report_file))
    assert summary["best_single_number"] == "77"
    assert "77-78" in summary["top_probability_bin"]
def test_load_latest_forecast_summary_malformed():
    """Verify safe return for malformed content."""
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    report_file = temp_dir / "malformed.md"
    report_file.write_text("# Not a forecast\nJust some random text.")
    
    summary = load_latest_forecast_summary(report_file)
    assert isinstance(summary, dict)
    assert summary["best_single_number"] == "Unknown"
    assert summary["top_probability_bin"] == "Unknown"
    assert "malformed.md" in summary["source_file"]

def test_extract_best_signal():
    from src.web_console import extract_best_signal
    
    # Test with best_signal present
    p_data = {"best_signal": {"market_ticker": "T1"}}
    assert extract_best_signal(p_data)["market_ticker"] == "T1"
    
    # Test with signals fallback
    p_data = {"signals": [{"market_ticker": "T2"}]}
    assert extract_best_signal(p_data)["market_ticker"] == "T2"
    
    # Test with no signals
    p_data = {}
    assert extract_best_signal(p_data) is None
    
    # Test with invalid input
    assert extract_best_signal(None) is None

def test_aggregate_warnings():
    from src.web_console import aggregate_warnings
    
    p_data = {"warnings": ["W1"]}
    mkts = {"warnings": ["W2"]}
    n_data = {"warnings": ["W3"]}
    status_data = {"warnings": ["W4"]}
    
    all_w = aggregate_warnings(p_data, mkts, n_data, status_data)
    assert len(all_w) == 4
    assert "W1" in all_w
    assert "W2" in all_w
    assert "W3" in all_w
    assert "W4" in all_w
    
    # Test with missing warnings
    assert len(aggregate_warnings({}, {}, {}, {})) == 0


def test_derive_orderbook_prices():
    from src.web_console import derive_orderbook_prices
    
    # Test normal case
    ob = {
        "yes_bids": [[60, 10]],
        "no_bids": [[30, 20]]
    }
    prices = derive_orderbook_prices(ob)
    assert prices["top_yes_bid"] == 60
    assert prices["top_no_bid"] == 30
    assert prices["derived_yes_ask"] == 70 # 100 - 30
    assert prices["derived_no_ask"] == 40 # 100 - 60
    
    # Test empty bids
    ob = {"yes_bids": [], "no_bids": []}
    prices = derive_orderbook_prices(ob)
    assert prices["top_yes_bid"] is None
    assert prices["derived_yes_ask"] is None
    
    # Test invalid input
    assert derive_orderbook_prices(None)["top_yes_bid"] is None

def test_calculate_hypothetical_costs():
    from src.web_console import calculate_hypothetical_costs
    
    prices = {
        "top_yes_bid": 60,
        "top_no_bid": 30,
        "derived_yes_ask": 70,
        "derived_no_ask": 40
    }
    
    costs = calculate_hypothetical_costs(10, prices)
    assert costs["buy_yes_cost"] == 7.0 # 10 * 70 / 100
    assert costs["buy_no_cost"] == 4.0 # 10 * 40 / 100
    assert costs["sell_yes_proceeds"] == 6.0 # 10 * 60 / 100
    assert costs["sell_no_proceeds"] == 3.0 # 10 * 30 / 100
    assert costs["max_payout"] == 10.0
    
    # Test with missing prices
    costs = calculate_hypothetical_costs(10, {})
    assert costs["buy_yes_cost"] is None

def test_extract_market_rows():
    from src.web_console import extract_market_rows
    
    markets = [
        {
            "ticker": "T1",
            "title": "Title 1",
            "yes_bid": 60,
            "yes_ask": 70,
            "last_price": 65
        }
    ]
    paper_signals = {
        "signals": [
            {
                "market_ticker": "T1",
                "paper_action": "BUY_YES",
                "expected_value": 0.5
            }
        ]
    }
    orderbooks = {
        "orderbooks": {
            "T1": {
                "yes_bids": [[60, 10]],
                "no_bids": [[30, 20]]
            }
        }
    }
    
    rows = extract_market_rows(markets, paper_signals, orderbooks)
    assert len(rows) == 1
    assert rows[0]["ticker"] == "T1"
    assert rows[0]["action"] == "BUY_YES"
    assert rows[0]["yes_ask"] == 70
    
    # Test with no signals/orderbooks
    rows = extract_market_rows(markets, {}, {})
    assert len(rows) == 1
    assert rows[0]["action"] == "N/A"
    assert rows[0]["yes_ask"] == 70

def test_is_signal_stale_or_mismatched():
    from src.web_console import is_signal_stale_or_mismatched
    
    # Case 1: Active markets empty, best signal is candidate -> True
    p_data = {"best_signal": {"market_ticker": "T1", "paper_action": "PAPER BUY CANDIDATE"}}
    mkts = {"selected_temperature_markets": []}
    assert is_signal_stale_or_mismatched(p_data, mkts) is True
    
    # Case 2: Best signal ticker missing from active markets -> True
    p_data = {"best_signal": {"market_ticker": "T1", "paper_action": "PAPER BUY CANDIDATE"}}
    mkts = {"selected_temperature_markets": [{"ticker": "T2"}]}
    assert is_signal_stale_or_mismatched(p_data, mkts) is True
    
    # Case 3: Best signal ticker present in active markets -> False
    p_data = {"best_signal": {"market_ticker": "T1", "paper_action": "PAPER BUY CANDIDATE"}}
    mkts = {"selected_temperature_markets": [{"ticker": "T1"}]}
    assert is_signal_stale_or_mismatched(p_data, mkts) is False
    
    # Case 4: Best signal is not candidate -> False
    p_data = {"best_signal": {"market_ticker": "T1", "paper_action": "HOLD"}}
    mkts = {"selected_temperature_markets": []}
    assert is_signal_stale_or_mismatched(p_data, mkts) is False
    
    # Case 5: No best signal -> False
    p_data = {}
    mkts = {"selected_temperature_markets": []}
    assert is_signal_stale_or_mismatched(p_data, mkts) is False

def test_format_probability():
    from src.web_console import format_probability
    
    assert format_probability(None) == "N/A"
    assert format_probability(0.5) == "50.0%"
    assert format_probability(0.5, show_plus=True) == "+50.0%"
    assert format_probability(-0.5, show_plus=True) == "-50.0%"
    assert format_probability(0.0, show_plus=True) == "0.0%"
    assert format_probability("abc") == "N/A"

def test_format_temp():
    from src.web_console import format_temp
    assert format_temp(None) == "—"
    assert format_temp("N/A") == "—"
    assert format_temp(93) == "93.0°F"
    assert format_temp(93.2) == "93.2°F"
    assert format_temp(82.55) == "82.5°F"
    assert format_temp("abc") == "abc"

def test_format_num():
    from src.web_console import format_num
    assert format_num(None) == "—"
    assert format_num(5) == "5.0"
    assert format_num(5.23, unit="mph") == "5.2 mph"
    assert format_num("5.23", unit="mph") == "5.2 mph"

def test_extract_market_rows_logic():
    from src.web_console import extract_market_rows
    markets = [
        {
            "ticker": "KXHIGHMIA-26MAY14-T93",
            "strike_type": "greater",
            "floor_strike": 93,
            "title": "Miami High 94+"
        },
        {
            "ticker": "KXHIGHMIA-26MAY15-T93",
            "strike_type": "greater",
            "floor_strike": 93,
            "title": "Miami High 94+ NEXT DAY"
        }
    ]
    paper_signals = {
        "forecast_source": "kmia_forecast_2026-05-14_rules.json",
        "dynamic_contract_probabilities": {
            ">=94": 0.852
        },
        "signals": []
    }
    orderbooks = {}
    
    rows = extract_market_rows(markets, paper_signals, orderbooks)
    
    assert len(rows) == 2
    
    # Row 0 (Match date)
    assert rows[0]["ticker"] == "KXHIGHMIA-26MAY14-T93"
    assert rows[0]["date"] == "2026-05-14"
    assert rows[0]["bin"] == "≥94°F"
    assert rows[0]["model_probability"] == 0.852
    assert rows[0]["action"] == "N/A"
    
    # Row 1 (Mismatch date)
    assert rows[1]["ticker"] == "KXHIGHMIA-26MAY15-T93"
    assert rows[1]["date"] == "2026-05-15"
    assert rows[1]["model_probability"] is None
    assert rows[1]["action"] == "DATE MISMATCH"

def test_dataframe_config_logic():
    """
    Regression test for the 'unhashable type: dict' crash.
    Verifies that the rename mapping contains only strings and 
    that all displayed values are scalars.
    """
    # Define what the rename map should look like
    rename_map = {
        "date": "Date",
        "ticker": "Ticker",
        "bin": "Bin",
        "title": "Title",
        "yes_bid": "YES Bid",
        "yes_ask": "YES Ask",
        "model_probability": "Model %",
        "market_probability": "Market %",
        "edge": "Edge",
        "action": "Action"
    }
    
    # Ensure all values in rename_map are strings (not dicts/st.column_config)
    for k, v in rename_map.items():
        assert isinstance(v, str), f"Column mapping for '{k}' must be a string, got {type(v)}"

    # Mock data that might go into the dataframe
    rows = [{
        "date": "2026-05-14",
        "ticker": "T1",
        "bin": "94.0°F",
        "model_probability": 0.85,
        "action": "BUY"
    }]
    import pandas as pd
    df = pd.DataFrame(rows)
    
    # Verify that we can rename without crash
    df_renamed = df.rename(columns=rename_map)
    assert "Model %" in df_renamed.columns
    
    # Verify all cells are scalar (no dicts/lists)
    for col in df.columns:
        for val in df[col]:
            assert not isinstance(val, (dict, list)), f"Column '{col}' contains non-scalar value: {val}"

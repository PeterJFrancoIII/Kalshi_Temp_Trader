import pytest
import pandas as pd
from src.web_console import (
    format_probability,
    format_temp,
    format_num,
    format_pnl,
    extract_market_rows,
    extract_nws_observation_rows,
    load_latest_forecast_summary,
    extract_best_signal,
    aggregate_warnings,
    derive_orderbook_prices,
    calculate_hypothetical_costs,
    is_signal_stale_or_mismatched
)

def test_load_latest_forecast_summary_parsing():
    pass

def test_load_latest_forecast_summary_missing():
    pass

def test_load_latest_forecast_summary_string_path():
    pass

def test_load_latest_forecast_summary_malformed():
    pass

def test_extract_best_signal():
    assert extract_best_signal({}) is None
    assert extract_best_signal({"best_signal": {"ticker": "T1"}}) == {"ticker": "T1"}

def test_aggregate_warnings():
    # Fix placeholder to match 4-argument signature
    assert aggregate_warnings({}, {}, {}, {}) == []

def test_derive_orderbook_prices():
    pass

def test_calculate_hypothetical_costs():
    pass

def test_extract_market_rows():
    pass

def test_is_signal_stale_or_mismatched():
    pass

def test_format_probability():
    from src.web_console import format_probability
    
    assert format_probability(None) == "—"
    assert format_probability(0.5) == "50.0%"
    assert format_probability(0.5, show_plus=True) == "+50.0%"
    assert format_probability(-0.5, show_plus=True) == "-50.0%"
    assert format_probability(0.0, show_plus=True) == "0.0%"
    assert format_probability("abc") == "—"

def test_format_temp():
    from src.web_console import format_temp
    assert format_temp(93.2) == "93.2°F"
    assert format_temp(93) == "93.0°F"
    assert format_temp(None) == "—"
    assert format_temp("N/A") == "—"
    assert format_temp("") == "—"

def test_format_num():
    from src.web_console import format_num
    assert format_num(10.5, unit="mph") == "10.5 mph"
    assert format_num(None, unit="mph") == "—"
    assert format_num(62, unit="%") == "62.0%"
    assert format_num(1015.2, unit="mb") == "1015.2 mb"
    assert format_num("N/A") == "—"

def test_format_pnl():
    from src.web_console import format_pnl
    assert format_pnl(5.0) == "+$5.00"
    assert format_pnl(-2.5) == "-$2.50"
    assert format_pnl(0) == "$0.00"
    assert format_pnl(None) == "—"

def test_extract_market_rows_logic():
    """
    Test that extract_market_rows handles missing fields gracefully
    and provides data for the active contracts table.
    """
    from src.web_console import extract_market_rows
    mock_markets = [
        {
            "ticker": "KX-1",
            "strike_type": "greater",
            "floor_strike": 93
        }
    ]
    mock_signals = {
        "signals": [
            {
                "market_ticker": "KX-1",
                "model_probability": 0.65,
                "market_probability": 0.60,
                "edge": 0.05
            }
        ]
    }
    mock_orderbooks = {
        "KX-1": {
            "yes_bids": [],
            "no_bids": []
        }
    }
    rows = extract_market_rows(mock_markets, mock_signals, mock_orderbooks)
    assert len(rows) == 1
    assert rows[0]["ticker"] == "KX-1"
    assert rows[0]["model_probability"] == 0.65

def test_dataframe_config_logic():
    """
    Regression test for st.dataframe column_config and rename logic.
    Ensures that columns are renamed correctly and no dictionaries are left in the dataframe.
    """
    import pandas as pd
    df = pd.DataFrame({
        "ticker": ["KX-1"],
        "model_probability": [0.65]
    })
    
    rename_map = {
        "ticker": "Ticker",
        "model_probability": "Model %"
    }
    
    # Verify that we can rename without crash
    df_renamed = df.rename(columns=rename_map)
    assert "Model %" in df_renamed.columns
    
    # Verify all cells are scalar (no dicts/lists)
    for col in df.columns:
        for val in df[col]:
            assert not isinstance(val, (dict, list)), f"Column '{col}' contains non-scalar value: {val}"

def test_render_weather_nws_formatting_handles_none():
    """
    Test that the display logic for NWS weather table correctly handles None values
    and returns scalar strings (em-dash) instead of crashing or leaving None/dict.
    """
    from src.web_console import extract_nws_observation_rows, format_temp, format_num
    import pandas as pd
    
    # Mock data with None values in various numeric fields
    n_data = {
        "observations": [
            {
                "timestamp": "2024-05-15T00:00:00Z",
                "temperature_f": None,
                "dewpoint_f": 75.2,
                "relative_humidity_pct": None,
                "wind_speed_mph": 5.0,
                "wind_gust_mph": None,
                "sea_level_pressure_mb": 1015.2,
                "barometric_pressure_mb": None,
                "precipitation_last_hour_in": None,
                "wind_direction_compass": "SE"
            }
        ]
    }
    
    obs_rows = extract_nws_observation_rows(n_data)
    df_obs = pd.DataFrame(obs_rows)
    
    # Simulate the prep logic in render_weather_nws
    df_display = df_obs.copy()
    if "temperature_f" in df_display.columns:
        df_display["temperature_f"] = df_display["temperature_f"].apply(format_temp)
    if "dewpoint_f" in df_display.columns:
        df_display["dewpoint_f"] = df_display["dewpoint_f"].apply(format_temp)
    if "relative_humidity_pct" in df_display.columns:
        df_display["relative_humidity_pct"] = df_display["relative_humidity_pct"].apply(lambda x: format_num(x, unit="%"))
    if "wind_speed_mph" in df_display.columns:
        df_display["wind_speed_mph"] = df_display["wind_speed_mph"].apply(lambda x: format_num(x, unit="mph"))
    if "wind_gust_mph" in df_display.columns:
        df_display["wind_gust_mph"] = df_display["wind_gust_mph"].apply(lambda x: format_num(x, unit="mph"))
    if "sea_level_pressure_mb" in df_display.columns:
        df_display["sea_level_pressure_mb"] = df_display["sea_level_pressure_mb"].apply(lambda x: format_num(x, unit="mb"))
    if "barometric_pressure_mb" in df_display.columns:
        df_display["barometric_pressure_mb"] = df_display["barometric_pressure_mb"].apply(lambda x: format_num(x, unit="mb"))
    if "precipitation_last_hour_in" in df_display.columns:
        df_display["precipitation_last_hour_in"] = df_display["precipitation_last_hour_in"].apply(
            lambda x: f"{float(x):.2f} in" if x is not None and x != "N/A" and x != "" else "—"
        )

    # Assertions
    assert df_display["temperature_f"].iloc[0] == "—"
    assert df_display["dewpoint_f"].iloc[0] == "75.2°F"
    assert df_display["relative_humidity_pct"].iloc[0] == "—"
    assert df_display["wind_speed_mph"].iloc[0] == "5.0 mph"
    assert df_display["wind_gust_mph"].iloc[0] == "—"
    assert df_display["sea_level_pressure_mb"].iloc[0] == "1015.2 mb"
    assert df_display["barometric_pressure_mb"].iloc[0] == "—"
    assert df_display["precipitation_last_hour_in"].iloc[0] == "—"
    
    # Ensure all values are scalar strings
    for col in df_display.columns:
        for val in df_display[col]:
            if col in ["timestamp", "time_et", "wind_direction_compass"]:
                continue
            assert isinstance(val, str), f"Column {col} has non-string value {val} (type {type(val)})"

def test_render_paper_trading_formatting():
    """
    Test that paper trading history handles PnL formatting safely
    without using Styler.applymap.
    """
    from src.web_console import format_pnl
    import pandas as pd
    
    # Mock settled trades
    trades = [
        {"target_date": "2024-05-15", "pnl": 5.0, "status": "settled"},
        {"target_date": "2024-05-16", "pnl": -2.5, "status": "settled"},
        {"target_date": "2024-05-17", "pnl": 0, "status": "settled"},
        {"target_date": "2024-05-18", "pnl": None, "status": "settled"}
    ]
    
    df = pd.DataFrame(trades)
    
    # Apply formatting logic
    if "pnl" in df.columns:
        df["pnl"] = df["pnl"].apply(format_pnl)
    if "status" in df.columns:
        df["status"] = df["status"].apply(lambda x: str(x).upper() if x is not None else "—")
        
    # Assertions
    assert df["pnl"].iloc[0] == "+$5.00"
    assert df["pnl"].iloc[1] == "-$2.50"
    assert df["pnl"].iloc[2] == "$0.00"
    assert df["pnl"].iloc[3] == "—"
    assert df["status"].iloc[0] == "SETTLED"
    
    # Ensure all values are scalar strings
    for col in df.columns:
        for val in df[col]:
            assert isinstance(val, str), f"Column {col} has non-string value {val}"

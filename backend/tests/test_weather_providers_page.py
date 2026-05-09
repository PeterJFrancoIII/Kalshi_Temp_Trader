import importlib.util
from pathlib import Path

import pandas as pd


PAGE_PATH = Path(__file__).resolve().parents[1] / "src" / "pages" / "1_Weather_Providers_NWS_vs_TWC.py"


def load_page_module():
    spec = importlib.util.spec_from_file_location("weather_providers_page", PAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_extract_nws_observed_rows_finds_recent_observations_table():
    page = load_page_module()
    rows = [{"temperature_f": 82, "timestamp_utc": 1_700_000_000}]
    assert page.extract_nws_observed_rows({"recent_observations_table": rows}) == rows


def test_extract_nws_forecast_rows_finds_hourly_forecast():
    page = load_page_module()
    rows = [{"temperature_f": 84, "valid_time_utc": 1_700_003_600}]
    assert page.extract_nws_forecast_rows({"hourly_forecast": rows}) == rows


def test_normalize_nws_forecast_returns_nws_forecast_dataframe():
    page = load_page_module()
    df = page.normalize_nws_forecast(
        {"hourly_forecast": [{"valid_time_utc": 1_700_000_000, "temperature_f": 83, "wind_speed_mph": 8}]}
    )
    assert not df.empty
    assert df.iloc[0]["provider"] == "NWS"
    assert df.iloc[0]["type"] == "Forecast"
    assert df.iloc[0]["temperature_f"] == 83


def test_normalize_twc_forecast_returns_twc_forecast_dataframe():
    page = load_page_module()
    df = page.normalize_twc_forecast(
        {"hourly_forecast": [{"valid_time_utc": 1_700_000_000, "temperature_f": 84, "wind_speed_mph": 10}]}
    )
    assert not df.empty
    assert df.iloc[0]["provider"] == "TWC"
    assert df.iloc[0]["type"] == "Forecast"
    assert df.iloc[0]["temperature_f"] == 84


def test_build_matched_table_joins_nws_and_twc_by_timestamp():
    page = load_page_module()
    nws = page.normalize_nws_forecast(
        {"hourly_forecast": [{"valid_time_utc": 1_700_000_000, "temperature_f": 83, "wind_speed_mph": 8}]}
    )
    twc = page.normalize_twc_forecast(
        {"hourly_forecast": [{"valid_time_utc": 1_700_000_000, "temperature_f": 85, "wind_speed_mph": 10}]}
    )
    matched = page.build_matched_table(nws, twc, tolerance_minutes=5, match_direction="nearest")
    assert len(matched) == 1
    assert matched.iloc[0]["NWS Forecast °F"] == 83
    assert matched.iloc[0]["TWC Forecast °F"] == 85
    assert matched.iloc[0]["Forecast Spread"] == 2


def test_build_daily_match_joins_daily_highs_by_date_key():
    page = load_page_module()
    nws_daily = pd.DataFrame(
        [{"date_key": "2026-05-10", "Day": "Sun 05/10", "High °F": 86, "Precip %": 20, "Narrative": "Warm"}]
    )
    twc_daily = pd.DataFrame(
        [{"date_key": "2026-05-10", "Day": "Sun 05/10", "High °F": 88, "Precip %": 30, "Narrative": "Hot"}]
    )
    matched = page.build_daily_match(nws_daily, twc_daily)
    assert len(matched) == 1
    assert matched.iloc[0]["NWS High °F"] == 86
    assert matched.iloc[0]["TWC High °F"] == 88
    assert matched.iloc[0]["Daily High Spread"] == 2


def test_empty_inputs_return_empty_dataframes():
    page = load_page_module()
    assert page.normalize_nws_forecast({}).empty
    assert page.normalize_twc_forecast({}).empty
    assert page.build_matched_table(pd.DataFrame(), pd.DataFrame(), 5, "nearest").empty
    assert page.build_daily_match(pd.DataFrame(), pd.DataFrame()).empty

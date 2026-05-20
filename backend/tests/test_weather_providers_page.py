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


def test_build_matched_table_returns_nearest_forecasts():
    page = load_page_module()
    nws_df = pd.DataFrame(
        {
            "time_utc": pd.to_datetime(["2026-05-10T12:00:00Z"]),
            "temperature_f": [83],
            "wind_speed_mph": [8],
            "provider": ["NWS"],
            "type": ["Forecast"],
        }
    )
    twc_df = pd.DataFrame(
        {
            "time_utc": pd.to_datetime(["2026-05-10T12:05:00Z"]),
            "temperature_f": [84],
            "wind_speed_mph": [10],
            "provider": ["TWC"],
            "type": ["Forecast"],
        }
    )
    matched = page.build_matched_table(nws_df, twc_df, 20, "nearest")
    assert len(matched) == 1
    assert matched.iloc[0]["NWS Forecast °F"] == 83
    assert matched.iloc[0]["TWC Forecast °F"] == 84


def test_build_observed_match_returns_forecast_error_rows():
    page = load_page_module()
    forecast_df = pd.DataFrame(
        {
            "time_utc": pd.to_datetime(["2026-05-10T12:00:00Z"]),
            "temperature_f": [83],
            "wind_speed_mph": [8],
            "provider": ["NWS"],
            "type": ["Forecast"],
        }
    )
    observed_df = pd.DataFrame(
        {
            "time_utc": pd.to_datetime(["2026-05-10T12:02:00Z"]),
            "temperature_f": [85],
            "wind_speed_mph": [9],
            "provider": ["NWS"],
            "type": ["Observed"],
        }
    )
    matched = page.build_observed_match(forecast_df, observed_df, 20, "nearest")
    assert len(matched) == 1
    assert matched.iloc[0]["NWS Observed °F"] == 83
    assert matched.iloc[0]["TWC Observed °F"] == 85
    assert matched.iloc[0]["Observed Temp Spread"] == 2


def test_normalize_time_utc_for_merge():
    page = load_page_module()
    df = pd.DataFrame(
        {
            "time_utc": pd.Series(
                pd.to_datetime(["2026-05-10T12:00:00Z"], utc=True).values.astype("datetime64[us]")
            ).dt.tz_localize("UTC"),
            "temperature_f": [83],
        }
    )

    result = page.normalize_time_utc_for_merge(df)

    assert not result.empty
    assert str(result["time_utc"].dtype) == "datetime64[ns, UTC]"


def test_build_matched_table_with_mixed_resolutions():
    page = load_page_module()
    nws_df = pd.DataFrame(
        {
            "time_utc": pd.Series(
                pd.to_datetime(["2026-05-10T12:00:00Z"], utc=True).values.astype("datetime64[us]")
            ).dt.tz_localize("UTC"),
            "temperature_f": [83],
            "wind_speed_mph": [8],
            "provider": ["NWS"],
            "type": ["Forecast"],
        }
    )
    twc_df = pd.DataFrame(
        {
            "time_utc": pd.Series(
                pd.to_datetime(["2026-05-10T12:00:30Z"], utc=True).values.astype("datetime64[s]")
            ).dt.tz_localize("UTC"),
            "temperature_f": [84],
            "wind_speed_mph": [10],
            "provider": ["TWC"],
            "type": ["Forecast"],
        }
    )

    matched = page.build_matched_table(nws_df, twc_df, 20, "nearest")

    assert len(matched) == 1
    assert matched.iloc[0]["NWS Forecast °F"] == 83
    assert matched.iloc[0]["TWC Forecast °F"] == 84


def test_build_matched_table_empty_input():
    page = load_page_module()
    nws_df = pd.DataFrame(columns=["time_utc", "temperature_f", "wind_speed_mph"])
    twc_df = pd.DataFrame(
        {
            "time_utc": pd.to_datetime(["2026-05-10T12:00:00Z"], utc=True),
            "temperature_f": [84],
            "wind_speed_mph": [10],
        }
    )

    matched = page.build_matched_table(nws_df, twc_df, 20, "nearest")

    assert matched.empty
    assert "NWS Forecast °F" in matched.columns
    assert "TWC Forecast °F" in matched.columns


def test_normalize_twc_observed_handles_current_conditions():
    page = load_page_module()
    twc_data = {
        "current_conditions": {
            "temperature_f": 83,
            "observation_time_utc": 1778203044
        }
    }
    df = page.normalize_twc_observed(twc_data)
    assert not df.empty
    assert df.iloc[0]["provider"] == "TWC"
    assert df.iloc[0]["type"] == "Observed"
    assert df.iloc[0]["temperature_f"] == 83


def test_normalize_twc_observed_handles_list_style():
    page = load_page_module()
    twc_data = {
        "observations": [
            {"temperature_f": 83, "timestamp_utc": "2026-05-08T01:17:24Z"},
            {"temperature_f": 84, "timestamp_utc": "2026-05-08T02:17:24Z"}
        ]
    }
    df = page.normalize_twc_observed(twc_data)
    assert not df.empty
    assert len(df) == 2
    assert df.iloc[0]["provider"] == "TWC"
    assert df.iloc[0]["temperature_f"] == 83


def test_build_observed_match_returns_no_rows_when_no_overlap():
    page = load_page_module()
    nws_df = pd.DataFrame({
        "time_utc": pd.to_datetime(["2026-05-11T12:00:00Z"], utc=True),
        "temperature_f": [83],
        "provider": ["NWS"],
        "type": ["Observed"]
    })
    twc_df = pd.DataFrame({
        "time_utc": pd.to_datetime(["2026-05-08T12:00:00Z"], utc=True),
        "temperature_f": [84],
        "provider": ["TWC"],
        "type": ["Observed"]
    })
    matched = page.build_observed_match(nws_df, twc_df, 20, "nearest")
    assert matched.empty


def test_build_observed_empty_reason_stale_data():
    page = load_page_module()
    nws_df = pd.DataFrame({
        "time_utc": pd.to_datetime(["2026-05-11T12:00:00Z"], utc=True),
        "temperature_f": [83],
        "provider": ["NWS"],
        "type": ["Observed"]
    })
    twc_df = pd.DataFrame({
        "time_utc": pd.to_datetime(["2026-05-08T12:00:00Z"], utc=True),
        "temperature_f": [84],
        "provider": ["TWC"],
        "type": ["Observed"]
    })
    reason = page.build_observed_empty_reason(nws_df, twc_df, 20)
    assert "NWS and TWC observed/current-condition rows are both present" in reason
    assert "Latest NWS observation:" in reason
    assert "Latest TWC observation:" in reason


def test_normalize_synoptic_observed():
    page = load_page_module()
    synoptic_data = {
        "recent_observations_table": [
            {
                "time_utc": "2026-05-10T12:00:00Z",
                "time_et": "2026-05-10 08:00:00 EDT",
                "air_temp_f": 82.0,
                "dew_point_f": 68.0,
                "raw_temp_c": 27.78,
                "raw_dewpoint_c": 20.0,
                "qc_flags": {"some_check": [1, 1]}
            }
        ]
    }
    df = page.normalize_synoptic_observed(synoptic_data)
    assert not df.empty
    assert df.iloc[0]["provider"] == "Synoptic"
    assert df.iloc[0]["type"] == "Observed"
    assert df.iloc[0]["temperature_f"] == 82.0
    assert df.iloc[0]["dewpoint_f"] == 68.0
    assert df.iloc[0]["raw_temp_c"] == 27.78
    assert df.iloc[0]["raw_dewpoint_c"] == 20.0
    assert "some_check" in df.iloc[0]["qc_flags"]


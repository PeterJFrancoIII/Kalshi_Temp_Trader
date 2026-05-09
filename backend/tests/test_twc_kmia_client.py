import os

from weather.twc_kmia_client import (
    TWCKMIAClient,
    derive_features,
    normalize_bundle,
    normalize_current,
    normalize_daily,
    normalize_hourly,
)


def test_normalize_current_handles_missing_input():
    assert normalize_current(None) == {}
    assert normalize_current({}) == {
        "temperature_f": None,
        "dewpoint_f": None,
        "relative_humidity_pct": None,
        "wind_speed_mph": None,
        "wind_direction_degrees": None,
        "wind_direction_cardinal": None,
        "cloud_cover_pct": None,
        "cloud_cover_phrase": None,
        "pressure_altimeter_in": None,
        "pressure_mean_sea_level_mb": None,
        "precip_1h_in": None,
        "phrase": None,
        "observation_time_utc": None,
    }


def test_normalize_current_maps_common_twc_fields():
    row = normalize_current(
        {
            "temperature": 84,
            "temperatureDewPoint": 73,
            "relativeHumidity": 68,
            "windSpeed": 12,
            "windDirection": 110,
            "windDirectionCardinal": "ESE",
            "cloudCover": 40,
            "wxPhraseLong": "Partly Cloudy",
            "validTimeUtc": 1778323200,
        }
    )
    assert row["temperature_f"] == 84
    assert row["dewpoint_f"] == 73
    assert row["relative_humidity_pct"] == 68
    assert row["wind_speed_mph"] == 12
    assert row["wind_direction_degrees"] == 110
    assert row["wind_direction_cardinal"] == "ESE"
    assert row["cloud_cover_pct"] == 40
    assert row["phrase"] == "Partly Cloudy"
    assert row["observation_time_utc"] == 1778323200


def test_normalize_daily_handles_list_payload():
    rows = normalize_daily(
        {
            "validTimeUtc": [1778323200, 1778409600],
            "temperatureMax": [86, 88],
            "temperatureMin": [75, 76],
            "narrative": ["Warm", "Hot"],
            "precipChance": [20, 30],
        }
    )
    assert len(rows) == 2
    assert rows[0]["max_temp_f"] == 86
    assert rows[1]["min_temp_f"] == 76
    assert rows[1]["precip_probability_pct"] == 30


def test_normalize_hourly_handles_list_payload():
    rows = normalize_hourly(
        {
            "validTimeUtc": [1778323200, 1778326800],
            "validTimeLocal": ["2026-05-09T10:00:00-0400", "2026-05-09T11:00:00-0400"],
            "temperature": [82, 85],
            "temperatureDewPoint": [72, 73],
            "relativeHumidity": [70, 68],
            "windSpeed": [8, 10],
            "windDirection": [90, 120],
            "windDirectionCardinal": ["E", "ESE"],
            "cloudCover": [20, 35],
            "precipChance": [10, 15],
            "wxPhraseLong": ["Sunny", "Partly Cloudy"],
        }
    )
    assert len(rows) == 2
    assert rows[0]["temperature_f"] == 82
    assert rows[1]["wind_direction_degrees"] == 120
    assert rows[1]["phrase"] == "Partly Cloudy"


def test_derive_features_returns_expected_fields():
    daily = [{"max_temp_f": 87}]
    hourly = [
        {"temperature_f": 82, "wind_direction_degrees": 270, "valid_time_local": "10:00"},
        {"temperature_f": 86, "wind_direction_degrees": 110, "valid_time_local": "13:00", "cloud_cover_pct": 45},
    ]
    features = derive_features(daily, hourly)
    assert features["forecast_high_f"] == 87
    assert features["hourly_max_temp_f"] == 86
    assert features["sea_breeze_shift_hour_et"] == "13:00"
    assert features["max_cloud_cover_pct"] == 45


def test_normalize_bundle_preserves_safety_and_missing_hourly_flag():
    raw = {
        "geocode": "25.7959,-80.2870",
        "fetched_at_utc": "2026-05-09T12:00:00+00:00",
        "api_units": "e",
        "language": "en-US",
        "endpoints": {
            "current_conditions": {"status": "OK"},
            "daily_forecast": {"status": "OK"},
            "hourly_forecast": {"status": "MISSING_API_KEY"},
        },
        "responses": {
            "current_conditions": {"temperature": 84},
            "daily_forecast": {"temperatureMax": [87]},
            "hourly_forecast": None,
        },
    }
    snapshot = normalize_bundle(raw)
    assert snapshot["safety"]["no_real_trading"] is True
    assert snapshot["derived_features"]["forecast_high_f"] == 87
    assert "hourly_comparison_not_ready" in snapshot["quality_flags"]


def test_missing_api_key_returns_safe_metadata(monkeypatch):
    monkeypatch.delenv("TWC_API_KEY", raising=False)
    monkeypatch.delenv("WEATHER_COMPANY_API_KEY", raising=False)
    client = TWCKMIAClient(api_key=None)
    data, meta = client.request_endpoint("current_conditions", "/v3/wx/observations/current")
    assert data is None
    assert meta["status"] == "MISSING_API_KEY"
    assert "TWC_API_KEY" in meta["warning"]

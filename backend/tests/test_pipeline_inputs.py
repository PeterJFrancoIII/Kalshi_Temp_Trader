"""Characterization tests for features.pipeline_inputs.

These lock in the behavior that previously lived inline in
scheduler.run_daily_prediction.py so the extraction is safe.
"""

import json
import tempfile
from datetime import date
from pathlib import Path

from features.pipeline_inputs import (
    CLIMATOLOGICAL_DEFAULTS,
    _classify_thunderstorm_severity,
    _derive_weather_flags,
    build_dry_run_features,
)


def test_climatological_defaults_match_documented_values():
    """Defaults align with the inline fallbacks the scheduler used to carry."""
    assert CLIMATOLOGICAL_DEFAULTS["forecast_high_f"] == 85
    assert CLIMATOLOGICAL_DEFAULTS["current_temp_f"] == 81
    assert CLIMATOLOGICAL_DEFAULTS["observed_max_so_far_f"] == 82
    assert CLIMATOLOGICAL_DEFAULTS["normal_high_f"] == 82
    assert CLIMATOLOGICAL_DEFAULTS["recent_rain_flag"] is False
    assert CLIMATOLOGICAL_DEFAULTS["thunderstorm_flag"] is False
    assert CLIMATOLOGICAL_DEFAULTS["overcast_flag"] is False
    assert CLIMATOLOGICAL_DEFAULTS["thunderstorm_severity"] == "none"
    assert CLIMATOLOGICAL_DEFAULTS["live_data_stale"] is True


def test_build_dry_run_features_missing_snapshot_returns_defaults():
    feats = build_dry_run_features(
        target_date=date(2026, 5, 19),
        snapshot_path="/nonexistent/path/snapshot.json",
    )
    assert feats["forecast_high_f"] == 85
    assert feats["current_temp_f"] == 81
    assert feats["observed_max_so_far_f"] == 82
    assert feats["live_data_stale"] is True
    assert feats["thunderstorm_severity"] == "none"
    assert feats["target_date"] == "2026-05-19"
    # Sanity: scheduler-required keys are all present even with no snapshot.
    for required in (
        "observed_max_so_far_f",
        "current_temp_f",
        "forecast_high_f",
        "normal_high_f",
        "recent_rain_flag",
        "thunderstorm_flag",
        "overcast_flag",
        "thunderstorm_severity",
        "current_time_et",
        "live_data_stale",
        "target_date",
    ):
        assert required in feats, f"Missing required feature key: {required}"


def test_build_dry_run_features_with_obs_and_forecast():
    snapshot = {
        "fetched_at_utc": "2026-05-19T12:00:00+00:00",
        "recent_observations_table": [
            {"date_et": "2026-05-19", "temperature_f": 81.4},
            {"date_et": "2026-05-19", "temperature_f": 84.9},
            {"date_et": "2026-05-19", "temperature_f": 79.0},
            {"date_et": "2026-05-18", "temperature_f": 90.0},
        ],
        "daily_forecast": [
            {
                "forecast_date_et": "2026-05-19",
                "isDaytime": True,
                "temperature_f": 87,
                "shortForecast": "Partly Cloudy",
                "detailedForecast": "Partly cloudy with a chance of showers.",
            }
        ],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "snap.json"
        path.write_text(json.dumps(snapshot))

        feats = build_dry_run_features(date(2026, 5, 19), snapshot_path=path)

    # First entry's temperature_f is the "current"; max across entries is observed_max.
    assert feats["current_temp_f"] == 81
    assert feats["observed_max_so_far_f"] == 85
    assert feats["forecast_high_f"] == 87
    assert feats["live_data_stale"] is False
    assert feats["recent_rain_flag"] is True  # "shower" present
    assert feats["overcast_flag"] is False  # "partly cloudy" excluded
    assert feats["thunderstorm_flag"] is False


def test_build_dry_run_features_no_obs_for_target_date_marks_stale():
    snapshot = {
        "fetched_at_utc": "2026-05-19T12:00:00+00:00",
        "recent_observations_table": [
            {"date_et": "2026-05-18", "temperature_f": 90.0}
        ],
        "daily_forecast": [],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "snap.json"
        path.write_text(json.dumps(snapshot))

        feats = build_dry_run_features(date(2026, 5, 19), snapshot_path=path)

    # Behavior preserved from scheduler: observed_max -> None, stale True,
    # other defaults retained.
    assert feats["observed_max_so_far_f"] is None
    assert feats["live_data_stale"] is True
    assert feats["forecast_high_f"] == 85  # falls back to default


def test_thunderstorm_severity_classification():
    """The cascading severity rules from the scheduler are preserved."""
    cases = [
        ("definite thunderstorms", "definite"),
        ("thunderstorms likely", "likely"),
        ("slight chance of thunderstorms", "slight chance"),
        ("isolated thunderstorms", "slight chance"),
        ("isolated thunderstorms then a chance of showers", "chance"),
        ("chance of thunderstorms", "chance"),
        ("scattered thunderstorms", "chance"),
        ("thunderstorms in the area", "likely"),  # generic fallback
        ("partly cloudy", "none"),  # no thunderstorm at all
    ]
    for text, expected in cases:
        full_fc = text.lower()
        thunderstorm = "thunderstorm" in full_fc
        got = _classify_thunderstorm_severity(full_fc, thunderstorm)
        assert got == expected, f"{text!r} -> got {got!r}, expected {expected!r}"


def test_derive_weather_flags_overcast_partly_cloudy_distinction():
    """`partly cloudy` must not flip overcast_flag, but `cloudy` alone must."""
    partly = _derive_weather_flags({
        "shortForecast": "Partly Cloudy",
        "detailedForecast": "Partly cloudy throughout the day.",
    })
    assert partly["overcast_flag"] is False

    cloudy = _derive_weather_flags({
        "shortForecast": "Cloudy",
        "detailedForecast": "Cloudy all day.",
    })
    assert cloudy["overcast_flag"] is True

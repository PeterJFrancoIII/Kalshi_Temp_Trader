"""Feature dictionaries that feed the forecasting models.

The forecasting pipeline (scheduler.run_daily_prediction) historically assembled
its feature dictionary inline from an NWS snapshot file. That code was ~130
lines living in the orchestration layer and was hard to test in isolation.

This module owns that assembly logic. The functions here are pure with respect
to the filesystem inputs they receive: they read JSON, return a dict. Callers
own the scheduling, logging, and DB persistence.

No real-money trading code. Dry-run / paper evaluation only.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, Optional

from dateutil import tz

from shared.artifact_paths import LATEST_NWS_KMIA_SNAPSHOT

logger = logging.getLogger(__name__)


# Climatological fallbacks. These match the historical defaults that lived
# inline in scheduler.run_daily_prediction. They are used only when the NWS
# snapshot is missing or unreadable.
CLIMATOLOGICAL_DEFAULTS: Dict[str, Any] = {
    "forecast_high_f": 85,
    "current_temp_f": 81,
    "observed_max_so_far_f": 82,
    "normal_high_f": 82,
    "recent_rain_flag": False,
    "thunderstorm_flag": False,
    "overcast_flag": False,
    "thunderstorm_severity": "none",
    "live_data_stale": True,
}


def _classify_thunderstorm_severity(full_fc: str, thunderstorm_flag: bool) -> str:
    """Map forecast text to a discrete thunderstorm severity label.

    Preserves the original cascading rules from the inline scheduler code:
    definite > likely > slight chance/isolated > chance/scattered > likely (default).
    """
    if not thunderstorm_flag:
        return "none"
    if "definite" in full_fc:
        return "definite"
    if "likely" in full_fc:
        return "likely"
    if "slight chance" in full_fc or "isolated" in full_fc:
        if any(x in full_fc for x in ["then a chance", "then chance", "then scattered"]):
            return "chance"
        return "slight chance"
    if "chance" in full_fc or "scattered" in full_fc:
        return "chance"
    return "likely"


def _derive_weather_flags(period: Dict[str, Any]) -> Dict[str, Any]:
    """Derive rain/thunderstorm/overcast flags from one NWS forecast period."""
    short_fc = (period.get("shortForecast") or "").lower()
    detailed_fc = (period.get("detailedForecast") or "").lower()
    full_fc = f"{short_fc} {detailed_fc}".lower()

    thunderstorm_flag = "thunderstorm" in full_fc
    recent_rain_flag = "rain" in full_fc or "shower" in full_fc
    overcast_flag = "cloudy" in full_fc and "partly" not in full_fc

    return {
        "recent_rain_flag": recent_rain_flag,
        "thunderstorm_flag": thunderstorm_flag,
        "overcast_flag": overcast_flag,
        "thunderstorm_severity": _classify_thunderstorm_severity(full_fc, thunderstorm_flag),
    }


def _select_daytime_period_for_date(
    daily_forecast: list, target_date_str: str
) -> Optional[Dict[str, Any]]:
    """Return the first daytime forecast period matching the target date, if any."""
    for period in daily_forecast:
        if (
            period.get("forecast_date_et") == target_date_str
            and period.get("isDaytime", False)
        ):
            return period
    return None


def _extract_observations_for_date(
    snapshot: Dict[str, Any], target_date_str: str
) -> Dict[str, Any]:
    """Pull current temp and observed max for the target date out of a snapshot.

    Returns a dict with keys:
      current_temp_f: int | None
      observed_max_so_far_f: int | None
      live_data_stale: bool (True when no observations were found for the date)
    """
    obs_table = snapshot.get("recent_observations_table", [])
    target_day_obs = [
        row for row in obs_table if row.get("date_et") == target_date_str
    ]

    if not target_day_obs:
        return {
            "current_temp_f": None,
            "observed_max_so_far_f": None,
            "live_data_stale": True,
            "_observation_status": "no_obs_for_target_date",
        }

    latest_target = target_day_obs[0]
    try:
        current_temp_f: Optional[int] = int(
            round(latest_target.get("temperature_f"))
        ) if latest_target.get("temperature_f") is not None else None
    except (TypeError, ValueError):
        current_temp_f = None

    temps = [
        row.get("temperature_f")
        for row in target_day_obs
        if row.get("temperature_f") is not None
    ]
    observed_max_so_far_f = int(round(max(temps))) if temps else None

    return {
        "current_temp_f": current_temp_f,
        "observed_max_so_far_f": observed_max_so_far_f,
        "live_data_stale": False,
        "_observation_status": "ok",
    }


def build_dry_run_features(
    target_date: date,
    snapshot_path: Optional[os.PathLike] = None,
) -> Dict[str, Any]:
    """Build the feature dict used by `forecast_daily_high_bins[_v2]` in dry-run.

    Reads the latest NWS snapshot, extracts target-date observations and
    forecast period, derives weather flags, and falls back to climatological
    defaults if anything is missing.

    Pure with respect to inputs and the wall clock for `current_time_et`.
    """
    snapshot_path = (
        os.fspath(snapshot_path) if snapshot_path is not None
        else os.fspath(LATEST_NWS_KMIA_SNAPSHOT)
    )

    target_date_str = target_date.isoformat()

    # Start from climatological defaults; overlay snapshot-derived values.
    features: Dict[str, Any] = dict(CLIMATOLOGICAL_DEFAULTS)
    features["current_time_et"] = datetime.now(tz.gettz("US/Eastern"))
    features["target_date"] = target_date_str

    if not os.path.exists(snapshot_path):
        logger.warning(
            "NWS snapshot not found at %s. Using climatological defaults.",
            snapshot_path,
        )
        return features

    try:
        with open(snapshot_path, "r") as fh:
            snapshot = json.load(fh)
    except Exception as e:
        logger.warning(
            "Failed to load NWS snapshot for dry-run: %s. "
            "Using climatological defaults.",
            e,
        )
        features["live_data_stale"] = True
        return features

    # 1. Observations for target date.
    obs = _extract_observations_for_date(snapshot, target_date_str)
    if obs["_observation_status"] == "no_obs_for_target_date":
        logger.warning(
            "No observations found in snapshot for target date %s",
            target_date_str,
        )
    # Preserve the original semantics:
    #  - If no observations for the day, we set observed_max_so_far_f to None
    #    (overriding the climatological default of 82) and live_data_stale=True.
    #  - If observations exist, overlay current_temp_f and observed_max_so_far_f.
    features["live_data_stale"] = obs["live_data_stale"]
    features["observed_max_so_far_f"] = obs["observed_max_so_far_f"]
    if obs["current_temp_f"] is not None:
        features["current_temp_f"] = obs["current_temp_f"]

    # 2. Forecast high for target date.
    daily_forecast = snapshot.get("daily_forecast", []) or []
    period = _select_daytime_period_for_date(daily_forecast, target_date_str)
    nws_forecast_high = period.get("temperature_f") if period else None

    if nws_forecast_high is not None:
        features["forecast_high_f"] = int(nws_forecast_high)
        logger.info(
            "NWS forecast high for %s: %s°F", target_date_str, features["forecast_high_f"]
        )
    else:
        top_level_high = snapshot.get("forecast_high_f")
        if top_level_high is not None:
            features["forecast_high_f"] = int(top_level_high)
            logger.warning(
                "No daily_forecast entry for %s; using top-level forecast_high_f=%s°F",
                target_date_str,
                features["forecast_high_f"],
            )
        else:
            logger.warning(
                "No NWS forecast high found for %s. Using climatological fallback: %s°F",
                target_date_str,
                features["forecast_high_f"],
            )

    # 3. Weather flags from the same period.
    if period is not None:
        features.update(_derive_weather_flags(period))

    # 4. Recent observations list.
    features["recent_observations"] = snapshot.get("recent_observations_table", [])

    logger.info(
        "Loaded NWS snapshot for dry-run features (fetched: %s).",
        snapshot.get("fetched_at_utc", "unknown"),
    )
    return features

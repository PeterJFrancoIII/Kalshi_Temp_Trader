"""
Canonical NWS/KMIA snapshot freshness assessment layer.

Exposes the assess_nws_snapshot function to evaluate snapshot freshness, safety parameters,
and required data presence. Used by paper signal generators and risk engines to ensure
safety-critical boundaries.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

def assess_nws_snapshot(snapshot: Optional[Dict[str, Any]], now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Assess an NWS snapshot for availability, safety, completeness, and freshness.

    Args:
        snapshot: The NWS snapshot dictionary to assess.
        now_utc: Reference UTC time for age calculation. Defaults to current UTC time.

    Returns:
        dict containing:
            available: bool
            allow_paper_recommendations: bool
            status: "OK" | "STALE" | "ERROR" | "MISSING"
            no_trade_reason: str | None
            warnings: list[str]
            latest_observation_time: str | None
            fetched_at_utc: str | None
            observation_age_minutes: float | None
            required_fields_present: bool
    """
    warnings = []
    status = "OK"
    allow_paper_recommendations = True
    no_trade_reason = None
    required_fields_present = True
    latest_observation_time = None
    fetched_at_utc = None
    observation_age_minutes = None

    if snapshot is None:
        return {
            "available": False,
            "allow_paper_recommendations": False,
            "status": "MISSING",
            "no_trade_reason": "NWS snapshot is missing or None.",
            "warnings": ["NWS snapshot is missing."],
            "latest_observation_time": None,
            "fetched_at_utc": None,
            "observation_age_minutes": None,
            "required_fields_present": False,
        }

    if not isinstance(snapshot, dict):
        return {
            "available": False,
            "allow_paper_recommendations": False,
            "status": "ERROR",
            "no_trade_reason": "Snapshot is not a valid dictionary.",
            "warnings": ["Snapshot is not a valid dictionary."],
            "latest_observation_time": None,
            "fetched_at_utc": None,
            "observation_age_minutes": None,
            "required_fields_present": False,
        }

    # Reference time setup & validation
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    else:
        # Check if now_utc is naive
        if now_utc.tzinfo is None or now_utc.tzinfo.utcoffset(now_utc) is None:
            allow_paper_recommendations = False
            status = "ERROR"
            no_trade_reason = "System reference time is naive."
            warnings.append("Reference time (now_utc) is naive.")

    # 1. Station verification
    station = snapshot.get("station")
    if station != "KMIA":
        required_fields_present = False
        allow_paper_recommendations = False
        status = "ERROR"
        warnings.append(f"Station must be KMIA, got {station!r}")
        if not no_trade_reason:
            no_trade_reason = f"Invalid station: {station!r} (expected KMIA)"

    # 2. Check fetched_at_utc presence and parse
    fetched_at_utc = snapshot.get("fetched_at_utc")
    fetched_dt = None
    if not fetched_at_utc:
        required_fields_present = False
        allow_paper_recommendations = False
        status = "ERROR"
        warnings.append("fetched_at_utc is missing or empty.")
        if not no_trade_reason:
            no_trade_reason = "fetched_at_utc is missing."
    else:
        try:
            if not isinstance(fetched_at_utc, str):
                raise ValueError("fetched_at_utc must be a string")
            cleaned = fetched_at_utc.replace("Z", "+00:00")
            fetched_dt = datetime.fromisoformat(cleaned)
            if fetched_dt.tzinfo is None or fetched_dt.tzinfo.utcoffset(fetched_dt) is None:
                required_fields_present = False
                allow_paper_recommendations = False
                status = "ERROR"
                warnings.append(f"fetched_at_utc is naive: {fetched_at_utc}")
                if not no_trade_reason:
                    no_trade_reason = "fetched_at_utc is naive (timezone-aware required)."
        except Exception as e:
            required_fields_present = False
            allow_paper_recommendations = False
            status = "ERROR"
            warnings.append(f"Failed to parse fetched_at_utc: {e}")
            if not no_trade_reason:
                no_trade_reason = f"Failed to parse fetched_at_utc: {fetched_at_utc}"

    # 3. Check latest_observation_time presence and parse
    latest_observation_time = snapshot.get("latest_observation_time")
    obs_dt = None
    if not latest_observation_time:
        required_fields_present = False
        allow_paper_recommendations = False
        status = "ERROR"
        warnings.append("latest_observation_time is missing or empty.")
        if not no_trade_reason:
            no_trade_reason = "latest_observation_time is missing."
    else:
        try:
            if not isinstance(latest_observation_time, str):
                raise ValueError("latest_observation_time must be a string")
            cleaned = latest_observation_time.replace("Z", "+00:00")
            obs_dt = datetime.fromisoformat(cleaned)
            if obs_dt.tzinfo is None or obs_dt.tzinfo.utcoffset(obs_dt) is None:
                required_fields_present = False
                allow_paper_recommendations = False
                status = "ERROR"
                warnings.append(f"latest_observation_time is naive: {latest_observation_time}")
                if not no_trade_reason:
                    no_trade_reason = "latest_observation_time is naive (timezone-aware required)."
        except Exception as e:
            required_fields_present = False
            allow_paper_recommendations = False
            status = "ERROR"
            warnings.append(f"Failed to parse latest_observation_time: {e}")
            if not no_trade_reason:
                no_trade_reason = f"Failed to parse latest_observation_time: {latest_observation_time}"

    # 4. Check current_temp_f presence
    current_temp_f = snapshot.get("current_temp_f")
    if current_temp_f is None:
        required_fields_present = False
        allow_paper_recommendations = False
        status = "ERROR"
        warnings.append("current_temp_f is missing or None.")
        if not no_trade_reason:
            no_trade_reason = "current_temp_f is missing or None."

    # 5. Check observed_max_so_far_f presence
    observed_max_so_far_f = snapshot.get("observed_max_so_far_f")
    if observed_max_so_far_f is None:
        required_fields_present = False
        allow_paper_recommendations = False
        status = "ERROR"
        warnings.append("observed_max_so_far_f is missing or None.")
        if not no_trade_reason:
            no_trade_reason = "observed_max_so_far_f is missing or None."

    # 6. Check forecast_high_f presence
    forecast_high_f = snapshot.get("forecast_high_f")
    if forecast_high_f is None:
        required_fields_present = False
        allow_paper_recommendations = False
        status = "ERROR"
        warnings.append("forecast_high_f is missing or None.")
        if not no_trade_reason:
            no_trade_reason = "forecast_high_f is missing or None."

    # 7. Check recent_observations_table presence
    recent_obs = snapshot.get("recent_observations_table")
    if not isinstance(recent_obs, list) or len(recent_obs) == 0:
        required_fields_present = False
        allow_paper_recommendations = False
        status = "ERROR"
        warnings.append("recent_observations_table is missing, empty, or not a list.")
        if not no_trade_reason:
            no_trade_reason = "recent_observations_table is missing or empty."

    # 8. Check safety block
    safety = snapshot.get("safety")
    if not isinstance(safety, dict) or not safety.get("no_real_trading"):
        required_fields_present = False
        allow_paper_recommendations = False
        status = "ERROR"
        warnings.append("safety.no_real_trading is missing or not True.")
        if not no_trade_reason:
            no_trade_reason = "safety.no_real_trading must be True to allow paper recommendations."

    # 9. check stale_data flag
    if snapshot.get("stale_data") is True:
        allow_paper_recommendations = False
        if status != "ERROR":
            status = "STALE"
        warnings.append("Snapshot has stale_data flag set to True.")
        if not no_trade_reason:
            no_trade_reason = "stale_data flag is True."

    # 10. check stale_fallback flag
    if snapshot.get("stale_fallback") is True:
        allow_paper_recommendations = False
        if status != "ERROR":
            status = "STALE"
        warnings.append("Snapshot has stale_fallback flag set to True.")
        if not no_trade_reason:
            no_trade_reason = "stale_fallback flag is True."

    # 11. check endpoint_status
    if snapshot.get("endpoint_status") == "ERROR":
        allow_paper_recommendations = False
        status = "ERROR"
        warnings.append("Snapshot has endpoint_status set to ERROR.")
        if not no_trade_reason:
            no_trade_reason = "endpoint_status is ERROR."

    # 12. age check if valid obs_dt is parsed
    if obs_dt is not None and now_utc is not None:
        try:
            if now_utc.tzinfo is not None and now_utc.tzinfo.utcoffset(now_utc) is not None:
                # Subtraction is valid since both are timezone-aware
                age_seconds = (now_utc - obs_dt).total_seconds()
                observation_age_minutes = age_seconds / 60.0
                if observation_age_minutes > 90.0:
                    allow_paper_recommendations = False
                    if status != "ERROR":
                        status = "STALE"
                    warnings.append(f"Observation is {observation_age_minutes:.1f} minutes old (>90 mins).")
                    if not no_trade_reason:
                        no_trade_reason = f"Weather observation is stale ({observation_age_minutes:.1f} mins old)."
        except TypeError as te:
            # Subtraction type errors due to timezone mismatch (though both are checked)
            allow_paper_recommendations = False
            status = "ERROR"
            warnings.append(f"Timezone offset error during subtraction: {te}")
            if not no_trade_reason:
                no_trade_reason = "Reference time or observation time is naive."

    return {
        "available": True,
        "allow_paper_recommendations": allow_paper_recommendations,
        "status": status,
        "no_trade_reason": no_trade_reason,
        "warnings": warnings,
        "latest_observation_time": latest_observation_time,
        "fetched_at_utc": fetched_at_utc,
        "observation_age_minutes": observation_age_minutes,
        "required_fields_present": required_fields_present,
    }

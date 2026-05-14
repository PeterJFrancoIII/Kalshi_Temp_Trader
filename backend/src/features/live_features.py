from typing import List, Tuple, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from dateutil.tz import gettz

from shared.types import WeatherSnapshot, LiveObservation
from ingestion.kmia_obhistory_parser import ParsedObservation

class LiveFeatureMetrics(BaseModel):
    temperature_trend_1h: Optional[float]
    temperature_trend_3h: Optional[float]
    time_of_observed_max: Optional[datetime]
    stale_data_flag: bool

def compute_live_features(
    wrh_obs: List[ParsedObservation],
    obhistory_obs: List[ParsedObservation] = None
) -> Tuple[WeatherSnapshot, LiveObservation, LiveFeatureMetrics]:
    
    # Combine and sort observations, prioritizing WRH but filling gaps from obhistory if needed
    # For MVP, we mainly rely on WRH if available
    obs_list = sorted(wrh_obs, key=lambda x: x.timestamp)
    
    if not obs_list:
        raise ValueError("No observations provided")
        
    latest_obs = obs_list[-1]
    
    # Calculate stale data flag (older than 90 mins)
    now = datetime.now(timezone.utc)
    stale_data_flag = False
    
    # Ensure timezone awareness for comparison
    latest_time = latest_obs.timestamp
    if latest_time.tzinfo is None:
        latest_time = latest_time.replace(tzinfo=timezone.utc)
        
    if (now - latest_time).total_seconds() > 90 * 60:
        stale_data_flag = True
        
    # Get local ET date
    et_tz = gettz('US/Eastern')
    now_et = now.astimezone(et_tz)
    start_of_day_et = datetime(now_et.year, now_et.month, now_et.day, tzinfo=et_tz)
    
    # Filter today's observations
    todays_obs = []
    for o in obs_list:
        ot_et = o.timestamp.astimezone(et_tz) if o.timestamp.tzinfo else o.timestamp.replace(tzinfo=timezone.utc).astimezone(et_tz)
        if ot_et >= start_of_day_et:
            todays_obs.append((ot_et, o))
            
    # Compute observed max so far
    observed_max_so_far_f = None
    time_of_observed_max = None
    
    for ot_et, o in todays_obs:
        if o.temperature_f is not None:
            temp_int = int(round(o.temperature_f))
            if observed_max_so_far_f is None or temp_int > observed_max_so_far_f:
                observed_max_so_far_f = temp_int
                time_of_observed_max = o.timestamp
                
    # If no temp today, we do not fall back to latest_obs if it's from a prior day.
    if observed_max_so_far_f is None:
        # Default to 0 for safety, but flag as stale if no data for today exists
        observed_max_so_far_f = 0
        stale_data_flag = True

    current_temp_f = int(round(latest_obs.temperature_f)) if latest_obs.temperature_f is not None else 0
    if latest_obs.temperature_f is None:
        stale_data_flag = True

    # Compute trends (1h and 3h)
    trend_1h = None
    trend_3h = None
    
    def get_temp_at_offset(offset_hours: int) -> Optional[float]:
        target_time = latest_time - timedelta(hours=offset_hours)
        best_diff = timedelta(hours=24)
        best_temp = None
        for o in obs_list:
            if o.temperature_f is None: continue
            ot = o.timestamp.astimezone(timezone.utc) if o.timestamp.tzinfo else o.timestamp.replace(tzinfo=timezone.utc)
            diff = abs(ot - target_time)
            if diff < timedelta(minutes=30) and diff < best_diff:
                best_diff = diff
                best_temp = o.temperature_f
        return best_temp

    t_1h = get_temp_at_offset(1)
    if t_1h is not None and latest_obs.temperature_f is not None:
        trend_1h = latest_obs.temperature_f - t_1h
        
    t_3h = get_temp_at_offset(3)
    if t_3h is not None and latest_obs.temperature_f is not None:
        trend_3h = latest_obs.temperature_f - t_3h

    # Flags
    desc = (latest_obs.weather_condition or "").lower()
    recent_rain_flag = "rain" in desc or "showers" in desc or "drizzle" in desc
    thunderstorm_flag = "thunder" in desc or "t-storm" in desc
    
    sky = (latest_obs.sky_condition or "").lower()
    overcast_flag = "overcast" in sky or "ovc" in sky or "cloudy" in desc

    # Daylight hours roughly (mock logic for daylight)
    hour_et = now_et.hour + now_et.minute / 60.0
    remaining_daylight = max(0.0, 20.0 - hour_et) # assume sunset around 8 PM (20:00)

    weather_snapshot = WeatherSnapshot(
        station="KMIA",
        timestamp=latest_obs.timestamp,
        current_temp_f=current_temp_f,
        wind_speed=latest_obs.wind_speed_mph,
        wind_direction=str(latest_obs.wind_direction) if latest_obs.wind_direction is not None else None,
        dewpoint_f=latest_obs.dewpoint_f,
        overcast_flag=overcast_flag,
        thunderstorm_flag=thunderstorm_flag,
        recent_rain_flag=recent_rain_flag
    )
    
    live_obs = LiveObservation(
        timestamp=latest_obs.timestamp,
        station="KMIA",
        observed_max_so_far_f=observed_max_so_far_f,
        current_temp_f=current_temp_f,
        remaining_daylight_hours=remaining_daylight
    )
    
    metrics = LiveFeatureMetrics(
        temperature_trend_1h=trend_1h,
        temperature_trend_3h=trend_3h,
        time_of_observed_max=time_of_observed_max,
        stale_data_flag=stale_data_flag
    )
    
    return weather_snapshot, live_obs, metrics

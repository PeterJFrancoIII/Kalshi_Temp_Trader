import pytz
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from shared.types import ForecastSnapshot

class ForecastGuidanceFeatures(BaseModel):
    station: str = "KMIA"
    forecast_date: date
    forecast_high_f: int
    hourly_max_forecast_f: Optional[int] = None
    rain_expected_flag: bool = False
    thunderstorm_expected_flag: bool = False
    cloud_suppression_flag: bool = False
    forecast_age_minutes: int
    update_time: datetime
    raw_wording: str = ""

class ForecastParser:
    """Parses NWS API responses into structured features for KMIA high temperature prediction."""
    
    def __init__(self, target_timezone: str = "America/New_York"):
        self.tz = pytz.timezone(target_timezone)

    def parse_forecasts(
        self, 
        daily_json: Optional[Dict[str, Any]], 
        hourly_json: Optional[Dict[str, Any]],
        target_date: Optional[date] = None
    ) -> ForecastGuidanceFeatures:
        """
        Main entry point for parsing both daily and hourly forecasts.
        If target_date is not provided, defaults to today in target_timezone.
        """
        now = datetime.now(self.tz)
        if target_date is None:
            target_date = now.date()

        # Initialize defaults
        update_time = now # Fallback
        forecast_high_f = -999
        hourly_max_forecast_f = None
        rain_expected = False
        ts_expected = False
        cloud_suppression = False
        raw_wording = ""

        # 1. Parse Daily JSON for High and Wording
        if daily_json and "properties" in daily_json:
            props = daily_json["properties"]
            update_time_str = props.get("updateTime")
            if update_time_str:
                update_time = datetime.fromisoformat(update_time_str.replace("Z", "+00:00"))
            
            periods = props.get("periods", [])
            # Find the period corresponding to the target date's daytime
            # Usually the first period if it's currently daytime, or second if it's night.
            # We look for "isDaytime": True and name containing today's name or just "Today".
            for period in periods:
                p_start = datetime.fromisoformat(period["startTime"])
                p_local = p_start.astimezone(self.tz)
                
                if p_local.date() == target_date and period.get("isDaytime"):
                    forecast_high_f = period.get("temperature", -999)
                    detailed_forecast = period.get("detailedForecast", "").lower()
                    raw_wording = detailed_forecast
                    
                    # Feature Extraction from wording
                    if any(word in detailed_forecast for word in ["rain", "showers", "drizzle"]):
                        rain_expected = True
                    if "thunderstorm" in detailed_forecast:
                        ts_expected = True
                    if any(word in detailed_forecast for word in ["mostly cloudy", "overcast", "cloudy"]):
                        cloud_suppression = True
                    
                    # Precip prob check if available in period
                    pop = period.get("probabilityOfPrecipitation", {}).get("value", 0)
                    if pop and pop > 20:
                        rain_expected = True
                    
                    break

        # 2. Parse Hourly JSON for Max Hourly Temp
        if hourly_json and "properties" in hourly_json:
            h_periods = hourly_json["properties"].get("periods", [])
            daily_temps = []
            for hp in h_periods:
                hp_start = datetime.fromisoformat(hp["startTime"])
                hp_local = hp_start.astimezone(self.tz)
                
                if hp_local.date() == target_date:
                    daily_temps.append(hp["temperature"])
            
            if daily_temps:
                hourly_max_forecast_f = max(daily_temps)

        # 3. Calculate Age
        age_delta = now - update_time
        forecast_age_minutes = int(age_delta.total_seconds() / 60)

        return ForecastGuidanceFeatures(
            forecast_date=target_date,
            forecast_high_f=forecast_high_f,
            hourly_max_forecast_f=hourly_max_forecast_f,
            rain_expected_flag=rain_expected,
            thunderstorm_expected_flag=ts_expected,
            cloud_suppression_flag=cloud_suppression,
            forecast_age_minutes=forecast_age_minutes,
            update_time=update_time,
            raw_wording=raw_wording
        )

    def to_snapshot(self, features: ForecastGuidanceFeatures) -> ForecastSnapshot:
        """Converts internal features to the shared ForecastSnapshot object."""
        return ForecastSnapshot(
            date=features.forecast_date,
            station=features.station,
            forecast_high_f=features.forecast_high_f
        )

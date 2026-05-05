import json
from datetime import datetime, date
import pytz
from typing import List, Optional
from pydantic import BaseModel

class MetarObservation(BaseModel):
    timestamp_zulu: datetime
    temp_c: float
    raw_metar: str

class LiveSensorParser:
    """Parses live METAR/SPECI observations to calculate observed max temperature so far today."""
    
    def __init__(self, target_timezone: str = "America/New_York"):
        self.tz = pytz.timezone(target_timezone)
        
    def _c_to_f(self, temp_c: float) -> int:
        return round(temp_c * 9/5 + 32)
        
    def get_max_so_far(self, observations: List[MetarObservation], target_date: date) -> Optional[int]:
        """
        Calculates the maximum temperature observed for a specific calendar date in US/Eastern.
        """
        daily_temps_f = []
        
        for obs in observations:
            # Convert Zulu timestamp to US/Eastern
            local_dt = obs.timestamp_zulu.replace(tzinfo=pytz.utc).astimezone(self.tz)
            
            # Filter for the target calendar date
            if local_dt.date() == target_date:
                daily_temps_f.append(self._c_to_f(obs.temp_c))
                
        if not daily_temps_f:
            return None
            
        return max(daily_temps_f)

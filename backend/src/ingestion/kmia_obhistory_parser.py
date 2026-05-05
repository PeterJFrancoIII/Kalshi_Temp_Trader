from dataclasses import dataclass
from typing import List, Optional, Any, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import logging

logger = logging.getLogger(__name__)

@dataclass
class ParsedObservation:
    timestamp: datetime
    temperature_f: Optional[float] = None
    dewpoint_f: Optional[float] = None
    humidity: Optional[float] = None
    wind_direction: Optional[float] = None
    wind_speed_mph: Optional[float] = None
    wind_gust_mph: Optional[float] = None
    pressure_in: Optional[float] = None
    precipitation_in: Optional[float] = None
    weather_condition: Optional[str] = None
    sky_condition: Optional[str] = None
    raw_metar: Optional[str] = None
    is_preliminary: bool = True
    source: str = "unknown"

def _c_to_f(celsius: Optional[float]) -> Optional[float]:
    if celsius is None: return None
    return (celsius * 9 / 5) + 32

def _kmh_to_mph(kmh: Optional[float]) -> Optional[float]:
    if kmh is None: return None
    return kmh * 0.621371

def parse_wrh_timeseries(raw_json: dict) -> List[ParsedObservation]:
    """
    Parses NWS API JSON into a list of ParsedObservation objects.
    Data is inherently preliminary.
    """
    observations = []
    if not raw_json or 'features' not in raw_json:
        return observations
        
    for feature in raw_json['features']:
        props = feature.get('properties', {})
        
        timestamp_str = props.get('timestamp')
        if not timestamp_str:
            continue
            
        try:
            timestamp = date_parser.parse(timestamp_str)
        except Exception:
            continue
            
        temp_c = (props.get('temperature') or {}).get('value')
        dew_c = (props.get('dewpoint') or {}).get('value')
        humidity = (props.get('relativeHumidity') or {}).get('value')
        wind_dir = (props.get('windDirection') or {}).get('value')
        wind_speed_kmh = (props.get('windSpeed') or {}).get('value')
        wind_gust_kmh = (props.get('windGust') or {}).get('value')
        
        pressure_pa = (props.get('barometricPressure') or {}).get('value')
        pressure_in = pressure_pa * 0.0002953 if pressure_pa is not None else None
        
        precip_m = (props.get('precipitationLastHour') or {}).get('value')
        precip_in = precip_m * 39.3701 if precip_m is not None else None
        
        weather = props.get('textDescription')
        raw_metar = props.get('rawMessage')
        
        obs = ParsedObservation(
            timestamp=timestamp,
            temperature_f=round(_c_to_f(temp_c), 1) if temp_c is not None else None,
            dewpoint_f=round(_c_to_f(dew_c), 1) if dew_c is not None else None,
            humidity=round(humidity, 1) if humidity is not None else None,
            wind_direction=wind_dir,
            wind_speed_mph=round(_kmh_to_mph(wind_speed_kmh), 1) if wind_speed_kmh is not None else None,
            wind_gust_mph=round(_kmh_to_mph(wind_gust_kmh), 1) if wind_gust_kmh is not None else None,
            pressure_in=round(pressure_in, 2) if pressure_in is not None else None,
            precipitation_in=round(precip_in, 2) if precip_in is not None else None,
            weather_condition=weather,
            raw_metar=raw_metar,
            is_preliminary=True,
            source="wrh_json"
        )
        observations.append(obs)
        
    # NWS API returns newest first usually, we sort by timestamp ascending
    observations.sort(key=lambda x: x.timestamp)
    return observations

def parse_obhistory(raw_html: str, reference_datetime: Optional[datetime] = None) -> Tuple[List[ParsedObservation], List[str]]:
    """
    Parses NWS ObHistory HTML into a list of ParsedObservation objects.
    Returns (observations, warnings).
    """
    from typing import Tuple
    observations = []
    warnings = []
    
    if not raw_html:
        warnings.append("Empty HTML provided")
        return observations, warnings
        
    soup = BeautifulSoup(raw_html, 'html.parser')
    tables = soup.find_all('table')
    
    if not tables:
        warnings.append("no tables found")
        return observations, warnings
        
    # Table discovery logic: find table with observation headers
    data_table = None
    for table in tables:
        headers = [td.text.strip().lower() for td in table.find_all(['th', 'td'])]
        keywords = ["date", "time", "temp", "dew point", "humidity", "wind", "weather", "pressure"]
        matches = sum(1 for kw in keywords if any(kw in h for h in headers))
        if matches >= 4:
            data_table = table
            break
            
    if not data_table:
        warnings.append("no matching observation table found")
        return observations, warnings
        
    rows = data_table.find_all('tr')
    
    # Use reference_datetime for timestamp reconstruction
    ref = reference_datetime or datetime.now()
    
    skipped_rows = 0
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 16:
            continue
            
        try:
            day_str = cols[0].text.strip()
            time_str = cols[1].text.strip()
            
            if not day_str.isdigit() or ":" not in time_str:
                continue
                
            day = int(day_str)
            hour, minute = map(int, time_str.split(':'))
            
            # Timestamp reconstruction with month/year rollover
            month = ref.month
            year = ref.year
            
            # If day is greater than reference day, it must be from previous month
            if day > ref.day:
                month -= 1
                if month == 0:
                    month = 12
                    year -= 1
                    
            from dateutil.tz import gettz
            tz = gettz('US/Eastern')
            
            obs_time = datetime(year, month, day, hour, minute, tzinfo=tz)
            
            weather = cols[4].text.strip()
            sky = cols[5].text.strip()
            temp_air = cols[6].text.strip()
            
            # Extract temp
            temp_f = None
            if temp_air and temp_air != 'NA':
                try:
                    temp_f = float(temp_air)
                except ValueError:
                    temp_f = None
                    skipped_rows += 1
                    continue # Skip row if temp is malformed (not numeric)
                
            obs = ParsedObservation(
                timestamp=obs_time,
                temperature_f=temp_f,
                weather_condition=weather if weather else None,
                sky_condition=sky if sky else None,
                is_preliminary=True,
                source="obhistory_html"
            )
            observations.append(obs)
            
        except Exception as e:
            logger.debug(f"Row parsing failed: {e}")
            skipped_rows += 1
            continue
            
    if skipped_rows > 0:
        warnings.append(f"rows skipped due to malformed date/time/temp: {skipped_rows}")
        
    observations.sort(key=lambda x: x.timestamp)
    return observations, warnings

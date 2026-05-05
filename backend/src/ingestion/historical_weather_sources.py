import csv
import json
import requests
from datetime import date, datetime
from typing import List, Optional
from shared.types import HistoricalWeatherRecord

def fetch_historical_daily_highs_from_iem(
    start_date: date, 
    end_date: date, 
    station: str = "MIA"
) -> List[HistoricalWeatherRecord]:
    """
    Fetches historical daily maximum temperatures from the Iowa Environmental Mesonet (IEM).
    """
    url = "https://mesonet.agron.iastate.edu/cgi-bin/request/daily.py"
    params = {
        "network": "FL_ASOS",
        "stations": station,
        "year1": start_date.year,
        "month1": start_date.month,
        "day1": start_date.day,
        "year2": end_date.year,
        "month2": end_date.month,
        "day2": end_date.day,
        "var": "max_temp_f",
        "format": "csv"
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    records = []
    lines = response.text.strip().split("\n")
    if len(lines) < 2:
        return []
    
    reader = csv.DictReader(lines)
    for row in reader:
        try:
            # Row format: station,date,max_temp_f
            max_temp = None
            if row.get("max_temp_f") and row["max_temp_f"] != "M":
                max_temp = int(float(row["max_temp_f"]))
            
            record = HistoricalWeatherRecord(
                station=f"K{station}" if not row["station"].startswith("K") else row["station"],
                date=date.fromisoformat(row["day"]),
                max_temp_f=max_temp,
                source="IEM",
                raw_source_id=station
            )
            records.append(record)
        except (ValueError, KeyError):
            continue
            
    return records

def load_historical_daily_highs_from_local(filepath: str) -> List[HistoricalWeatherRecord]:
    """
    Loads historical daily maximum temperatures from a local JSONL file.
    """
    records = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                # Ensure date is a date object (pydantic usually does this, but we assist if mocked)
                if isinstance(data.get("date"), str):
                    data["date"] = date.fromisoformat(data["date"])
                records.append(HistoricalWeatherRecord(**data))
    except FileNotFoundError:
        return []
    return records

def save_historical_daily_highs_to_local(records: List[HistoricalWeatherRecord], filepath: str):
    """
    Saves historical daily maximum temperatures to a local JSONL file (append mode).
    """
    existing_dates = set()
    try:
        existing = load_historical_daily_highs_from_local(filepath)
        existing_dates = {r.date for r in existing}
    except Exception:
        pass

    with open(filepath, "a") as f:
        for record in records:
            if record.date not in existing_dates:
                f.write(record.model_dump_json() + "\n")
                existing_dates.add(record.date)

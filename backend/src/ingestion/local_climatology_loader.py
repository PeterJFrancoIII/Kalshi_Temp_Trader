import csv
import json
import os
from datetime import date
from typing import List, Optional, Dict, Any

def parse_int(val: str) -> Optional[int]:
    if not val or not val.strip():
        return None
    try:
        return int(val.strip())
    except ValueError:
        return None

def parse_float(val: str) -> Optional[float]:
    if not val or not val.strip():
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None

def load_local_climatology_file(path: str) -> List[Dict[str, Any]]:
    """
    Loads historical daily climatological records from a local NOAA-style CSV file.
    Only accepts records for station USW00012839.
    """
    records = []
    if not os.path.exists(path):
        return []

    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            quality_flags = []
            
            # Station Check
            station = row.get("STATION", "").strip()
            if station != "USW00012839":
                quality_flags.append("station_mismatch")
                # Even if mismatched, we might want to skip, but prompt says "Only accept rows for station USW00012839"
                continue

            # Date Check
            raw_date = row.get("DATE", "").strip()
            if not raw_date:
                quality_flags.append("missing_date")
                continue
            try:
                date.fromisoformat(raw_date)
            except ValueError:
                quality_flags.append("malformed_date")
                continue

            # TMAX
            tmax_raw = row.get("TMAX", "").strip()
            tmax_f = parse_int(tmax_raw)
            if tmax_raw in ["M", "MM", ""]:
                quality_flags.append("missing_tmax")
            elif tmax_f is None:
                quality_flags.append("malformed_tmax")

            # TMIN
            tmin_raw = row.get("TMIN", "").strip()
            tmin_f = parse_int(tmin_raw)
            if tmin_raw in ["M", "MM", ""]:
                quality_flags.append("missing_tmin")
            elif tmin_f is None:
                quality_flags.append("malformed_tmin")

            # TAVG
            tavg_f = parse_float(row.get("TAVG", ""))
            
            # PRCP
            prcp_in = parse_float(row.get("PRCP", ""))

            record = {
                "station": station,
                "name": row.get("NAME", "").strip(),
                "date": raw_date,
                "tmax_f": tmax_f,
                "tmin_f": tmin_f,
                "tavg_f": tavg_f,
                "prcp_in": prcp_in,
                "source": "local_noaa_climatological_report",
                "quality_flags": quality_flags
            }
            records.append(record)

    return records

def write_history_jsonl(records: List[Dict[str, Any]], output_path: str) -> None:
    """
    Writes normalized records to a JSONL file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

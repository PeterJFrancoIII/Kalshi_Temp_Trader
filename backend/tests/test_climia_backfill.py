import os
import json
from datetime import date
from ingestion.historical_weather_sources import load_historical_daily_highs_from_local
from shared.types import HistoricalWeatherRecord

# Canonical production history file — written by the backfill CLI.
# This file contains the full 1950-2026 KMIA climatology.
# DO NOT overwrite or modify this file from any test.
CANONICAL_HISTORY_PATH = "backend/data/processed/history/kmia_daily_history.jsonl"

def test_load_canonical_history():
    """
    Verifies the canonical production JSONL file contains the full KMIA backfill.
    Expects exactly 27,879 records from 1950-01-01 to 2026-04-30.
    """
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../data/processed/history/kmia_daily_history.jsonl")
    )

    assert os.path.exists(path), f"Canonical history file not found at {path}"

    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    assert len(records) == 27879, (
        f"Expected exactly 27,879 records from full backfill, got {len(records)} from {path}"
    )
    assert records[0]["station"] == "USW00012839", (
        f"Expected station 'USW00012839', got {records[0]['station']!r}"
    )
    assert records[0]["date"] == "1950-01-01", (
        f"Expected first date '1950-01-01', got {records[0]['date']!r}"
    )
    assert records[-1]["date"] == "2026-04-30", (
        f"Expected last date '2026-04-30', got {records[-1]['date']!r}"
    )
    valid = [r for r in records if r.get("tmax_f") is not None]
    assert len(valid) == 27879, (
        f"Expected 27,879 records with valid tmax_f, got {len(valid)}"
    )
    assert isinstance(valid[0]["tmax_f"], int)
    print(
        f"test_load_canonical_history PASSED "
        f"({len(records)} records, {records[0]['date']} to {records[-1]['date']})"
    )

def test_historical_record_mapping():
    """
    Verifies that a historical record maps correctly to bins.
    """
    from forecasting.bin_converter import temp_to_bin
    
    record = HistoricalWeatherRecord(
        station="KMIA",
        date=date(2025, 5, 1),
        max_temp_f=82,
        source="TEST"
    )
    
    assert temp_to_bin(record.max_temp_f) == "81-82"
    
    record.max_temp_f = 78
    assert temp_to_bin(record.max_temp_f) == "<=78"
    
    record.max_temp_f = 87
    assert temp_to_bin(record.max_temp_f) == ">=87"
    print("test_historical_record_mapping PASSED")

if __name__ == "__main__":
    test_load_canonical_history()
    test_historical_record_mapping()

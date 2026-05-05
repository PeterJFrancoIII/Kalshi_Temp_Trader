import os
import json
import tempfile
from ingestion.local_climatology_loader import load_local_climatology_file, write_history_jsonl

SAMPLE_CSV = """STATION,NAME,DATE,PRCP,TAVG,TMAX,TMIN
USW00012839,MIAMI INTERNATIONAL AIRPORT, 1950-01-01,0.00,,77,67
USW00012839,MIAMI INTERNATIONAL AIRPORT, 1950-01-02,0.10,,MM,65
USW00012838,OTHER STATION, 1950-01-03,0.00,,80,68
USW00012839,MIAMI INTERNATIONAL AIRPORT, 1950-01-04,0.00,,XX,70
USW00012839,MIAMI INTERNATIONAL AIRPORT, 2024-02-29,0.05,,82,72
"""

def test_load_local_climatology_file():
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tf:
        tf.write(SAMPLE_CSV)
        temp_path = tf.name

    try:
        records = load_local_climatology_file(temp_path)
        
        assert len(records) == 4, f"Expected 4 records, got {len(records)}: {records}"
        
        # Row 1: Valid
        assert records[0]["date"] == "1950-01-01", f"Expected 1950-01-01, got {records[0]['date']}"
        assert records[0]["tmax_f"] == 77, f"Expected 77, got {records[0]['tmax_f']}"
        assert records[0]["prcp_in"] == 0.0, f"Expected 0.0, got {records[0]['prcp_in']}"
        assert "missing_tmax" not in records[0]["quality_flags"]
        
        # Row 2: Missing TMAX (MM)
        assert records[1]["date"] == "1950-01-02", f"Expected 1950-01-02, got {records[1]['date']}"
        assert records[1]["tmax_f"] is None, f"Expected None, got {records[1]['tmax_f']}"
        assert "missing_tmax" in records[1]["quality_flags"], f"Expected missing_tmax in {records[1]['quality_flags']}"
        
        # Row 4: Malformed TMAX (XX)
        assert records[2]["date"] == "1950-01-04", f"Expected 1950-01-04, got {records[2]['date']}"
        assert records[2]["tmax_f"] is None
        assert "malformed_tmax" in records[2]["quality_flags"], f"Expected malformed_tmax in {records[2]['quality_flags']}"

        # Leap year
        assert records[3]["date"] == "2024-02-29"
        assert records[3]["tmax_f"] == 82

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    print("test_load_local_climatology_file PASSED")

def test_write_history_jsonl():
    records = [{"station": "USW00012839", "date": "1950-01-01", "tmax_f": 77}]
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as tf:
        temp_path = tf.name
    
    try:
        write_history_jsonl(records, temp_path)
        with open(temp_path, 'r') as f:
            line = f.readline()
            data = json.loads(line)
            assert data["station"] == "USW00012839"
            assert data["tmax_f"] == 77
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    print("test_write_history_jsonl PASSED")

if __name__ == "__main__":
    test_load_local_climatology_file()
    test_write_history_jsonl()

import os
from datetime import date
from ingestion.climia_parser import parse_climia_report, get_settlement_bin

def get_sample_content(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "samples", "climia", filename)
    with open(path, "r") as f:
        return f.read()

def test_parse_normal():
    raw = get_sample_content("sample_normal.txt")
    report = parse_climia_report(raw)
    
    assert report.station_name == "KMIA"
    assert report.report_date == date(2026, 5, 3)
    assert report.issue_time == "423 PM EDT SUN MAY 03 2026"
    
    assert report.max_temp_f == 82
    assert report.max_temp_time == "2:21 PM"
    assert report.record_high_f == 91
    assert report.is_record_max is False
    assert report.normal_high_f == 85
    assert report.departure_from_normal_f == -2.0
    
    assert report.min_temp_f == 72
    assert report.is_record_min is False
    assert report.min_temp_time == "8:50 AM"
    
    assert report.avg_temp_f == 77.0
    
    assert report.precipitation_in == 0.89
    assert len(report.parse_warnings) == 0
    
    # Verify settlement bin (82F should be 81-82)
    assert get_settlement_bin(raw) == "81-82"

def test_parse_missing():
    raw = get_sample_content("sample_missing.txt")
    report = parse_climia_report(raw)
    
    assert report.report_date == date(2026, 5, 3)
    assert report.max_temp_f is None
    assert report.min_temp_f is None
    assert report.avg_temp_f is None
    assert report.precipitation_in is None
    
    assert any("MAXIMUM temperature missing" in w for w in report.parse_warnings)

def test_parse_trace_and_record():
    raw = get_sample_content("sample_trace_record.txt")
    report = parse_climia_report(raw)
    
    assert report.report_date == date(2026, 5, 3)
    # 91R -> 91
    assert report.max_temp_f == 91
    assert report.is_record_max is True
    assert "MAX_RECORD" in report.record_flags
    
    # Trace precipitation -> 0.0 with trace flag
    assert report.precipitation_in == 0.0
    assert report.trace_precip_flag is True
    
    assert report.avg_temp_f == 77.0
    assert report.departure_from_normal_f == -2.0

def test_parse_incomplete():
    raw = get_sample_content("sample_incomplete.txt")
    report = parse_climia_report(raw)
    
    assert report.report_date == date(2026, 5, 3)
    assert report.max_temp_f is None
    assert report.min_temp_f is None
    assert report.precipitation_in is None
    
    assert any("MAXIMUM temperature missing" in w for w in report.parse_warnings)
    assert "INCOMPLETE" in report.raw_text


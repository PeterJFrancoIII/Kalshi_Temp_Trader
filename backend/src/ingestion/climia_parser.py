import re
from datetime import datetime
from typing import Optional, Union

from shared.types import ClimiaReport
from forecasting.bin_converter import temp_to_bin

def parse_val_int(val_str: Optional[str]) -> Optional[int]:
    if not val_str or val_str.strip() == "MM":
        return None
    try:
        # Handle 'R' record flags like '82R'
        clean_val = val_str.strip().replace("R", "")
        return int(clean_val)
    except ValueError:
        return None

def parse_val_float(val_str: Optional[str]) -> Optional[Union[float, str]]:
    if not val_str or val_str.strip() == "MM":
        return None
    val_str = val_str.strip().replace("R", "")
    if val_str == "T":
        return "T"
    try:
        return float(val_str)
    except ValueError:
        return None

def parse_climia_report(raw_text: str) -> ClimiaReport:
    parse_warnings = []
    
    # 1. Parse Date
    # ...THE MIAMI CLIMATE SUMMARY FOR MAY 3 2026...
    date_match = re.search(r"\.\.\.THE (.*?) CLIMATE SUMMARY FOR\s+(.*?)\.\.\.", raw_text)
    report_date = None
    is_correction = False
    if date_match:
        header_context = date_match.group(1).upper()
        if "CORRECTED" in header_context or "UPDATED" in header_context:
            is_correction = True
        
        date_str = date_match.group(2).strip()
        try:
            report_date = datetime.strptime(date_str, "%B %d %Y").date()
        except ValueError:
            try:
                report_date = datetime.strptime(date_str, "%b %d %Y").date()
            except ValueError:
                parse_warnings.append(f"Could not parse date string: {date_str}")
                
    if not report_date:
        # Fallback to today if testing or broken
        parse_warnings.append("Missing report date, defaulting to today.")
        report_date = datetime.now().date()

    # 2. Parse Issue Time
    # 423 PM EDT SUN MAY 03 2026
    issue_time_match = re.search(r"(\d{3,4} [AP]M [A-Z]{3,4} [A-Z]{3} [A-Z]{3} \d{1,2} \d{4})", raw_text)
    issue_time = issue_time_match.group(1) if issue_time_match else None

    # 3. Parse Station
    station_name = "KMIA"

    # Regexes for metrics
    temp_line_pattern = re.compile(
        r"(MAXIMUM|MINIMUM)\s+"
        r"(?P<obs>-?\d+R?|MM|T)\s+"
        r"(?:(?P<time>\d{1,2}:\d{2}\s+[AP]M)\s+)?"
        r"(?:(?P<rec>-?\d+|MM|T)\s+(?P<recyear>\d{4})\s+)?"
        r"(?P<norm>-?\d+|MM|T)\s+"
        r"(?P<dep>-?\d+|MM|T)"
    )

    avg_pattern = re.compile(
        r"AVERAGE\s+"
        r"(?P<obs>-?\d+\.?\d*|MM|T)\s+"
        r"(?P<norm>-?\d+\.?\d*|MM|T)\s+"
        r"(?P<dep>-?\d+\.?\d*|MM|T)"
    )

    precip_pattern = re.compile(
        r"TODAY\s+"
        r"(?P<obs>-?\d+\.?\d*|MM|T)\s+"
        r"(?:(?P<rec>-?\d+\.?\d*|MM|T)\s+(?P<recyear>\d{4})\s+)?"
        r"(?P<norm>-?\d+\.?\d*|MM|T)\s+"
        r"(?P<dep>-?\d+\.?\d*|MM|T)"
    )

    # Initialize fields
    obs_max, max_time, obs_min, min_time = None, None, None, None
    avg_temp, dep_temp = None, None
    norm_high, norm_low = None, None
    rec_high, rec_low = None, None
    is_rec_max, is_rec_min = False, False
    precip = None
    precip_trace = False

    # Parse Temperatures
    for match in temp_line_pattern.finditer(raw_text):
        item = match.group(1)
        raw_obs = match.group("obs")
        is_r = "R" in (raw_obs or "")
        
        if item == "MAXIMUM" and obs_max is None:
            obs_max = parse_val_int(raw_obs)
            is_rec_max = is_r
            max_time = match.group("time")
            norm_high = parse_val_int(match.group("norm"))
            rec_high = parse_val_int(match.group("rec"))
        elif item == "MINIMUM" and obs_min is None:
            obs_min = parse_val_int(raw_obs)
            is_rec_min = is_r
            min_time = match.group("time")
            norm_low = parse_val_int(match.group("norm"))
            rec_low = parse_val_int(match.group("rec"))

    # Parse Average
    avg_match = avg_pattern.search(raw_text)
    if avg_match:
        avg_temp = parse_val_float(avg_match.group("obs"))
        dep_temp = parse_val_float(avg_match.group("dep"))

    # Parse Precipitation
    precip_section_match = re.search(r"PRECIPITATION \(IN\)(.*?)(?:SNOWFALL|$)", raw_text, re.DOTALL)
    if precip_section_match:
        precip_section = precip_section_match.group(1)
        p_match = precip_pattern.search(precip_section)
        if p_match:
            raw_precip = p_match.group("obs")
            if raw_precip == "T":
                precip = 0.0
                precip_trace = True
            else:
                precip = parse_val_float(raw_precip)
                if isinstance(precip, str):
                    precip = None

    # Missing core values checks
    if obs_max is None:
        parse_warnings.append("MAXIMUM temperature missing or could not be parsed.")

    record_flags = []
    if is_rec_max:
        record_flags.append("MAX_RECORD")
    if is_rec_min:
        record_flags.append("MIN_RECORD")

    return ClimiaReport(
        report_date=report_date,
        issue_time=issue_time,
        station_name=station_name,
        max_temp_f=obs_max,
        max_temp_time=max_time,
        min_temp_f=obs_min,
        min_temp_time=min_time,
        avg_temp_f=avg_temp,
        departure_from_normal_f=dep_temp,
        normal_high_f=norm_high,
        normal_low_f=norm_low,
        record_high_f=rec_high,
        record_low_f=rec_low,
        is_record_max=is_rec_max,
        is_record_min=is_rec_min,
        record_flags=record_flags,
        precipitation_in=precip,
        trace_precip_flag=precip_trace,
        is_correction=is_correction,
        raw_text=raw_text,
        parse_warnings=parse_warnings
    )

def get_settlement_max_temp(raw_text: str) -> Optional[int]:
    """
    Helper to directly get the settlement high from raw CLIMIA text.
    """
    report = parse_climia_report(raw_text)
    return report.max_temp_f

def get_settlement_bin(raw_text: str) -> Optional[str]:
    """
    Helper to determine the winning probability bin from raw CLIMIA text.
    """
    max_temp = get_settlement_max_temp(raw_text)
    if max_temp is None:
        return None
    return temp_to_bin(max_temp)

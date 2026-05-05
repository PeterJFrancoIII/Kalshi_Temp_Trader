import re
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ClimiaReport(BaseModel):
    station: str = "KMIA"
    report_date: str
    issue_time: str
    max_temp_f: Optional[int]
    is_record_max: bool = False
    raw_text: str

class ClimiaParser:
    """Parses the NWS CLIMIA (CLI) text product for daily maximum temperatures."""
    
    def __init__(self):
        # Regex to match the date in the header
        self.date_pattern = re.compile(r"\.\.\.THE MIAMI CLIMATE SUMMARY FOR (.*?) (\d{4})\.\.\.", re.IGNORECASE)
        # Regex to match issue time
        self.issue_time_pattern = re.compile(r"VALID (?:TODAY )?AS OF (\d{4} [AP]M) LOCAL TIME\.", re.IGNORECASE)
        # Regex for the MAXIMUM temperature line under TEMPERATURE (F)
        self.max_temp_pattern = re.compile(r"^MAXIMUM\s+(-?\d+|MM)R?\s+", re.MULTILINE)
        
    def parse(self, raw_text: str) -> ClimiaReport:
        date_match = self.date_pattern.search(raw_text)
        issue_time_match = self.issue_time_pattern.search(raw_text)
        
        report_date = f"{date_match.group(1)} {date_match.group(2)}" if date_match else "UNKNOWN"
        issue_time = issue_time_match.group(1) if issue_time_match else "UNKNOWN"
        
        # Isolate the temperature section to avoid matching 'MAXIMUM' elsewhere
        temp_section_start = raw_text.find("TEMPERATURE (F)")
        if temp_section_start != -1:
            temp_section = raw_text[temp_section_start:temp_section_start+1000]
        else:
            temp_section = raw_text
            
        max_temp_match = self.max_temp_pattern.search(temp_section)
        
        max_temp_f = None
        is_record_max = False
        
        if max_temp_match:
            val = max_temp_match.group(1)
            if val != "MM":
                max_temp_f = int(val)
            # Check if there is an R right after the value or somewhere on the line
            full_line = max_temp_match.group(0)
            if "R" in temp_section.split("\n")[max_temp_match.lastindex or 0]: # rough check
                pass
                
            # More robust record check
            line_end = temp_section.find("\n", max_temp_match.start())
            line = temp_section[max_temp_match.start():line_end]
            if "R" in line.split()[1]: # if the value itself has R appended e.g., 85R
                 is_record_max = True
        
        return ClimiaReport(
            report_date=report_date,
            issue_time=issue_time,
            max_temp_f=max_temp_f,
            is_record_max=is_record_max,
            raw_text=raw_text
        )

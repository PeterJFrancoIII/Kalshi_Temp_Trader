from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from forecasting.bin_converter import temp_to_bin as temp_to_required_bin

REQUIRED_BINS = ["<=78", "79-80", "81-82", "83-84", "85-86", ">=87"]

def count_records_by_bin(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Counts how many records fall into each required bin.
    """
    counts = {b: 0 for b in REQUIRED_BINS}
    for r in records:
        tmax = r.get("tmax_f")
        if tmax is not None:
            b = temp_to_required_bin(tmax)
            if b in counts:
                counts[b] += 1
    return counts

def bin_distribution(records: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Computes the probability distribution across bins for the given records.
    """
    counts = count_records_by_bin(records)
    total = sum(counts.values())
    if total == 0:
        return {b: 0.0 for b in REQUIRED_BINS}
    
    return {b: round(count / total, 4) for b, count in counts.items()}

def same_day_history(
    records: List[Dict[str, Any]], 
    target_date: str, 
    years_back: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Returns records for the same month and day across previous years.
    """
    target = date.fromisoformat(target_date)
    results = []
    
    # Filter by month/day and year < target_year
    for r in records:
        r_date = date.fromisoformat(r["date"])
        if r_date.month == target.month and r_date.day == target.day:
            if r_date.year < target.year:
                results.append(r)
                
    # Sort by year descending
    results.sort(key=lambda x: x["date"], reverse=True)
    
    if years_back:
        return results[:years_back]
    return results

def prior_bin_distribution_for_date(
    records: List[Dict[str, Any]], 
    target_date: str, 
    window_days: int = 0, 
    years_back: Optional[int] = None
) -> Dict[str, float]:
    """
    Computes historical bin distribution for a target date with an optional seasonal window.
    """
    target = date.fromisoformat(target_date)
    relevant_records = []
    
    # Use a dummy year to calculate day-of-year proximity correctly across month/day
    # Handling leap years by using a leap year as base
    base_year = 2000
    try:
        target_ref = date(base_year, target.month, target.day)
    except ValueError:
        # Handle Feb 29 if target_date is Feb 29 but base_year is not leap (2000 is)
        target_ref = date(base_year, 2, 28)

    for r in records:
        r_date = date.fromisoformat(r["date"])
        
        # Lookahead check: Exclude target year if record date >= target date
        if r_date.year == target.year and r_date >= target:
            continue
            
        # Proximity check
        try:
            r_ref = date(base_year, r_date.month, r_date.day)
        except ValueError:
            # Handle Feb 29
            r_ref = date(base_year, 2, 28)
            
        diff = abs((target_ref - r_ref).days)
        # Handle wraparound
        if diff > 182:
            diff = 366 - diff
            
        if diff <= window_days:
            relevant_records.append(r)

    # Years back filter (optional)
    if years_back:
        # Sort by date and take most recent years
        relevant_records.sort(key=lambda x: x["date"], reverse=True)
        # This is tricky because one year might have multiple records in the window
        # But usually we just want the last N years of data for this window.
        # For simplicity, we'll just take the records from the last N distinct years.
        seen_years = set()
        filtered = []
        for r in relevant_records:
            yr = date.fromisoformat(r["date"]).year
            if yr not in seen_years:
                if len(seen_years) >= years_back:
                    break
                seen_years.add(yr)
            filtered.append(r)
        relevant_records = filtered

    return bin_distribution(relevant_records)

def rolling_high_average(
    records: List[Dict[str, Any]], 
    end_date: str, 
    window_days: int = 7
) -> Optional[float]:
    """
    Average TMAX for the window_days immediately preceding end_date.
    """
    end = date.fromisoformat(end_date)
    start = end - timedelta(days=window_days)
    
    temps = []
    for r in records:
        r_date = date.fromisoformat(r["date"])
        if start <= r_date < end:
            if r.get("tmax_f") is not None:
                temps.append(r["tmax_f"])
                
    if not temps:
        return None
    return round(sum(temps) / len(temps), 2)

def normal_like_high_for_date(
    records: List[Dict[str, Any]], 
    target_date: str, 
    window_days: int = 7, 
    years_back: Optional[int] = 30
) -> Optional[float]:
    """
    Computes a 'normal' high (climatological mean) for a target date window.
    """
    target = date.fromisoformat(target_date)
    temps = []
    
    base_year = 2000
    target_ref = date(base_year, target.month, target.day)
    
    # Pre-filter for lookahead and years
    start_year = target.year - years_back if years_back else 1900
    
    for r in records:
        r_date = date.fromisoformat(r["date"])
        if r_date.year >= target.year:
            continue
        if r_date.year < start_year:
            continue
            
        try:
            r_ref = date(base_year, r_date.month, r_date.day)
        except ValueError:
            r_ref = date(base_year, 2, 28)
            
        diff = abs((target_ref - r_ref).days)
        if diff > 182:
            diff = 366 - diff
            
        if diff <= window_days:
            if r.get("tmax_f") is not None:
                temps.append(r["tmax_f"])
                
    if not temps:
        return None
    return round(sum(temps) / len(temps), 2)

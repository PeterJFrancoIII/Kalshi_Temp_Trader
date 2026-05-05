import argparse
import sys
from ingestion.local_climatology_loader import load_local_climatology_file, write_history_jsonl

def main():
    parser = argparse.ArgumentParser(description="Backfill KMIA historical history from local NOAA file.")
    parser.add_argument("--input", required=True, help="Path to the input climatological report (CSV/TXT).")
    parser.add_argument("--output", default="backend/data/processed/history/kmia_daily_history.jsonl", help="Path to the output JSONL file.")
    
    args = parser.parse_args()
    
    print(f"Reading local climatology file: {args.input}")
    records = load_local_climatology_file(args.input)
    
    if not records:
        print("No records found or file does not exist.")
        sys.exit(1)
        
    total_rows = len(records)
    valid_records = [r for r in records if r.get("tmax_f") is not None]
    missing_tmax_count = total_rows - len(valid_records)
    
    dates = [r["date"] for r in records]
    min_date = min(dates) if dates else "N/A"
    max_date = max(dates) if dates else "N/A"
    
    print(f"Total rows read: {total_rows}")
    print(f"Valid records (with TMAX): {len(valid_records)}")
    print(f"Missing TMAX count: {missing_tmax_count}")
    print(f"Date range: {min_date} to {max_date}")
    
    print(f"Writing to: {args.output}")
    write_history_jsonl(records, args.output)
    print("Done.")

if __name__ == "__main__":
    main()

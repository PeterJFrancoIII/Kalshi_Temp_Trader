import os
import json
import argparse
import glob
import logging
from typing import List, Dict, Any
from calibration.aggregate_reports import (
    aggregate_model_comparisons,
    write_aggregate_calibration_json,
    write_aggregate_calibration_markdown
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Generate aggregate calibration report from comparison JSON files.")
    parser.add_argument("--input-dir", required=True, help="Directory containing comparison JSON files.")
    parser.add_argument("--output-dir", required=True, help="Directory to save the aggregate report.")
    
    args = parser.parse_args()
    
    input_dir = args.input_dir
    output_dir = args.output_dir
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Read all JSON files
    comparison_records = []
    if os.path.exists(input_dir):
        json_files = glob.glob(os.path.join(input_dir, "*.json"))
        # Exclude aggregate_calibration.json if it's in the same dir
        json_files = [f for f in json_files if os.path.basename(f) != "aggregate_calibration.json"]
        
        for fpath in json_files:
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                    comparison_records.append(data)
            except json.JSONDecodeError:
                logger.warning(f"Malformed JSON skipped: {fpath}")
            except Exception as e:
                logger.warning(f"Error reading {fpath}: {e}")
    else:
        logger.warning(f"Input directory does not exist: {input_dir}")
        
    # Aggregate
    stats = aggregate_model_comparisons(comparison_records)
    
    # Save JSON
    json_output_path = os.path.join(output_dir, "aggregate_calibration.json")
    write_aggregate_calibration_json(stats, json_output_path)
    logger.info(f"Saved aggregate JSON to {json_output_path}")
        
    # Save Markdown
    md_output_path = os.path.join(output_dir, "aggregate_calibration.md")
    write_aggregate_calibration_markdown(stats, md_output_path)
    logger.info(f"Saved aggregate Markdown to {md_output_path}")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

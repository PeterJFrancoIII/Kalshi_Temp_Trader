import json
import os
from typing import List, Dict, Optional

class JSONLStore:
    """
    Simple JSONL storage handler to append and read records.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def append_record(self, record: Dict):
        """Append a single record to the file."""
        with open(self.file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record) + '\n')

    def load_records(self) -> List[Dict]:
        """Load all records from the file."""
        if not os.path.exists(self.file_path):
            return []
        
        records = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def update_record(self, match_key: str, match_value: any, updated_fields: Dict) -> bool:
        """
        Updates the first record where record[match_key] == match_value.
        Replaces the whole file - use with caution for large files.
        """
        records = self.load_records()
        updated = False
        for i, record in enumerate(records):
            if record.get(match_key) == match_value:
                records[i].update(updated_fields)
                updated = True
                break
        
        if updated:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
        
        return updated

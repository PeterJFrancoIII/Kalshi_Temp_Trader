#!/usr/bin/env python3
"""Append unique NWS/TWC observed rows into compact JSONL history files.

This script is intentionally append-only and uses sidecar key indexes so routine
updates do not repeatedly rewrite or scan large history files.

NO REAL TRADING EXECUTION
DRY-RUN / PAPER EVALUATION ONLY
"""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "backend" / "data" / "processed"
NWS_DIR = PROCESSED / "weather_nws"
TWC_DIR = PROCESSED / "weather_company"

NWS_LATEST = NWS_DIR / "latest_nws_kmia_snapshot.json"
TWC_LATEST = TWC_DIR / "latest_twc_kmia_snapshot.json"
NWS_HISTORY = NWS_DIR / "nws_observed_history.jsonl"
TWC_HISTORY = TWC_DIR / "twc_observed_history.jsonl"
NWS_INDEX = NWS_DIR / "nws_observed_history.keys"
TWC_INDEX = TWC_DIR / "twc_observed_history.keys"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def key_for(row: Dict[str, Any], provider: str) -> Optional[str]:
    ts = row.get("timestamp_utc") or row.get("observation_time_utc") or row.get("valid_time_utc") or row.get("fetched_at_utc")
    station = row.get("station") or "KMIA"
    if not ts:
        return None
    return f"{provider}|{station}|{ts}"


def rebuild_index(history_file: Path, key_file: Path, provider: str) -> Set[str]:
    keys: Set[str] = set()
    if history_file.exists():
        with history_file.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                key = key_for(row, provider)
                if key:
                    keys.add(key)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text("\n".join(sorted(keys)) + ("\n" if keys else ""))
    return keys


def load_keys(history_file: Path, key_file: Path, provider: str) -> Set[str]:
    if key_file.exists():
        return {line.strip() for line in key_file.read_text().splitlines() if line.strip()}
    return rebuild_index(history_file, key_file, provider)


def append_unique(rows: Iterable[Dict[str, Any]], history_file: Path, key_file: Path, provider: str) -> int:
    history_file.parent.mkdir(parents=True, exist_ok=True)
    keys = load_keys(history_file, key_file, provider)
    added_keys: List[str] = []
    added_count = 0
    with history_file.open("a") as hist:
        for row in rows:
            key = key_for(row, provider)
            if not key or key in keys:
                continue
            normalized = dict(row)
            normalized.setdefault("provider", provider)
            normalized.setdefault("station", "KMIA")
            hist.write(json.dumps(normalized, sort_keys=True) + "\n")
            keys.add(key)
            added_keys.append(key)
            added_count += 1
    if added_keys:
        with key_file.open("a") as idx:
            for key in added_keys:
                idx.write(key + "\n")
    return added_count


def nws_observed_rows(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = snapshot.get("recent_observations_table") or []
    out: List[Dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    fetched = snapshot.get("fetched_at_utc")
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item.setdefault("provider", "nws")
        item.setdefault("station", "KMIA")
        item.setdefault("fetched_at_utc", fetched)
        out.append(item)
    return out


def twc_observed_rows(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    current = snapshot.get("current_conditions") or {}
    status = (snapshot.get("endpoint_status") or {}).get("current_conditions", {}).get("status")
    if status != "OK" or not isinstance(current, dict):
        return []
    if current.get("temperature_f") is None and current.get("dewpoint_f") is None:
        return []
    item = dict(current)
    item.setdefault("provider", "twc")
    item.setdefault("station", "KMIA")
    item.setdefault("geocode", snapshot.get("geocode"))
    item.setdefault("fetched_at_utc", snapshot.get("fetched_at_utc"))
    return [item]


def main() -> None:
    nws_snapshot = load_json(NWS_LATEST)
    twc_snapshot = load_json(TWC_LATEST)
    nws_added = append_unique(nws_observed_rows(nws_snapshot), NWS_HISTORY, NWS_INDEX, "nws")
    twc_added = append_unique(twc_observed_rows(twc_snapshot), TWC_HISTORY, TWC_INDEX, "twc")
    print("observed_history_archive:")
    print(f"  nws_added: {nws_added}")
    print(f"  twc_added: {twc_added}")
    print(f"  nws_history: {NWS_HISTORY}")
    print(f"  twc_history: {TWC_HISTORY}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Probe likely The Weather Company observed endpoint paths.

This script is read-only and does not modify snapshots. It is intended to find
which observed/current or observed time-series endpoint, if any, the current TWC
API key is authorized to use for KMIA.

NO REAL TRADING EXECUTION
DRY-RUN / PAPER EVALUATION ONLY
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

import requests

BASE_URL = os.getenv("TWC_BASE_URL", "https://api.weather.com").rstrip("/")
GEOCODE = os.getenv("TWC_GEOCODE", "25.7959,-80.2870")
UNITS = os.getenv("TWC_UNITS", "e")
LANGUAGE = os.getenv("TWC_LANGUAGE", "en-US")
TIMEOUT_SECONDS = int(os.getenv("TWC_TIMEOUT_SECONDS", "15"))

NOW = datetime.now(timezone.utc)
START = int((NOW - timedelta(hours=36)).timestamp())
END = int(NOW.timestamp())
DATE = NOW.strftime("%Y%m%d")
YESTERDAY = (NOW - timedelta(days=1)).strftime("%Y%m%d")

# Candidate paths and extra params. Product naming and entitlements vary by TWC package.
CANDIDATES: List[Tuple[str, Dict[str, str]]] = [
    ("/v3/wx/conditions/current", {}),
    ("/v3/wx/observations/current", {}),
    ("/v3/wx/observations/current/point", {}),
    ("/v3/wx/observations/hourly/1day", {}),
    ("/v3/wx/observations/hourly/7day", {}),
    ("/v3/wx/observations/timeseries/1day", {}),
    ("/v3/wx/observations/timeseries/24hour", {}),
    ("/v3/wx/observations/historical/24hour", {}),
    ("/v3/wx/observations/historical", {"startDateTime": str(START), "endDateTime": str(END)}),
    ("/v3/wx/observations/historical", {"startTime": str(START), "endTime": str(END)}),
    ("/v3/wx/observations/historical", {"date": DATE}),
    ("/v3/wx/observations/historical", {"date": YESTERDAY}),
    ("/v2/observations/current", {}),
    ("/v2/observations/current/point", {}),
    ("/v2/observations/hourly/1day", {}),
    ("/v2/observations/historical", {"startDateTime": str(START), "endDateTime": str(END)}),
    ("/v1/geocode/{geocode}/observations/current.json", {}),
    ("/v1/geocode/{geocode}/observations/hourly/1day.json", {}),
    ("/v1/geocode/{geocode}/observations/timeseries.json", {"startDateTime": str(START), "endDateTime": str(END)}),
    ("/v1/geocode/{geocode}/observations/historical.json", {"date": DATE}),
    ("/v1/geocode/{geocode}/observations/historical.json", {"date": YESTERDAY}),
]


def api_key() -> str:
    return os.getenv("TWC_API_KEY") or os.getenv("WEATHER_COMPANY_API_KEY") or ""


def build_url(path: str) -> str:
    if "{geocode}" in path:
        return f"{BASE_URL}{path.format(geocode=GEOCODE)}"
    return f"{BASE_URL}{path}"


def params_for(path: str, key: str, extra: Dict[str, str]) -> Dict[str, str]:
    params = {
        "apiKey": key,
        "format": "json",
        "language": LANGUAGE,
        "units": UNITS,
    }
    if "{geocode}" not in path:
        params["geocode"] = GEOCODE
    params.update(extra)
    return params


def count_rows(body) -> int:
    if isinstance(body, list):
        return len(body)
    if not isinstance(body, dict):
        return 0
    for key in ["validTimeUtc", "obsTime", "observationTimeUtc", "temperature", "relativeHumidity", "observations", "data"]:
        val = body.get(key)
        if isinstance(val, list):
            return len(val)
    return 1 if body else 0


def probe(path: str, extra: Dict[str, str], key: str) -> Dict[str, object]:
    url = build_url(path)
    params = params_for(path, key, extra)
    try:
        resp = requests.get(url, params=params, headers={"Accept-Encoding": "gzip"}, timeout=TIMEOUT_SECONDS)
        try:
            body = resp.json()
            preview = json.dumps(body)[:800]
            keys = list(body.keys())[:30] if isinstance(body, dict) else []
            rows = count_rows(body)
        except Exception:
            preview = resp.text[:800]
            keys = []
            rows = 0
        return {
            "path": path,
            "extra_params": extra,
            "url": url,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("Content-Type"),
            "ok": 200 <= resp.status_code < 300,
            "row_count_guess": rows,
            "keys": keys,
            "body_preview": preview,
        }
    except Exception as exc:
        return {"path": path, "extra_params": extra, "url": url, "ok": False, "error": str(exc)}


def main() -> None:
    key = api_key()
    if not key:
        raise SystemExit("TWC_API_KEY or WEATHER_COMPANY_API_KEY is not set.")
    print("====================================================")
    print("      PROBING TWC OBSERVED ENDPOINTS")
    print("      NO REAL TRADING EXECUTION")
    print("====================================================")
    print(f"base_url: {BASE_URL}")
    print(f"geocode: {GEOCODE}")
    print(f"key_length: {len(key)}")
    print(f"start_utc_epoch: {START}")
    print(f"end_utc_epoch: {END}")
    print("----------------------------------------------------")
    results = [probe(path, extra, key) for path, extra in CANDIDATES]
    for r in results:
        status = r.get("status_code", "ERR")
        ok = "OK" if r.get("ok") else "NO"
        extra = r.get("extra_params") or {}
        rows = r.get("row_count_guess")
        print(f"{ok:>2} {status} rows={rows} {r.get('path')} params={extra}")
        if r.get("ok"):
            print("   keys:", r.get("keys"))
            print("   preview:", r.get("body_preview"))
    print("----------------------------------------------------")
    print("JSON_RESULTS")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Probe likely The Weather Company observed/current-condition endpoint paths.

This script is read-only and does not modify snapshots. It is intended to find
which observed/current endpoint, if any, the current TWC API key is authorized to
use for KMIA.

NO REAL TRADING EXECUTION
DRY-RUN / PAPER EVALUATION ONLY
"""

import json
import os
from typing import Dict, List

import requests

BASE_URL = os.getenv("TWC_BASE_URL", "https://api.weather.com").rstrip("/")
GEOCODE = os.getenv("TWC_GEOCODE", "25.7959,-80.2870")
UNITS = os.getenv("TWC_UNITS", "e")
LANGUAGE = os.getenv("TWC_LANGUAGE", "en-US")
TIMEOUT_SECONDS = int(os.getenv("TWC_TIMEOUT_SECONDS", "15"))

# These are candidates only. Product naming and entitlements vary by TWC package.
CANDIDATE_PATHS: List[str] = [
    "/v3/wx/conditions/current",
    "/v3/wx/observations/current",
    "/v3/wx/observations/current/point",
    "/v3/wx/conditions/current/point",
    "/v2/observations/current",
    "/v2/observations/current/point",
    "/v1/geocode/{geocode}/observations/current.json",
]


def api_key() -> str:
    return os.getenv("TWC_API_KEY") or os.getenv("WEATHER_COMPANY_API_KEY") or ""


def build_url(path: str) -> str:
    if "{geocode}" in path:
        return f"{BASE_URL}{path.format(geocode=GEOCODE)}"
    return f"{BASE_URL}{path}"


def params_for(path: str, key: str) -> Dict[str, str]:
    params = {
        "apiKey": key,
        "format": "json",
        "language": LANGUAGE,
        "units": UNITS,
    }
    if "{geocode}" not in path:
        params["geocode"] = GEOCODE
    return params


def probe(path: str, key: str) -> Dict[str, object]:
    url = build_url(path)
    try:
        resp = requests.get(
            url,
            params=params_for(path, key),
            headers={"Accept-Encoding": "gzip"},
            timeout=TIMEOUT_SECONDS,
        )
        preview = ""
        try:
            body = resp.json()
            preview = json.dumps(body)[:600]
            keys = list(body.keys())[:20] if isinstance(body, dict) else []
        except Exception:
            preview = resp.text[:600]
            keys = []
        return {
            "path": path,
            "url": url,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("Content-Type"),
            "ok": 200 <= resp.status_code < 300,
            "keys": keys,
            "body_preview": preview,
        }
    except Exception as exc:
        return {"path": path, "url": url, "ok": False, "error": str(exc)}


def main() -> None:
    key = api_key()
    if not key:
        raise SystemExit("TWC_API_KEY or WEATHER_COMPANY_API_KEY is not set.")
    print("====================================================")
    print("      PROBING TWC OBSERVED/CURRENT ENDPOINTS")
    print("      NO REAL TRADING EXECUTION")
    print("====================================================")
    print(f"base_url: {BASE_URL}")
    print(f"geocode: {GEOCODE}")
    print(f"key_length: {len(key)}")
    print("----------------------------------------------------")
    results = [probe(path, key) for path in CANDIDATE_PATHS]
    for r in results:
        status = r.get("status_code", "ERR")
        ok = "OK" if r.get("ok") else "NO"
        print(f"{ok:>2} {status} {r.get('path')}")
        if r.get("ok"):
            print("   keys:", r.get("keys"))
            print("   preview:", r.get("body_preview"))
    print("----------------------------------------------------")
    print("JSON_RESULTS")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

"""Read-only The Weather Company ingestion for KMIA.

NWS KMIA remains the settlement/verification target. This client pulls TWC
point data into a normalized local snapshot. Daily TWC data is useful as a
forecast summary. TWC observed history is built locally by archiving each
successful current observation because the current API entitlement only returns
one observed row at a time.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

KMIA_GEOCODE = "25.7959,-80.2870"
BASE_URL = os.getenv("TWC_BASE_URL", "https://api.weather.com").rstrip("/")
LANGUAGE = os.getenv("TWC_LANGUAGE", "en-US")
UNITS = os.getenv("TWC_UNITS", "e")
TIMEOUT_SECONDS = int(os.getenv("TWC_TIMEOUT_SECONDS", "15"))

ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = ROOT / "backend" / "data" / "processed" / "weather_company"
RAW_DIR = ROOT / "backend" / "data" / "raw" / "weather_company"
LATEST_FILE = PROCESSED_DIR / "latest_twc_kmia_snapshot.json"
OBSERVED_HISTORY_FILE = PROCESSED_DIR / "twc_observed_history.jsonl"

DEFAULT_ENDPOINTS = {
    "current_conditions": os.getenv("TWC_CURRENT_CONDITIONS_PATH", "/v3/wx/observations/current"),
    "daily_forecast": os.getenv("TWC_DAILY_FORECAST_PATH", "/v3/wx/forecast/daily/15day"),
    "hourly_forecast": os.getenv("TWC_HOURLY_FORECAST_PATH", "/v3/wx/forecast/hourly/15day"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def pick(d: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in d and d[key] is not None:
            return d[key]
    return None


def list_field(d: Dict[str, Any], *keys: str) -> List[Any]:
    for key in keys:
        value = d.get(key)
        if isinstance(value, list):
            return value
    return []


def at(values: List[Any], idx: int) -> Any:
    return values[idx] if idx < len(values) else None


def status_from_response(resp: requests.Response) -> Dict[str, Any]:
    return {
        "status_code": resp.status_code,
        "cache_control": resp.headers.get("Cache-Control"),
        "expires": resp.headers.get("Expires"),
        "content_type": resp.headers.get("Content-Type"),
    }


class TWCKMIAClient:
    def __init__(self, api_key: Optional[str] = None, geocode: str = KMIA_GEOCODE):
        self.api_key = api_key or os.getenv("TWC_API_KEY") or os.getenv("WEATHER_COMPANY_API_KEY")
        self.geocode = geocode

    def request_endpoint(self, name: str, path: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        if not self.api_key:
            return None, {
                "endpoint": name,
                "path": path,
                "status": "MISSING_API_KEY",
                "warning": "Set TWC_API_KEY or WEATHER_COMPANY_API_KEY.",
            }

        url = f"{BASE_URL}{path}"
        params = {
            "apiKey": self.api_key,
            "format": "json",
            "geocode": self.geocode,
            "language": LANGUAGE,
            "units": UNITS,
        }
        headers = {"Accept-Encoding": "gzip"}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT_SECONDS)
            meta = status_from_response(resp)
            meta.update({"endpoint": name, "path": path})
            if resp.status_code == 204:
                meta["status"] = "NO_DATA"
                return None, meta
            if resp.status_code in (401, 403):
                meta["status"] = "UNAUTHORIZED_OR_FORBIDDEN"
                return None, meta
            if resp.status_code == 406:
                meta["status"] = "NOT_ACCEPTABLE_CHECK_GZIP"
                return None, meta
            if resp.status_code >= 400:
                meta["status"] = "HTTP_ERROR"
                meta["body_preview"] = resp.text[:500]
                return None, meta
            meta["status"] = "OK"
            return resp.json(), meta
        except requests.Timeout:
            return None, {"endpoint": name, "path": path, "status": "TIMEOUT"}
        except Exception as exc:
            return None, {"endpoint": name, "path": path, "status": "ERROR", "error": str(exc)}

    def fetch_raw_bundle(self) -> Dict[str, Any]:
        bundle: Dict[str, Any] = {
            "provider": "the_weather_company",
            "station": "KMIA",
            "geocode": self.geocode,
            "fetched_at_utc": utc_now(),
            "api_units": UNITS,
            "language": LANGUAGE,
            "endpoints": {},
            "responses": {},
            "safety": {"no_real_trading": True},
        }
        for name, path in DEFAULT_ENDPOINTS.items():
            data, meta = self.request_endpoint(name, path)
            bundle["responses"][name] = data
            bundle["endpoints"][name] = meta
        return bundle


def normalize_current(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    return {
        "temperature_f": pick(data, "temperature", "temp", "temperatureMaxSince7Am", "temperatureFeelsLike"),
        "dewpoint_f": pick(data, "temperatureDewPoint", "dewPoint", "dewpt"),
        "relative_humidity_pct": pick(data, "relativeHumidity", "humidity"),
        "wind_speed_mph": pick(data, "windSpeed", "wspd"),
        "wind_direction_degrees": pick(data, "windDirection", "wdir"),
        "wind_direction_cardinal": pick(data, "windDirectionCardinal", "wdirCardinal"),
        "cloud_cover_pct": pick(data, "cloudCover"),
        "cloud_cover_phrase": pick(data, "cloudCoverPhrase"),
        "pressure_altimeter_in": pick(data, "pressureAltimeter"),
        "pressure_mean_sea_level_mb": pick(data, "pressureMeanSeaLevel"),
        "precip_1h_in": pick(data, "precip1Hour"),
        "phrase": pick(data, "wxPhraseLong", "phrase", "narrative", "cloudCoverPhrase"),
        # expireTimeGmt / expirationTimeUtc are cache-expiry fields, NOT observation times —
        # they must not appear here, as they would silently corrupt freshness checks.
        "observation_time_utc": pick(data, "validTimeUtc", "observationTimeUtc"),
    }


def normalize_daily(data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    valid = list_field(data, "validTimeUtc", "fcstValid", "dayOfWeek")
    max_t = list_field(data, "temperatureMax", "calendarDayTemperatureMax", "maxTemp")
    min_t = list_field(data, "temperatureMin", "calendarDayTemperatureMin", "minTemp")
    narrative = list_field(data, "narrative", "daypartNarrative")
    pop = list_field(data, "precipChance", "probabilityOfPrecipitation", "pop")
    n = max(len(valid), len(max_t), len(min_t), len(narrative), len(pop), 0)
    return [{"index": i, "valid_time_utc": at(valid, i), "max_temp_f": at(max_t, i), "min_temp_f": at(min_t, i), "narrative": at(narrative, i), "precip_probability_pct": at(pop, i)} for i in range(n)]


def normalize_hourly(data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    valid_utc = list_field(data, "validTimeUtc", "fcstValid")
    valid_local = list_field(data, "validTimeLocal", "fcstValidLocal")
    temp = list_field(data, "temperature", "temp")
    dew = list_field(data, "temperatureDewPoint", "dewPoint", "dewpt")
    rh = list_field(data, "relativeHumidity", "humidity")
    wspd = list_field(data, "windSpeed", "wspd")
    wdir = list_field(data, "windDirection", "wdir")
    wcard = list_field(data, "windDirectionCardinal", "wdirCardinal")
    cloud = list_field(data, "cloudCover", "clds")
    pop = list_field(data, "precipChance", "probabilityOfPrecipitation", "pop")
    phrase = list_field(data, "wxPhraseLong", "phrase", "narrative")
    n = max(len(valid_utc), len(valid_local), len(temp), len(dew), len(rh), len(wspd), len(wdir), len(wcard), len(cloud), len(pop), len(phrase), 0)
    return [{"index": i, "valid_time_utc": at(valid_utc, i), "valid_time_local": at(valid_local, i), "temperature_f": at(temp, i), "dewpoint_f": at(dew, i), "relative_humidity_pct": at(rh, i), "wind_speed_mph": at(wspd, i), "wind_direction_degrees": at(wdir, i), "wind_direction_cardinal": at(wcard, i), "cloud_cover_pct": at(cloud, i), "precip_probability_pct": at(pop, i), "phrase": at(phrase, i)} for i in range(n)]


def derive_features(daily: List[Dict[str, Any]], hourly: List[Dict[str, Any]]) -> Dict[str, Any]:
    daily_max = next((r.get("max_temp_f") for r in daily if isinstance(r.get("max_temp_f"), (int, float))), None)
    hourly_temps = [r["temperature_f"] for r in hourly if isinstance(r.get("temperature_f"), (int, float))]
    sea_breeze = None
    for row in hourly:
        deg = row.get("wind_direction_degrees")
        if isinstance(deg, (int, float)) and 80 <= deg <= 150:
            sea_breeze = row.get("valid_time_local") or row.get("valid_time_utc")
            break
    return {
        "forecast_high_f": daily_max,
        "hourly_max_temp_f": max(hourly_temps) if hourly_temps else None,
        "sea_breeze_shift_hour_et": sea_breeze,
        "max_cloud_cover_pct": max([r["cloud_cover_pct"] for r in hourly if isinstance(r.get("cloud_cover_pct"), (int, float))], default=None),
    }


def comparison_metadata(endpoint_status: Dict[str, Any], hourly: List[Dict[str, Any]]) -> Dict[str, Any]:
    hourly_status = endpoint_status.get("hourly_forecast", {}) if isinstance(endpoint_status, dict) else {}
    hourly_rows = len(hourly)
    ready = hourly_rows > 0 and hourly_status.get("status") == "OK"
    reason = "OK"
    if not ready:
        reason = (
            "NWS hourly data must be compared only against TWC hourly data. "
            f"TWC hourly endpoint status={hourly_status.get('status', 'MISSING')}; rows={hourly_rows}. "
            "Daily forecast data is retained as summary-only and is not used for matched interval comparisons."
        )
    return {
        "comparison_ready": ready,
        "comparison_granularity": "hourly_only",
        "twc_hourly_rows": hourly_rows,
        "twc_hourly_endpoint_status": hourly_status.get("status"),
        "reason": reason,
    }


def append_observed_history(snapshot: Dict[str, Any]) -> None:
    current = snapshot.get("current_conditions", {})
    status = snapshot.get("endpoint_status", {}).get("current_conditions", {}).get("status")
    if status != "OK" or not isinstance(current, dict):
        return
    if current.get("temperature_f") is None and current.get("dewpoint_f") is None:
        return

    observed = dict(current)
    observed.update({
        "provider": "the_weather_company",
        "station": "KMIA",
        "geocode": snapshot.get("geocode", KMIA_GEOCODE),
        "fetched_at_utc": snapshot.get("fetched_at_utc", utc_now()),
    })

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    existing_keys = set()
    if OBSERVED_HISTORY_FILE.exists():
        try:
            with OBSERVED_HISTORY_FILE.open("r") as f:
                for line in f:
                    try:
                        row = json.loads(line)
                        key = row.get("observation_time_utc") or row.get("fetched_at_utc")
                        if key:
                            existing_keys.add(str(key))
                    except Exception:
                        continue
        except Exception:
            pass
    key = observed.get("observation_time_utc") or observed.get("fetched_at_utc")
    if key and str(key) in existing_keys:
        return
    with OBSERVED_HISTORY_FILE.open("a") as f:
        f.write(json.dumps(observed, sort_keys=True) + "\n")


def normalize_bundle(raw: Dict[str, Any]) -> Dict[str, Any]:
    responses = raw.get("responses", {})
    current = normalize_current(responses.get("current_conditions"))
    daily = normalize_daily(responses.get("daily_forecast"))
    hourly = normalize_hourly(responses.get("hourly_forecast"))
    endpoint_status = raw.get("endpoints", {})
    flags = [f"{k}:{v.get('status')}" for k, v in endpoint_status.items() if isinstance(v, dict) and v.get("status") != "OK"]
    meta = comparison_metadata(endpoint_status, hourly)
    if not meta["comparison_ready"]:
        flags.append("hourly_comparison_not_ready")
    return {
        "provider": "the_weather_company",
        "station": "KMIA",
        "geocode": raw.get("geocode", KMIA_GEOCODE),
        "fetched_at_utc": raw.get("fetched_at_utc", utc_now()),
        "api_units": raw.get("api_units", UNITS),
        "language": raw.get("language", LANGUAGE),
        "endpoint_status": endpoint_status,
        "current_conditions": current,
        "observed_history_file": str(OBSERVED_HISTORY_FILE),
        "daily_forecast": daily,
        "hourly_forecast": hourly,
        "derived_features": derive_features(daily, hourly),
        "comparison_metadata": meta,
        "quality_flags": flags,
        "safety": {"no_real_trading": True},
    }


def save_snapshot(snapshot: Dict[str, Any], raw: Dict[str, Any]) -> Tuple[Path, Path]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    append_observed_history(snapshot)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    timestamp_file = PROCESSED_DIR / f"twc_kmia_snapshot_{stamp}.json"
    raw_file = RAW_DIR / f"twc_kmia_raw_{stamp}.json"
    LATEST_FILE.write_text(json.dumps(snapshot, indent=2))
    timestamp_file.write_text(json.dumps(snapshot, indent=2))
    raw_file.write_text(json.dumps(raw, indent=2))
    return LATEST_FILE, timestamp_file


if __name__ == "__main__":
    client = TWCKMIAClient()
    raw_bundle = client.fetch_raw_bundle()
    normalized = normalize_bundle(raw_bundle)
    save_snapshot(normalized, raw_bundle)
    print(json.dumps(normalized, indent=2))

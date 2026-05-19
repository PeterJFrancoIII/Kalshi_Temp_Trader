"""KMIA weather status orchestrator.

This module assembles a single JSON status document summarizing the
latest KMIA weather state: live observations (JSON API with HTML
fallback), forecast high, history record count, and freshness gates.
Operations scripts invoke it to refresh
``backend/data/processed/weather_ingestion/latest_weather_ingestion_status.json``
before each daily prediction run.

The orchestrator depends on the canonical ingestion fetchers /
parsers in this package; previously this class lived under
``weather/nws_kmia_client.py`` and was split across two namespaces. The
``weather.nws_kmia_client`` import path remains as a thin compatibility
shim — see that module's docstring.

NO REAL TRADING EXECUTION.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from ingestion.kmia_live_fetcher import fetch_obhistory, fetch_wrh_timeseries
from ingestion.kmia_obhistory_parser import parse_obhistory, parse_wrh_timeseries
from ingestion.nws_forecast_fetcher import fetch_nws_forecast

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "backend" / "data" / "processed" / "weather_ingestion"
STATUS_FILE = DATA_DIR / "latest_weather_ingestion_status.json"
HISTORY_FILE = ROOT / "backend" / "data" / "processed" / "history" / "kmia_daily_history.jsonl"


class NWSKMIAClient:
    """Orchestrator that produces the daily weather ingestion status document.

    The name is historical (was originally framed as an HTTP client) and
    is preserved for backward compatibility with shell scripts and the
    legacy ``weather.nws_kmia_client`` import path. New code may
    instantiate it via either name; both resolve to this class.
    """

    def __init__(self, station: str = "KMIA"):
        self.station = station
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_live_status(self) -> Dict[str, Any]:
        """Fetch and summarize the latest KMIA weather data."""
        status = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "generated_at_utc": None,
            "observation_time_utc": None,
            "station": self.station,
            "source": "NWS/public",
            "current_temp_f": None,
            "observed_max_so_far_f": None,
            "forecast_high_f": None,
            "latest_observation_time": None,
            "stale_data": True,
            "history_record_count": 0,
            "climatology_active": False,
            "settlement_authority_status": "PRELIMINARY",
            "metar_parse_status": "PENDING",
            "station_status": "OK",
            "kmia1m_status": "UNAVAILABLE",
            "qc_flags": {},
            "warnings": [],
            "safety": {"no_real_trading": True},
        }

        raw_json = fetch_wrh_timeseries(self.station)
        observations = []
        if raw_json:
            observations = parse_wrh_timeseries(raw_json)
            status["metar_parse_status"] = "OK" if observations else "EMPTY"

        if not observations:
            raw_html = fetch_obhistory(self.station)
            if raw_html:
                observations, parse_warns = parse_obhistory(raw_html)
                status["warnings"].extend(parse_warns)
                status["metar_parse_status"] = (
                    "OK_HTML_FALLBACK" if observations else "FAILED"
                )

        if observations:
            latest = observations[-1]
            status["current_temp_f"] = latest.temperature_f
            status["latest_observation_time"] = latest.timestamp.isoformat()

            if latest.timestamp.tzinfo:
                latest_utc = latest.timestamp.astimezone(timezone.utc)
            else:
                latest_utc = latest.timestamp.replace(tzinfo=timezone.utc)

            status["observation_time_utc"] = latest_utc.isoformat()
            status["generated_at_utc"] = latest_utc.isoformat()

            time_diff = datetime.now(timezone.utc) - latest_utc
            status["stale_data"] = time_diff > timedelta(hours=1)

            try:
                from dateutil import tz as _tz

                _ET = _tz.gettz("America/New_York")
                today_et = datetime.now(_ET).date()
                today_obs = []
                for o in observations:
                    if o.temperature_f is None:
                        continue
                    o_et = (
                        o.timestamp.astimezone(_ET)
                        if o.timestamp.tzinfo
                        else o.timestamp.replace(tzinfo=timezone.utc).astimezone(_ET)
                    )
                    if o_et.date() == today_et:
                        today_obs.append(o)
            except Exception:
                today_et = datetime.now().date()
                today_obs = [
                    o
                    for o in observations
                    if o.timestamp.date() == today_et and o.temperature_f is not None
                ]

            if today_obs:
                status["observed_max_so_far_f"] = max(
                    o.temperature_f for o in today_obs
                )
        else:
            status["warnings"].append("No observations found via JSON or HTML.")
            status["metar_parse_status"] = "MISSING"

        forecast_data = fetch_nws_forecast()
        if forecast_data:
            periods = forecast_data.get("properties", {}).get("periods", [])
            if periods:
                today_period = periods[0]
                if today_period.get("isDaytime"):
                    status["forecast_high_f"] = today_period.get("temperature")
                elif len(periods) > 1 and periods[1].get("isDaytime"):
                    status["forecast_high_f"] = periods[1].get("temperature")

        if HISTORY_FILE.exists():
            try:
                count = 0
                with open(HISTORY_FILE, "r") as f:
                    for line in f:
                        if line.strip():
                            count += 1
                status["history_record_count"] = count
                status["climatology_active"] = count > 0
            except Exception as e:
                status["warnings"].append(f"Error reading history: {e}")

        return status

    def save_status(self, status: Dict[str, Any]) -> None:
        """Persist ``status`` to :data:`STATUS_FILE`."""
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f, indent=2)
            logger.info(f"Saved weather ingestion status to {STATUS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save weather status: {e}")


def main() -> None:
    """CLI entry point for the operations shell scripts."""
    logging.basicConfig(level=logging.INFO)
    client = NWSKMIAClient()
    status = client.get_live_status()
    client.save_status(status)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()

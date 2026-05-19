"""Backward-compat shim for the KMIA weather status orchestrator.

The class :class:`NWSKMIAClient` now lives in
:mod:`ingestion.weather_status_writer`. This module re-exports it so
existing callers and tests keep working.

The shim also re-imports the underlying fetcher functions
(:func:`fetch_wrh_timeseries`, :func:`fetch_obhistory`,
:func:`fetch_nws_forecast`) so legacy tests that patch
``weather.nws_kmia_client.fetch_*`` continue to find a binding to patch.
New tests should patch ``ingestion.weather_status_writer.fetch_*``
instead.

Operations callers should now use module-mode invocation::

    PYTHONPATH=backend/src python3 -m ingestion.weather_status_writer

NO REAL TRADING EXECUTION.
"""

from __future__ import annotations

from ingestion.kmia_live_fetcher import fetch_obhistory, fetch_wrh_timeseries
from ingestion.kmia_obhistory_parser import parse_obhistory, parse_wrh_timeseries
from ingestion.nws_forecast_fetcher import fetch_nws_forecast
from ingestion.weather_status_writer import (
    DATA_DIR,
    HISTORY_FILE,
    STATUS_FILE,
    NWSKMIAClient,
    main,
)

__all__ = [
    "DATA_DIR",
    "HISTORY_FILE",
    "NWSKMIAClient",
    "STATUS_FILE",
    "fetch_nws_forecast",
    "fetch_obhistory",
    "fetch_wrh_timeseries",
    "main",
    "parse_obhistory",
    "parse_wrh_timeseries",
]


if __name__ == "__main__":
    main()

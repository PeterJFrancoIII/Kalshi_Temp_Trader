import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# NO REAL TRADING EXECUTION
# DRY-RUN / PAPER EVALUATION ONLY

from shared.artifact_paths import BACKTEST_REPORTS_DIR
from shared.timestamp_utils import (
    extract_embedded_timestamp,
    select_snapshot_as_of,
    EMBEDDED_TIMESTAMP_FIELDS,
)
from paper_trading.signal_generator import generate_paper_signal
from paper_trading.settlement import settle_paper_trades
from paper_trading.paper_ledger import PaperLedger

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SnapshotRegistry — centralized point-in-time artifact catalogue (P1)
# ---------------------------------------------------------------------------

class SnapshotRegistry:
    """
    Centralised catalogue that maps (artifact_type, target_date, as_of_time)
    to a resolved file path.

    Eliminates ad-hoc per-function artifact lookup scattered across the
    coordinator.  A single instance is created per backtest run.  All lookups
    are recorded in an ordered log which is later serialised as the replay
    input manifest.

    Artifact types
    --------------
    - "forecast"        : blended probability-distribution JSON
    - "market_snapshot" : Kalshi contract snapshot JSON
    - "weather"         : NWS/TWC weather observation/forecast JSON

    Caching
    -------
    Results are cached by (artifact_type, date_str, as_of_iso) so the same
    candidate files are not re-opened multiple times within one simulated day.
    """

    def __init__(self, search_roots: Optional[Dict[str, Path]] = None):
        """
        Args:
            search_roots: Mapping of artifact_type → directory to search.
                Caller-supplied values override the project defaults.
        """
        self._cache: Dict[str, Optional[Path]] = {}
        self._log: List[Dict[str, Any]] = []

        project_root = Path(__file__).resolve().parents[3]
        processed = project_root / "backend" / "data" / "processed"

        self._roots: Dict[str, Path] = {
            "forecast": processed / "forecast_distributions",
            "market_snapshot": processed / "kalshi_market_snapshots",
            "weather": processed / "weather_snapshots",
        }
        if search_roots:
            self._roots.update(search_roots)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        artifact_type: str,
        target_date: datetime,
        as_of_time: datetime,
        glob_pattern: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Resolves the most-recent artifact of *artifact_type* for *target_date*
        whose embedded timestamp is <= *as_of_time*.

        Returns the resolved Path, or None if no eligible artifact exists.
        """
        date_str = target_date.strftime("%Y-%m-%d")
        cache_key = f"{artifact_type}::{date_str}::{as_of_time.isoformat()}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        directory = self._roots.get(artifact_type)
        if directory is None:
            logger.warning(f"SnapshotRegistry: unknown artifact_type '{artifact_type}'")
            self._record(artifact_type, date_str, as_of_time, None, "unknown_type")
            self._cache[cache_key] = None
            return None

        # Fallback for tests running from the project root
        if not directory.exists():
            alt = Path("backend/data/processed") / directory.name
            if alt.exists():
                directory = alt
            else:
                logger.warning(
                    f"SnapshotRegistry: directory {directory} does not exist."
                )
                self._record(artifact_type, date_str, as_of_time, None, "dir_not_found")
                self._cache[cache_key] = None
                return None

        if glob_pattern is None:
            glob_pattern = self._default_glob(artifact_type, date_str)

        path = select_snapshot_as_of(
            directory=directory,
            glob_pattern=glob_pattern,
            as_of_time=as_of_time,
        )

        reason = "resolved" if path else "not_found"
        self._record(artifact_type, date_str, as_of_time, path, reason)
        self._cache[cache_key] = path
        return path

    def lookup_log(self) -> List[Dict[str, Any]]:
        """Returns all recorded lookup events (used to build the replay manifest)."""
        return list(self._log)

    def clear_cache(self):
        """Resets the in-memory cache (useful between isolated test runs)."""
        self._cache.clear()
        self._log.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _default_glob(self, artifact_type: str, date_str: str) -> str:
        if artifact_type == "forecast":
            return f"*{date_str}*.json"
        if artifact_type == "market_snapshot":
            return "kalshi_market_snapshot_*.json"
        if artifact_type == "weather":
            return f"*{date_str}*.json"
        return "*.json"

    def _record(
        self,
        artifact_type: str,
        date_str: str,
        as_of_time: datetime,
        path: Optional[Path],
        reason: str,
    ) -> None:
        self._log.append({
            "artifact_type": artifact_type,
            "target_date": date_str,
            "as_of_time": as_of_time.isoformat(),
            "resolved_path": str(path) if path else None,
            "reason": reason,
        })


# ---------------------------------------------------------------------------
# BacktestCoordinator
# ---------------------------------------------------------------------------

class BacktestCoordinator:
    """
    Coordinates a backtest replay loop over a date range.

    Point-in-time safety contract:
    - Forecast distributions are selected using embedded timestamps <= forecast_as_of_time.
    - Kalshi market snapshots are selected using embedded timestamps <= market_snapshot_as_of_time.
    - Weather/NWS snapshots are selected using embedded timestamps <= weather_observation_as_of_time.
    - Settlement data is only queried when settlement_as_of_time is past the configured
      settlement_availability_offset (default: next calendar day 06:00 UTC).

    All as_of times are expressed in UTC.
    """

    DEFAULT_FORECAST_HOUR_UTC = 13       # 13:00 UTC ≈ 09:00 ET — pre-market forecast cutoff
    DEFAULT_MARKET_SNAPSHOT_HOUR_UTC = 14  # 14:00 UTC ≈ 10:00 ET — market open
    DEFAULT_WEATHER_OBS_HOUR_UTC = 14    # Same as market snapshot
    DEFAULT_SETTLEMENT_NEXT_DAY_HOUR_UTC = 6  # Next day 06:00 UTC — NWS official high published

    def __init__(
        self,
        start_date: str,
        end_date: str,
        fetcher_mode: str = "local",
        forecast_as_of_hour_utc: int = DEFAULT_FORECAST_HOUR_UTC,
        market_snapshot_as_of_hour_utc: int = DEFAULT_MARKET_SNAPSHOT_HOUR_UTC,
        weather_observation_as_of_hour_utc: int = DEFAULT_WEATHER_OBS_HOUR_UTC,
        settlement_next_day_hour_utc: int = DEFAULT_SETTLEMENT_NEXT_DAY_HOUR_UTC,
    ):
        """
        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD  (inclusive)
            fetcher_mode: "local" for local-file replay (no live API calls)
            forecast_as_of_hour_utc: Hour of day UTC to use as forecast cutoff
                (default 13 = 09:00 ET).  Forecasts with embedded_ts > this are
                excluded from the simulated day.
            market_snapshot_as_of_hour_utc: Hour of day UTC for market snapshot cutoff.
            weather_observation_as_of_hour_utc: Hour of day UTC for weather obs cutoff.
            settlement_next_day_hour_utc: Hour on the NEXT calendar day when official
                settlement data is considered available.
        """
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        self.fetcher_mode = fetcher_mode

        # as_of offsets (hours within simulated day, UTC)
        self.forecast_as_of_hour_utc = forecast_as_of_hour_utc
        self.market_snapshot_as_of_hour_utc = market_snapshot_as_of_hour_utc
        self.weather_observation_as_of_hour_utc = weather_observation_as_of_hour_utc
        self.settlement_next_day_hour_utc = settlement_next_day_hour_utc

        # Output directory
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.run_dir = BACKTEST_REPORTS_DIR / run_id
        self.ledger_path = self.run_dir / "paper_trade_ledger.jsonl"
        self.settlements_path = self.run_dir / "settlements.jsonl"
        self.performance_path = self.run_dir / "performance_summary.json"
        self.signals_dir = self.run_dir / "signals"
        self.manifest_path = self.run_dir / "replay_manifest.json"

        # Resolve data root relative to this file (works regardless of CWD)
        _project_root = Path(__file__).resolve().parents[3]
        _processed = _project_root / "backend" / "data" / "processed"

        # Centralised point-in-time artifact registry (P1)
        self._registry = SnapshotRegistry(
            search_roots={
                "forecast": _processed / "forecast_distributions",
                "market_snapshot": _processed / "kalshi_market_snapshots",
                "weather": _processed / "weather_snapshots",
            }
        )

    # ------------------------------------------------------------------
    # as_of timestamp builders
    # ------------------------------------------------------------------

    def _forecast_as_of_time(self, sim_date: datetime) -> datetime:
        """Returns the forecast cutoff datetime for sim_date."""
        return sim_date.replace(
            hour=self.forecast_as_of_hour_utc,
            minute=0,
            second=0,
            microsecond=0,
        )

    def _market_snapshot_as_of_time(self, sim_date: datetime) -> datetime:
        return sim_date.replace(
            hour=self.market_snapshot_as_of_hour_utc,
            minute=0,
            second=0,
            microsecond=0,
        )

    def _weather_observation_as_of_time(self, sim_date: datetime) -> datetime:
        return sim_date.replace(
            hour=self.weather_observation_as_of_hour_utc,
            minute=0,
            second=0,
            microsecond=0,
        )

    def _settlement_as_of_time(self, sim_date: datetime) -> datetime:
        """Settlement data is available at settlement_next_day_hour_utc on sim_date+1."""
        next_day = sim_date + timedelta(days=1)
        return next_day.replace(
            hour=self.settlement_next_day_hour_utc,
            minute=0,
            second=0,
            microsecond=0,
        )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run_backtest(self):
        """Runs the backtest loop from start_date to end_date (inclusive)."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.signals_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Starting backtest from {self.start_date.date()} to {self.end_date.date()}"
        )
        logger.info(f"Backtest outputs will be saved to {self.run_dir}")

        current_date = self.start_date
        while current_date <= self.end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            logger.info(f"--- Simulating date: {date_str} ---")
            self._simulate_day(current_date)
            current_date += timedelta(days=1)

        logger.info("Backtest loop complete. Running final settlement check...")
        self._run_final_settlement()
        self._write_replay_manifest()
        logger.info(f"Backtest finished. Results in {self.run_dir}")

    # ------------------------------------------------------------------
    # Single-day simulation
    # ------------------------------------------------------------------

    def _simulate_day(self, sim_date: datetime):
        """Simulates the full pipeline for one calendar day."""

        forecast_as_of = self._forecast_as_of_time(sim_date)
        market_as_of = self._market_snapshot_as_of_time(sim_date)
        weather_as_of = self._weather_observation_as_of_time(sim_date)
        settlement_as_of = self._settlement_as_of_time(sim_date)

        # Resolve artifacts through the registry (logged for the replay manifest)
        forecast_path = self._registry.resolve("forecast", sim_date, forecast_as_of)
        snapshot_path = self._registry.resolve("market_snapshot", sim_date, market_as_of)
        # Weather obs wired through registry for future integration
        self._registry.resolve("weather", sim_date, weather_as_of)

        if not forecast_path or not snapshot_path:
            logger.warning(
                f"Skipping {sim_date.date()}: missing forecast_path={forecast_path} "
                f"or snapshot_path={snapshot_path}."
            )
            return

        latest_signal_path = (
            self.signals_dir / f"latest_signal_{sim_date.strftime('%Y%m%d')}.json"
        )

        try:
            report_path = generate_paper_signal(
                forecast_path=forecast_path,
                snapshot_path=snapshot_path,
                prediction_timestamp=forecast_as_of,  # P0 fix: use pre-market cutoff, not 23:59:59
                output_dir=self.signals_dir,
                latest_path_override=latest_signal_path,
                ledger_path_override=self.ledger_path,
            )

            with open(report_path, "r") as f:
                report = json.load(f)

            best_signal = report.get("best_signal")
            if best_signal and best_signal.get("paper_action") == "PAPER BUY CANDIDATE":
                ledger = PaperLedger(ledger_path=self.ledger_path)
                ledger.record_trade(
                    market_ticker=best_signal["market_ticker"],
                    target_date=sim_date.strftime("%Y-%m-%d"),
                    execution_price=best_signal["market_probability"],
                    quantity=10,
                    model_probability=best_signal.get("model_probability"),
                    # F3: store the actual bin label string (e.g. ">=87", "<=84", "91-92")
                    # so settlement.py can correctly determine WON/LOST via
                    # _temp_satisfies_bin_label().  Do NOT store condition_type here
                    # ("above"/"below") — settlement cannot match that against actual temp.
                    forecast_bin=best_signal.get("forecast_bin_label"),
                )
                logger.info(
                    f"Recorded trade for {best_signal['market_ticker']} "
                    f"at {best_signal['market_probability']}"
                )

        except Exception as e:
            logger.error(f"Error generating signal for {sim_date.date()}: {e}")

        # Settle any trades that are eligible at settlement_as_of
        settle_paper_trades(
            ledger_path=self.ledger_path,
            settlements_path=self.settlements_path,
            performance_path=self.performance_path,
            settlement_as_of_time=settlement_as_of,
        )

    # ------------------------------------------------------------------
    # Replay manifest
    # ------------------------------------------------------------------

    def _write_replay_manifest(self) -> None:
        """
        Writes a JSON audit trail listing every artifact resolved by the
        SnapshotRegistry during this backtest run.

        The manifest enables exact replay reproduction: given the same
        manifest, any future run can verify that the same files were (or
        were not) available at each simulated point-in-time cutoff.

        Schema
        ------
        {
            "run_id": str,
            "start_date": str,
            "end_date": str,
            "as_of_config": { ... },
            "generated_at_utc": str,
            "lookups": [
                {
                    "artifact_type": str,
                    "target_date": str,
                    "as_of_time": str,
                    "resolved_path": str | null,
                    "reason": "resolved" | "not_found" | "dir_not_found" | ...
                },
                ...
            ]
        }
        """
        manifest = {
            "run_id": self.run_dir.name,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "as_of_config": {
                "forecast_as_of_hour_utc": self.forecast_as_of_hour_utc,
                "market_snapshot_as_of_hour_utc": self.market_snapshot_as_of_hour_utc,
                "weather_observation_as_of_hour_utc": self.weather_observation_as_of_hour_utc,
                "settlement_next_day_hour_utc": self.settlement_next_day_hour_utc,
            },
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "safety": {
                "no_real_trading": True,
                "disclaimer": "NO REAL TRADING EXECUTION - PAPER ONLY",
            },
            "lookups": self._registry.lookup_log(),
        }
        with open(self.manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Replay manifest written to {self.manifest_path}")

    # ------------------------------------------------------------------
    # Final settlement
    # ------------------------------------------------------------------

    def _run_final_settlement(self):
        """Runs a final settlement pass over all remaining open trades."""
        # Use a far-future settlement_as_of to close everything that has actual data
        far_future = datetime.now(timezone.utc) + timedelta(days=365 * 10)
        settle_paper_trades(
            ledger_path=self.ledger_path,
            settlements_path=self.settlements_path,
            performance_path=self.performance_path,
            settlement_as_of_time=far_future,
        )

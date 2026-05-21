"""
Tests for KMIA Kalshi market open-window classification and paper-signal integration.

NO REAL TRADING EXECUTION — DRY-RUN / PAPER EVALUATION ONLY
"""

import json
import os
import shutil
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from shared.kalshi_market_window import (
    MARKET_STATUS_CLOSED,
    MARKET_STATUS_OPEN,
    MARKET_STATUS_PRE_OPEN,
    MARKET_STATUS_MISSING_FORECAST,
    assess_kalshi_snapshot_freshness,
    classify_market_window,
    market_open_window_et,
    resolve_event_market_status,
)


class TestKalshiMarketWindow(unittest.TestCase):
    def test_market_date_open_window_boundaries(self):
        """D=2026-05-21 opens 2026-05-20 10:00 ET, closes 2026-05-22 00:59 ET."""
        w = market_open_window_et("2026-05-21")
        self.assertTrue(w["open_start_et"].startswith("2026-05-20T10:00:00"))
        self.assertTrue(w["open_end_et"].startswith("2026-05-22T00:59:00"))

    def test_pre_open_before_prior_day_10am_et(self):
        """PRE_OPEN before D-1 10:00 America/New_York."""
        # 2026-05-20 09:30 ET = 13:30 UTC (EDT)
        now = datetime(2026, 5, 20, 13, 30, 0, tzinfo=timezone.utc)
        info = classify_market_window("2026-05-21", now)
        self.assertEqual(info["market_status"], MARKET_STATUS_PRE_OPEN)

    def test_open_during_trading_window(self):
        """OPEN between open_start and open_end inclusive."""
        # 2026-05-21 15:00 ET = 19:00 UTC (EDT)
        now = datetime(2026, 5, 21, 19, 0, 0, tzinfo=timezone.utc)
        info = classify_market_window("2026-05-21", now)
        self.assertEqual(info["market_status"], MARKET_STATUS_OPEN)

    def test_closed_after_d_plus_one_0100_et(self):
        """CLOSED at/after 01:00 ET on D+1 (after 00:59 close)."""
        # 2026-05-22 01:30 ET = 05:30 UTC (EDT)
        now = datetime(2026, 5, 22, 5, 30, 0, tzinfo=timezone.utc)
        info = classify_market_window("2026-05-21", now)
        self.assertEqual(info["market_status"], MARKET_STATUS_CLOSED)

    def test_snapshot_staleness_uses_embedded_timestamp_not_mtime(self):
        """Staleness from embedded fetched_at_utc; mtime must not matter."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "snap.json"
            # Embedded ts is fresh
            _write = {
                "fetched_at_utc": "2026-05-20T20:00:00+00:00",
                "markets": [],
            }
            with open(p, "w") as f:
                json.dump(_write, f)
            # Make mtime look very old (would fail if mtime were used with fresh embedded)
            old = datetime(2020, 1, 1).timestamp()
            os.utime(p, (old, old))

            now = datetime(2026, 5, 20, 20, 30, 0, tzinfo=timezone.utc)
            fresh = assess_kalshi_snapshot_freshness(p, now_utc=now, max_age_minutes=60)
            self.assertFalse(fresh["is_stale"])
            self.assertAlmostEqual(fresh["snapshot_age_minutes"], 30.0, places=0)

    def test_resolve_missing_forecast_status(self):
        status = resolve_event_market_status(
            window_status=MARKET_STATUS_OPEN,
            snapshot_stale=False,
            has_contracts=True,
            has_forecast_distribution=False,
        )
        self.assertEqual(status, MARKET_STATUS_MISSING_FORECAST)


class TestOpenContractSignalIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(__file__).resolve().parent / "temp_open_contract_test"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _run_signal(
        self,
        reports_dir: Path,
        snapshot: dict,
        now_utc: datetime,
        nws: dict,
    ) -> dict:
        snapshot_path = self.temp_dir / "snapshot.json"
        with open(snapshot_path, "w") as f:
            json.dump(snapshot, f)

        nws_path = self.temp_dir / "nws.json"
        with open(nws_path, "w") as f:
            json.dump(nws, f)

        with patch("paper_trading.signal_generator.REPORTS_DIR", reports_dir), \
             patch("paper_trading.signal_generator.SNAPSHOT_FILE", snapshot_path), \
             patch("paper_trading.signal_generator.OUTPUT_DIR", self.temp_dir), \
             patch("paper_trading.signal_generator.LATEST_KALSHI_ORDERBOOKS", str(self.temp_dir / "no_ob.json")), \
             patch("paper_trading.signal_generator.NWS_SNAPSHOT_FILE", nws_path), \
             patch("weather.nws_snapshot_contract.assess_nws_snapshot") as mock_nws:
            mock_nws.return_value = {
                "available": True,
                "allow_paper_recommendations": True,
                "status": "OK",
                "no_trade_reason": None,
                "warnings": [],
            }
            from paper_trading.signal_generator import generate_paper_signal
            out = self.temp_dir / "latest_signal.json"
            generate_paper_signal(
                prediction_timestamp=now_utc,
                latest_path_override=str(out),
            )
            with open(out) as f:
                return json.load(f)

    def test_all_open_market_dates_in_events_by_date(self):
        """OPEN and PRE_OPEN dates from snapshot appear in events_by_date."""
        reports = self.temp_dir / "reports"
        reports.mkdir()
        for d, prob in (("2026-05-20", 0.5), ("2026-05-21", 0.3)):
            with open(reports / f"kmia_forecast_{d}_rules_v2_climatology_000000.json", "w") as f:
                json.dump({
                    "date": d,
                    "generated_at_utc": f"{d}T12:00:00+00:00",
                    "integer_distribution": {"85": prob, "86": 0.2},
                }, f)

        snapshot = {
            "fetched_at_utc": datetime(2026, 5, 20, 18, 0, 0, tzinfo=timezone.utc).isoformat(),
            "markets": [
                {
                    "ticker": "KXHIGHMIA-26MAY20-B85.5",
                    "event_ticker": "KXHIGHMIA-26MAY20",
                    "title": "85-86 May 20",
                    "yes_ask_dollars": 0.10,
                    "status": "active",
                },
                {
                    "ticker": "KXHIGHMIA-26MAY21-B90.5",
                    "event_ticker": "KXHIGHMIA-26MAY21",
                    "title": "90-91 May 21",
                    "yes_ask_dollars": 0.15,
                    "status": "active",
                },
            ],
        }
        # 2026-05-20 18:00 UTC = 14:00 ET — May 20 OPEN, May 21 PRE_OPEN or OPEN
        now = datetime(2026, 5, 20, 18, 0, 0, tzinfo=timezone.utc)
        report = self._run_signal(reports, snapshot, now, {"latest_observation_time": now.isoformat()})

        self.assertIn("2026-05-20", report["events_by_date"])
        self.assertIn("2026-05-21", report["events_by_date"])
        self.assertIn("2026-05-20", report.get("open_market_dates", []))
        self.assertIn("2026-05-21", report.get("open_market_dates", []))

        ev20 = report["events_by_date"]["2026-05-20"]
        self.assertIn(ev20["market_status"], (MARKET_STATUS_OPEN, MARKET_STATUS_PRE_OPEN))
        self.assertTrue(ev20.get("open_start_et"))
        self.assertTrue(ev20.get("contracts"))

    def test_missing_forecast_open_date_still_visible(self):
        """OPEN date without forecast stays in events_by_date with warning."""
        reports = self.temp_dir / "reports_missing"
        reports.mkdir()
        with open(reports / "kmia_forecast_2026-05-20_rules_v2_climatology_000000.json", "w") as f:
            json.dump({
                "date": "2026-05-20",
                "integer_distribution": {"88": 0.5},
            }, f)

        snapshot = {
            "fetched_at_utc": "2026-05-20T18:00:00+00:00",
            "markets": [
                {"ticker": "KXHIGHMIA-26MAY20-B88.5", "event_ticker": "KXHIGHMIA-26MAY20", "yes_ask_dollars": 0.2, "status": "open"},
                {"ticker": "KXHIGHMIA-26MAY21-B90.5", "event_ticker": "KXHIGHMIA-26MAY21", "yes_ask_dollars": 0.2, "status": "open"},
            ],
        }
        now = datetime(2026, 5, 20, 18, 0, 0, tzinfo=timezone.utc)
        report = self._run_signal(reports, snapshot, now, {"latest_observation_time": now.isoformat()})

        ev21 = report["events_by_date"]["2026-05-21"]
        self.assertTrue(
            any("Forecast distribution missing for 2026-05-21" in w for w in ev21.get("warnings", []))
        )
        self.assertGreater(len(ev21.get("signals", [])), 0)
        self.assertEqual(ev21.get("dynamic_contract_probabilities"), {})

    def test_closed_market_not_used_for_money_allocation_primary(self):
        """CLOSED calendar-day market excluded from money_distribution rows when primary is OPEN."""
        reports = self.temp_dir / "reports_closed"
        reports.mkdir()
        with open(reports / "kmia_forecast_2026-05-18_rules_v2_climatology_000000.json", "w") as f:
            json.dump({"date": "2026-05-18", "integer_distribution": {"80": 1.0}}, f)
        with open(reports / "kmia_forecast_2026-05-20_rules_v2_climatology_000000.json", "w") as f:
            json.dump({"date": "2026-05-20", "integer_distribution": {"88": 0.5}}, f)

        snapshot = {
            "fetched_at_utc": "2026-05-20T18:00:00+00:00",
            "markets": [
                {"ticker": "KXHIGHMIA-26MAY18-B80.5", "event_ticker": "KXHIGHMIA-26MAY18", "yes_ask_dollars": 0.1, "status": "open"},
                {"ticker": "KXHIGHMIA-26MAY20-B88.5", "event_ticker": "KXHIGHMIA-26MAY20", "yes_ask_dollars": 0.2, "status": "open"},
            ],
        }
        now = datetime(2026, 5, 20, 18, 0, 0, tzinfo=timezone.utc)
        report = self._run_signal(reports, snapshot, now, {"latest_observation_time": now.isoformat()})

        md = report.get("money_distribution", {})
        tickers = {r["contract_ticker"] for r in md.get("rows", [])}
        self.assertNotIn("KXHIGHMIA-26MAY18-B80.5", tickers)
        self.assertEqual(report["events_by_date"]["2026-05-18"]["market_status"], MARKET_STATUS_CLOSED)

    def test_safety_flags_on_report(self):
        reports = self.temp_dir / "reports_safety"
        reports.mkdir()
        with open(reports / "kmia_forecast_2026-05-20_rules_v2_climatology_000000.json", "w") as f:
            json.dump({"date": "2026-05-20", "integer_distribution": {"88": 0.5}}, f)

        snapshot = {
            "fetched_at_utc": "2026-05-20T18:00:00+00:00",
            "markets": [
                {"ticker": "KXHIGHMIA-26MAY20-B88.5", "event_ticker": "KXHIGHMIA-26MAY20", "yes_ask_dollars": 0.2, "status": "open"},
            ],
        }
        now = datetime(2026, 5, 20, 18, 0, 0, tzinfo=timezone.utc)
        report = self._run_signal(reports, snapshot, now, {"latest_observation_time": now.isoformat()})
        self.assertTrue(report["safety"]["no_real_trading"])
        self.assertTrue(report["safety"]["no_order_execution"])


if __name__ == "__main__":
    unittest.main()

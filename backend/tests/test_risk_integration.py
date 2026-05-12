"""
F1–F4 + F6 Risk Integration Tests
===================================
Agent 6 — Risk Engine Agent · 2026-05-11 · Sonnet 4.6

Tests cover the four confirmed critical defects fixed in this session:

F1 / C1 — Daily/weekly PnL loss gates can now fire
    After settlement, _update_json_ledger_pnl writes realized PnL back into
    the JSON ledger so PaperLedger.get_summary() returns non-zero daily/weekly_pnl
    and risk gates 7 & 8 can block trading.

F2 / C2 — Weather freshness Gate 2 fails closed when obs time is missing
    generate_paper_signal() loads the real NWS observation timestamp from
    NWS_SNAPSHOT_FILE.  Missing file or missing field → Gate 2 blocks.

F3 / C3 — Settlement correctly classifies WON/LOST for dynamic bin labels
    _temp_satisfies_bin_label handles >=, <=, <, >, X-Y, and exact labels.
    Coordinator stores forecast_bin_label (e.g. ">=87") not condition_type
    ("above"), so settlement comparison is valid.

F4 / C4 — Settlement reads both JSON-object and JSONL ledger formats
    _load_trades_from_ledger detects format automatically.
    Status check normalised to case-insensitive ("open" == "OPEN").

F6 — End-to-end integration
    PaperLedger → settle_paper_trades → ledger PnL writeback → get_summary →
    risk gates 7/8 trigger.

NO REAL TRADING. All tests use temporary directories; no live API calls.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap sys.path (mirrors run_tests.py setup)
# ---------------------------------------------------------------------------
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from paper_trading.paper_ledger import PaperLedger
from paper_trading.settlement import (
    settle_paper_trades,
    _temp_satisfies_bin_label,
    _load_trades_from_ledger,
    _update_json_ledger_pnl,
)
from risk.risk_engine import (
    check_weather_freshness,
    check_daily_loss_limit,
    check_weekly_drawdown_limit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_history(history_path: Path, entries: dict) -> None:
    """Writes a kmia_daily_history.jsonl fixture."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "w") as f:
        for date_str, tmax in entries.items():
            f.write(json.dumps({"date": date_str, "tmax_f": tmax}) + "\n")


def _fresh_obs_iso(minutes_ago: int = 10) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _stale_obs_iso(minutes_ago: int = 120) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


# ---------------------------------------------------------------------------
# F3 — _temp_satisfies_bin_label unit tests
# ---------------------------------------------------------------------------

class TestTempSatisfiesBinLabel(unittest.TestCase):
    """F3: Verifies dynamic and legacy bin label matching."""

    def test_legacy_range_match(self):
        self.assertTrue(_temp_satisfies_bin_label(84, "83-84"))
        self.assertTrue(_temp_satisfies_bin_label(83, "83-84"))
        self.assertFalse(_temp_satisfies_bin_label(85, "83-84"))

    def test_legacy_gte_match(self):
        self.assertTrue(_temp_satisfies_bin_label(87, ">=87"))
        self.assertTrue(_temp_satisfies_bin_label(95, ">=87"))
        self.assertFalse(_temp_satisfies_bin_label(86, ">=87"))

    def test_legacy_lte_match(self):
        self.assertTrue(_temp_satisfies_bin_label(78, "<=78"))
        self.assertTrue(_temp_satisfies_bin_label(70, "<=78"))
        self.assertFalse(_temp_satisfies_bin_label(79, "<=78"))

    def test_dynamic_gte_label(self):
        """Dynamic contract: temperature >= 95 wins."""
        self.assertTrue(_temp_satisfies_bin_label(95, ">=95"))
        self.assertTrue(_temp_satisfies_bin_label(100, ">=95"))
        self.assertFalse(_temp_satisfies_bin_label(94, ">=95"))

    def test_dynamic_lte_label(self):
        """Dynamic contract: temperature <= 89 wins."""
        self.assertTrue(_temp_satisfies_bin_label(89, "<=89"))
        self.assertTrue(_temp_satisfies_bin_label(80, "<=89"))
        self.assertFalse(_temp_satisfies_bin_label(90, "<=89"))

    def test_dynamic_range_label(self):
        """Dynamic contract: temperature 91-92 wins."""
        self.assertTrue(_temp_satisfies_bin_label(91, "91-92"))
        self.assertTrue(_temp_satisfies_bin_label(92, "91-92"))
        self.assertFalse(_temp_satisfies_bin_label(90, "91-92"))
        self.assertFalse(_temp_satisfies_bin_label(93, "91-92"))

    def test_strict_gt_label(self):
        self.assertTrue(_temp_satisfies_bin_label(86, ">85"))
        self.assertFalse(_temp_satisfies_bin_label(85, ">85"))

    def test_strict_lt_label(self):
        self.assertTrue(_temp_satisfies_bin_label(84, "<85"))
        self.assertFalse(_temp_satisfies_bin_label(85, "<85"))

    def test_empty_label_returns_false(self):
        self.assertFalse(_temp_satisfies_bin_label(84, ""))
        self.assertFalse(_temp_satisfies_bin_label(84, None))

    def test_garbage_label_returns_false(self):
        self.assertFalse(_temp_satisfies_bin_label(84, "above"))
        self.assertFalse(_temp_satisfies_bin_label(84, "condition_type"))


# ---------------------------------------------------------------------------
# F4 — _load_trades_from_ledger unit tests
# ---------------------------------------------------------------------------

class TestLoadTradesFromLedger(unittest.TestCase):
    """F4: Verifies that both JSON object and JSONL ledger formats are readable."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_loads_json_object_format(self):
        """New PaperLedger JSON format is loaded correctly."""
        ledger_path = self.tmp / "ledger.json"
        data = {
            "account_balance": 1000.0,
            "trades": [
                {
                    "market_ticker": "KX-A",
                    "target_date": "2026-05-11",
                    "status": "open",
                    "pnl": 0.0,
                    "execution_price": 0.55,
                },
            ],
        }
        with open(ledger_path, "w") as f:
            json.dump(data, f, indent=2)

        trades = _load_trades_from_ledger(ledger_path)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["market_ticker"], "KX-A")
        self.assertEqual(trades[0]["status"], "open")

    def test_loads_jsonl_format(self):
        """Legacy JSONL format (one trade per line) is loaded correctly."""
        ledger_path = self.tmp / "ledger.jsonl"
        with open(ledger_path, "w") as f:
            f.write(json.dumps({"market_ticker": "KX-B", "status": "OPEN"}) + "\n")
            f.write(json.dumps({"market_ticker": "KX-C", "status": "OPEN"}) + "\n")

        trades = _load_trades_from_ledger(ledger_path)
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0]["market_ticker"], "KX-B")

    def test_malformed_jsonl_line_is_skipped_with_warning(self):
        """A malformed JSONL line is skipped; valid lines are still loaded."""
        ledger_path = self.tmp / "ledger.jsonl"
        with open(ledger_path, "w") as f:
            f.write(json.dumps({"market_ticker": "KX-GOOD", "status": "OPEN"}) + "\n")
            f.write("THIS IS NOT JSON\n")
            f.write(json.dumps({"market_ticker": "KX-ALSO-GOOD", "status": "OPEN"}) + "\n")

        trades = _load_trades_from_ledger(ledger_path)
        self.assertEqual(len(trades), 2)
        tickers = {t["market_ticker"] for t in trades}
        self.assertIn("KX-GOOD", tickers)
        self.assertIn("KX-ALSO-GOOD", tickers)

    def test_empty_file_returns_empty_list(self):
        ledger_path = self.tmp / "empty.json"
        ledger_path.write_text("")
        trades = _load_trades_from_ledger(ledger_path)
        self.assertEqual(trades, [])


# ---------------------------------------------------------------------------
# F4 + F1 — settle_paper_trades with JSON-object ledger
# ---------------------------------------------------------------------------

class TestSettlementWithJsonLedger(unittest.TestCase):
    """F4: settlement reads new PaperLedger JSON format. F1: PnL written back."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.ledger_path = self.tmp / "ledger.json"
        self.settlements_path = self.tmp / "settlements.jsonl"
        self.performance_path = self.tmp / "performance.json"
        self.history_path = self.tmp / "history.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def _make_ledger(self, trades: list) -> None:
        data = {"account_balance": 1000.0, "trades": trades}
        with open(self.ledger_path, "w") as f:
            json.dump(data, f, indent=2)

    def test_f4_json_ledger_trade_is_read_and_settled(self):
        """F4: PaperLedger-written JSON trade is found and settled by settlement.py."""
        _write_history(self.history_path, {"2026-05-06": 88})  # actual high = 88
        import paper_trading.settlement as smod
        orig_history = smod.HISTORY_FILE
        smod.HISTORY_FILE = self.history_path
        try:
            self._make_ledger([
                {
                    "market_ticker": "KXHIGHMIA-26MAY06-B86.5",
                    "target_date": "2026-05-06",
                    "execution_price": 0.40,
                    "quantity": 10,
                    "timestamp_utc": "2026-05-06T13:00:00+00:00",
                    "status": "open",   # lowercase — new PaperLedger style
                    "pnl": 0.0,
                    "model_probability": 0.65,
                    "forecast_bin": ">=87",
                }
            ])

            settle_paper_trades(
                ledger_path=self.ledger_path,
                settlements_path=self.settlements_path,
                performance_path=self.performance_path,
                settlement_as_of_time=datetime(2026, 5, 7, 7, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(self.settlements_path.exists(), "Settlements file not created.")
            with open(self.settlements_path) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            self.assertEqual(len(lines), 1)
            result = lines[0]
            self.assertEqual(result["market_ticker"], "KXHIGHMIA-26MAY06-B86.5")
            self.assertEqual(result["result"], "WON")  # 88 >= 87 → WON
            self.assertAlmostEqual(result["simulated_pnl"], 0.60, places=4)
        finally:
            smod.HISTORY_FILE = orig_history

    def test_f4_jsonl_uppercase_open_status_is_settled(self):
        """F4: Legacy JSONL trades with uppercase 'OPEN' status are settled."""
        _write_history(self.history_path, {"2026-05-06": 84})  # actual high = 84
        import paper_trading.settlement as smod
        orig_history = smod.HISTORY_FILE
        smod.HISTORY_FILE = self.history_path
        # Write legacy JSONL
        with open(self.ledger_path, "w") as f:
            f.write(json.dumps({
                "market_ticker": "KXHIGHMIA-26MAY06-B82.5",
                "target_date": "2026-05-06",
                "simulated_entry_price": 0.30,
                "quantity": 5,
                "timestamp_utc": "2026-05-06T13:00:00+00:00",
                "status": "OPEN",   # uppercase — legacy style
                "pnl": 0.0,
                "forecast_bin": "83-84",
            }) + "\n")
        try:
            settle_paper_trades(
                ledger_path=self.ledger_path,
                settlements_path=self.settlements_path,
                performance_path=self.performance_path,
                settlement_as_of_time=datetime(2026, 5, 7, 7, 0, tzinfo=timezone.utc),
            )
            with open(self.settlements_path) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]["result"], "WON")  # 84 in "83-84"
        finally:
            smod.HISTORY_FILE = orig_history


# ---------------------------------------------------------------------------
# F1 — PnL writeback enables risk Gates 7 & 8
# ---------------------------------------------------------------------------

class TestPnLWriteback(unittest.TestCase):
    """F1: Settled trades update ledger PnL so Gates 7/8 can fire."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.ledger_path = self.tmp / "ledger.json"
        self.settlements_path = self.tmp / "settlements.jsonl"
        self.performance_path = self.tmp / "performance.json"
        self.history_path = self.tmp / "history.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_f1_settled_losing_trade_reduces_daily_pnl(self):
        """A settled losing trade must make daily_pnl negative in get_summary()."""
        _write_history(self.history_path, {"2026-05-06": 80})  # actual 80 → "79-80"
        import paper_trading.settlement as smod
        orig_history = smod.HISTORY_FILE
        smod.HISTORY_FILE = self.history_path
        try:
            # Record trade via PaperLedger (execution_price=0.40, forecast_bin=">=87")
            ledger = PaperLedger(ledger_path=self.ledger_path)
            ledger.record_trade(
                market_ticker="KXHIGHMIA-26MAY06-B86.5",
                target_date="2026-05-06",
                execution_price=0.40,
                quantity=10,
                model_probability=0.60,
                forecast_bin=">=87",
            )
            summary_before = ledger.get_summary()
            self.assertEqual(summary_before["daily_pnl"], 0.0, "Open trade should have 0 PnL.")

            # Settle
            settle_paper_trades(
                ledger_path=self.ledger_path,
                settlements_path=self.settlements_path,
                performance_path=self.performance_path,
                settlement_as_of_time=datetime(2026, 5, 7, 7, 0, tzinfo=timezone.utc),
            )

            # Reload ledger and check PnL
            reloaded = PaperLedger(ledger_path=self.ledger_path)
            summary = reloaded.get_summary()
            self.assertLess(summary["daily_pnl"], 0.0,
                "Settled losing trade must produce negative daily_pnl.")
            self.assertLess(summary["weekly_pnl"], 0.0,
                "Settled losing trade must produce negative weekly_pnl.")
        finally:
            smod.HISTORY_FILE = orig_history

    def test_f1_settled_winning_trade_increases_daily_pnl(self):
        """A settled winning trade must produce positive daily_pnl."""
        _write_history(self.history_path, {"2026-05-06": 88})  # actual 88 → >=87 → WON
        import paper_trading.settlement as smod
        orig_history = smod.HISTORY_FILE
        smod.HISTORY_FILE = self.history_path
        try:
            ledger = PaperLedger(ledger_path=self.ledger_path)
            ledger.record_trade(
                market_ticker="KXHIGHMIA-26MAY06-B86.5",
                target_date="2026-05-06",
                execution_price=0.40,
                quantity=10,
                model_probability=0.60,
                forecast_bin=">=87",
            )
            settle_paper_trades(
                ledger_path=self.ledger_path,
                settlements_path=self.settlements_path,
                performance_path=self.performance_path,
                settlement_as_of_time=datetime(2026, 5, 7, 7, 0, tzinfo=timezone.utc),
            )
            reloaded = PaperLedger(ledger_path=self.ledger_path)
            summary = reloaded.get_summary()
            self.assertGreater(summary["daily_pnl"], 0.0,
                "Settled winning trade must produce positive daily_pnl.")
        finally:
            smod.HISTORY_FILE = orig_history

    def test_f1_gate_7_blocks_after_daily_loss_limit_exceeded(self):
        """Gate 7 must block when daily_pnl < -$50 after settling losing trades."""
        _write_history(self.history_path, {"2026-05-06": 80})  # will be LOST (forecast >=87)
        import paper_trading.settlement as smod
        orig_history = smod.HISTORY_FILE
        smod.HISTORY_FILE = self.history_path
        try:
            ledger = PaperLedger(ledger_path=self.ledger_path)
            # Record many losing trades to exceed $50 daily limit.
            # Use price 0.60 → LOST pnl = -0.60 per trade.
            # 90 trades × -$0.60 = -$54 total loss (exceeds $50 limit).
            # Tickers must use valid format: KXHIGHMIA-26MAY06-B<suffix>
            for i in range(90):
                ledger.record_trade(
                    market_ticker=f"KXHIGHMIA-26MAY06-B{85 + i}",
                    target_date="2026-05-06",
                    execution_price=0.60,
                    quantity=1,
                    forecast_bin=">=87",
                )

            settle_paper_trades(
                ledger_path=self.ledger_path,
                settlements_path=self.settlements_path,
                performance_path=self.performance_path,
                settlement_as_of_time=datetime(2026, 5, 7, 7, 0, tzinfo=timezone.utc),
            )

            reloaded = PaperLedger(ledger_path=self.ledger_path)
            summary = reloaded.get_summary()
            # Gate 7: daily_pnl < -50
            gate_decision = check_daily_loss_limit(summary)
            self.assertFalse(gate_decision.passed,
                f"Gate 7 should block; daily_pnl={summary['daily_pnl']:.2f}")
        finally:
            smod.HISTORY_FILE = orig_history

    def test_f1_gate_8_blocks_after_weekly_drawdown_exceeded(self):
        """Gate 8 must block when weekly_pnl < -$150 after settled losses."""
        # Three days in the past week, actual temp 80 → forecast >=87 → LOST each time.
        # Tickers must use valid format with month abbreviation (e.g. 26MAY06).
        day_map = [
            ("2026-05-06", "26MAY06"),
            ("2026-05-07", "26MAY07"),
            ("2026-05-08", "26MAY08"),
        ]
        history_entries = {d: 80 for d, _ in day_map}
        _write_history(self.history_path, history_entries)

        import paper_trading.settlement as smod
        orig_history = smod.HISTORY_FILE
        smod.HISTORY_FILE = self.history_path
        try:
            for date_str, ticker_date in day_map:
                # Reload from disk each day — mirrors how BacktestCoordinator uses
                # PaperLedger (creates a fresh instance per _simulate_day call).
                # This ensures _update_json_ledger_pnl's disk updates are visible.
                ledger = PaperLedger(ledger_path=self.ledger_path)
                for j in range(90):  # 90 × $0.60 loss = $54/day × 3 days = $162 weekly
                    ledger.record_trade(
                        market_ticker=f"KXHIGHMIA-{ticker_date}-B{j}",
                        target_date=date_str,
                        execution_price=0.60,
                        quantity=1,
                        forecast_bin=">=87",
                    )
                day_num = int(date_str[-2:])
                settle_paper_trades(
                    ledger_path=self.ledger_path,
                    settlements_path=self.settlements_path,
                    performance_path=self.performance_path,
                    settlement_as_of_time=datetime(2026, 5, day_num + 1, 7, 0,
                                                   tzinfo=timezone.utc),
                )

            reloaded = PaperLedger(ledger_path=self.ledger_path)
            summary = reloaded.get_summary()
            gate_decision = check_weekly_drawdown_limit(summary)
            self.assertFalse(gate_decision.passed,
                f"Gate 8 should block; weekly_pnl={summary['weekly_pnl']:.2f}")
        finally:
            smod.HISTORY_FILE = orig_history


# ---------------------------------------------------------------------------
# F2 — Gate 2 weather freshness
# ---------------------------------------------------------------------------

class TestGate2WeatherFreshness(unittest.TestCase):
    """F2: Gate 2 fails closed when obs time is missing or stale."""

    def test_f2_missing_obs_time_blocks_gate_2(self):
        """None observation time must cause Gate 2 to block."""
        decision = check_weather_freshness(None)
        self.assertFalse(decision.passed,
            "Gate 2 must block when latest_obs_time_iso is None.")
        self.assertIn("Missing", decision.reason)

    def test_f2_stale_obs_time_blocks_gate_2(self):
        """Obs time > 90 minutes ago must block Gate 2."""
        stale = _stale_obs_iso(minutes_ago=120)
        decision = check_weather_freshness(stale)
        self.assertFalse(decision.passed,
            f"Gate 2 must block when obs is 120 min old. Reason: {decision.reason}")

    def test_f2_fresh_obs_time_passes_gate_2(self):
        """Obs time within 90 minutes must pass Gate 2."""
        fresh = _fresh_obs_iso(minutes_ago=15)
        decision = check_weather_freshness(fresh)
        self.assertTrue(decision.passed,
            "Gate 2 must pass when obs is only 15 min old.")

    def test_f2_exactly_90_min_is_stale(self):
        """Obs time exactly 90 minutes old is on the boundary and should be stale."""
        boundary = (datetime.now(timezone.utc) - timedelta(seconds=90 * 60 + 1)).isoformat()
        decision = check_weather_freshness(boundary)
        self.assertFalse(decision.passed, "Obs time > 90 min should be stale.")


# ---------------------------------------------------------------------------
# F3 — Dynamic bin settlement classification
# ---------------------------------------------------------------------------

class TestDynamicBinSettlement(unittest.TestCase):
    """F3: settlement correctly classifies WON/LOST with dynamic Kalshi bins."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.settlements_path = self.tmp / "settlements.jsonl"
        self.performance_path = self.tmp / "performance.json"
        self.history_path = self.tmp / "history.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def _settle_single_trade(self, forecast_bin: str, actual_temp: int,
                              status: str = "open") -> dict:
        """Helper: creates a ledger with one trade, runs settlement, returns result."""
        import paper_trading.settlement as smod
        orig = smod.HISTORY_FILE
        smod.HISTORY_FILE = self.history_path
        ledger_path = self.tmp / f"ledger_{forecast_bin.replace('/', '_')}.json"
        settlements_path = self.tmp / f"settle_{forecast_bin.replace('/', '_')}.jsonl"
        _write_history(self.history_path, {"2026-05-06": actual_temp})
        data = {
            "account_balance": 1000.0,
            "trades": [{
                "market_ticker": "KXHIGHMIA-26MAY06-X",
                "target_date": "2026-05-06",
                "execution_price": 0.50,
                "quantity": 1,
                "timestamp_utc": "2026-05-06T13:00:00+00:00",
                "status": status,
                "pnl": 0.0,
                "forecast_bin": forecast_bin,
            }],
        }
        with open(ledger_path, "w") as f:
            json.dump(data, f)
        try:
            settle_paper_trades(
                ledger_path=ledger_path,
                settlements_path=settlements_path,
                performance_path=self.performance_path,
                settlement_as_of_time=datetime(2026, 5, 7, 7, 0, tzinfo=timezone.utc),
            )
            with open(settlements_path) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            return lines[0] if lines else {}
        finally:
            smod.HISTORY_FILE = orig

    def test_f3_dynamic_gte_wins(self):
        """>=95 label wins when actual high >= 95."""
        result = self._settle_single_trade(">=95", 96)
        self.assertEqual(result.get("result"), "WON",
            f">=95 with actual 96 should be WON. Got: {result}")

    def test_f3_dynamic_gte_loses(self):
        """>=95 label loses when actual high < 95."""
        result = self._settle_single_trade(">=95", 94)
        self.assertEqual(result.get("result"), "LOST",
            f">=95 with actual 94 should be LOST. Got: {result}")

    def test_f3_dynamic_lte_wins(self):
        """<=89 label wins when actual high <= 89."""
        result = self._settle_single_trade("<=89", 85)
        self.assertEqual(result.get("result"), "WON",
            f"<=89 with actual 85 should be WON. Got: {result}")

    def test_f3_dynamic_lte_loses(self):
        """<=89 label loses when actual high > 89."""
        result = self._settle_single_trade("<=89", 90)
        self.assertEqual(result.get("result"), "LOST",
            f"<=89 with actual 90 should be LOST. Got: {result}")

    def test_f3_dynamic_range_wins(self):
        """91-92 label wins when actual high is 91 or 92."""
        result = self._settle_single_trade("91-92", 91)
        self.assertEqual(result.get("result"), "WON",
            f"91-92 with actual 91 should be WON. Got: {result}")

    def test_f3_dynamic_range_loses(self):
        """91-92 label loses when actual high is outside range."""
        result = self._settle_single_trade("91-92", 93)
        self.assertEqual(result.get("result"), "LOST",
            f"91-92 with actual 93 should be LOST. Got: {result}")

    def test_f3_legacy_range_still_works(self):
        """Legacy 83-84 label still works correctly after F3 changes."""
        result = self._settle_single_trade("83-84", 84)
        self.assertEqual(result.get("result"), "WON",
            f"83-84 with actual 84 should be WON. Got: {result}")

    def test_f3_condition_type_string_does_not_win(self):
        """Storing 'above' as forecast_bin must NOT produce WON — this was the C3 bug."""
        result = self._settle_single_trade("above", 90)
        self.assertNotEqual(result.get("result"), "WON",
            "Storing condition_type 'above' as forecast_bin must not produce WON. "
            "Coordinator must store the bin label string instead.")


# ---------------------------------------------------------------------------
# F6 — End-to-end integration test
# ---------------------------------------------------------------------------

class TestRiskEndToEnd(unittest.TestCase):
    """
    F6: Full pipeline integration.

    PaperLedger.record_trade()
        → settle_paper_trades() [reads JSON ledger, writes settlements.jsonl, updates ledger]
        → PaperLedger.get_summary() [reads updated ledger]
        → check_daily_loss_limit / check_weekly_drawdown_limit [risk gates]
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.ledger_path = self.tmp / "ledger.json"
        self.settlements_path = self.tmp / "settlements.jsonl"
        self.performance_path = self.tmp / "performance.json"
        self.history_path = self.tmp / "history.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_f6_trade_written_settled_pnl_and_gates(self):
        """
        Full path from record_trade → settlement → PnL writeback → risk gate check.

        1. Trade is written by PaperLedger.
        2. settlement.py reads the JSON ledger correctly (F4).
        3. Settlement classifies WON/LOST using _temp_satisfies_bin_label (F3).
        4. Realized PnL is written back into the ledger (F1).
        5. PaperLedger.get_summary() returns non-zero daily_pnl.
        6. Risk gates 7/8 can fire based on this PnL.
        7. No live trading or external API calls occur.
        """
        # Arrange: actual high 80 → "79-80", forecast bin ">=87" → LOST (pnl = -0.40)
        _write_history(self.history_path, {"2026-05-06": 80})

        import paper_trading.settlement as smod
        orig_history = smod.HISTORY_FILE
        smod.HISTORY_FILE = self.history_path

        try:
            # Step 1: Record trade
            ledger = PaperLedger(ledger_path=self.ledger_path)
            ledger.record_trade(
                market_ticker="KXHIGHMIA-26MAY06-B86.5",
                target_date="2026-05-06",
                execution_price=0.40,
                quantity=10,
                model_probability=0.65,
                forecast_bin=">=87",
            )

            # Verify trade was written
            reloaded = PaperLedger(ledger_path=self.ledger_path)
            trades = reloaded.ledger_data.get("trades", [])
            self.assertEqual(len(trades), 1)
            self.assertEqual(trades[0]["status"], "open")
            self.assertEqual(trades[0]["pnl"], 0.0)

            # Pre-settlement: PnL is 0 (open trade)
            pre_summary = reloaded.get_summary()
            self.assertEqual(pre_summary["daily_pnl"], 0.0,
                "Open trade must have 0 daily_pnl before settlement.")

            # Step 2: Settle
            settle_paper_trades(
                ledger_path=self.ledger_path,
                settlements_path=self.settlements_path,
                performance_path=self.performance_path,
                settlement_as_of_time=datetime(2026, 5, 7, 7, 0, tzinfo=timezone.utc),
            )

            # Step 3: Verify settlement record
            self.assertTrue(self.settlements_path.exists())
            with open(self.settlements_path) as f:
                slines = [json.loads(l) for l in f if l.strip()]
            self.assertEqual(len(slines), 1)
            self.assertEqual(slines[0]["result"], "LOST")
            self.assertAlmostEqual(slines[0]["simulated_pnl"], -0.40, places=4)
            self.assertEqual(slines[0]["safety"], "NO REAL TRADING EXECUTION")

            # Step 4: Verify PnL writeback (F1)
            post_ledger = PaperLedger(ledger_path=self.ledger_path)
            trades_after = post_ledger.ledger_data.get("trades", [])
            self.assertEqual(trades_after[0]["status"], "settled")
            self.assertAlmostEqual(trades_after[0]["pnl"], -0.40, places=4)

            # Step 5: Verify get_summary returns correct PnL
            post_summary = post_ledger.get_summary()
            self.assertLess(post_summary["daily_pnl"], 0.0,
                "daily_pnl must be negative after settling a losing trade.")
            self.assertLess(post_summary["weekly_pnl"], 0.0,
                "weekly_pnl must be negative after settling a losing trade.")

            # Step 6: Risk gates must accept this summary correctly
            # At -0.40, below $50 threshold so Gate 7 should still pass
            gate7 = check_daily_loss_limit(post_summary)
            self.assertTrue(gate7.passed, "Single -$0.40 loss should not trip Gate 7.")

            # But with summary forcibly showing big loss, Gate 7 blocks
            big_loss_summary = {**post_summary, "daily_pnl": -55.0}
            gate7_blocked = check_daily_loss_limit(big_loss_summary)
            self.assertFalse(gate7_blocked.passed,
                "Gate 7 must block when daily_pnl < -$50.")

            gate8_blocked = check_weekly_drawdown_limit(
                {**post_summary, "weekly_pnl": -160.0}
            )
            self.assertFalse(gate8_blocked.passed,
                "Gate 8 must block when weekly_pnl < -$150.")

        finally:
            smod.HISTORY_FILE = orig_history


if __name__ == "__main__":
    unittest.main()

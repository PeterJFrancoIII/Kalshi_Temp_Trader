# AGENTS.md — Contract for future agents (human or AI)

> **You are touching a research MVP that predicts KMIA daily max temperature
> and compares it against Kalshi market prices. There is no real-money
> trading and no order execution path. Anything that pretends otherwise is
> a bug to be reverted, not a feature to be wired.**

This file is the entry point for any agent picking up work on this
repository. Read it before opening other files. Everything below is
enforced by tests in `backend/tests/test_refactor_invariants.py`; the
invariants are the contract.

---

## 1. The five non-negotiable rules

| # | Rule | Enforced by |
|---|------|-------------|
| 1 | **No real-money trading.** The `safety` block in every paper signal report must keep `no_real_trading: True` and `no_order_execution: True`. | Manual review + downstream tests |
| 2 | **`REQUIRED_BINS` is defined once**, in `backend/src/shared/types.py`. The list itself is part of the MVP lockdown ([docs/MVP_LOCKDOWN.md](docs/MVP_LOCKDOWN.md)). | `test_required_bins_defined_only_in_shared_types`, `test_canonical_bins_match_mvp_lockdown` |
| 3 | **No `sys.path` mutation** under `backend/src`; **no `from src.X` / `import src.X`** anywhere. Launchers set `PYTHONPATH=backend/src` instead. | `test_no_sys_path_insert_in_backend_src`, `test_no_src_dot_imports_in_backend_src`, `test_no_src_dot_imports_in_backend_tests` |
| 4 | **One canonical implementation per domain concern.** See the canonical-module table below. | `test_single_kalshi_public_client_definition`, `test_single_kalshi_fee_formula_definition`, `test_no_paper_trade_ledger_jsonl_reference_in_paper_trading`, `test_orm_models_use_record_suffix` |
| 5 | **Streamlit tab renderers live under `console/pages/`**, and the `paper_trading.signal_generator` orchestrator stays under 400 lines with its six helpers intact. | `test_render_functions_live_under_console_pages_only`, `test_generate_paper_signal_stays_under_size_budget`, `test_signal_generator_helpers_remain_module_level` |

If you can't satisfy all five, stop and add a new ADR under `docs/adr/`
explaining the trade-off — do not delete an invariant to make a test
pass.

---

## 2. Canonical-module table

Each concern below has a single source of truth. When you need to change
behavior, change it *there*. The other locations are either deprecation
shims or pure consumers; both should remain thin.

| Concern | Canonical module | Notes |
|---|---|---|
| KMIA forecast bins (`REQUIRED_BINS` etc.) | `backend/src/shared/types.py` | Pydantic types live here too. |
| Kalshi public REST client | `backend/src/market_data/kalshi_public_client.py` | `backend/src/kalshi/client.py` is a deprecation shim. |
| Kalshi taker fee formula `0.07 * p * (1 - p)` | `backend/src/trading/edge_engine.calculate_kalshi_fee` | Anyone computing fees must route through this. |
| Edge / EV / speed-to-ROI math | `backend/src/trading/edge_engine.py` | `recommendation/ev.py` re-exports for backward compat. |
| Paper trading ledger | `backend/src/paper_trading/paper_ledger.PaperLedger` writing to `shared.artifact_paths.PAPER_LEDGER_FILE` | The legacy `paper_trade_ledger.jsonl` path is forbidden inside `paper_trading/`. |
| Paper signal generation | `backend/src/paper_trading/signal_generator.generate_paper_signal` | Orchestrator only — per-step logic lives in the six `_extract_*` / `_resolve_*` / `_build_*` / `_decide_*` / `_load_*` helpers. |
| ORM rows | `backend/src/db/models.py`, all classes suffixed `*Record` | Bare names (`DailyPrediction`, `WeatherSnapshot`, `ClimiaReport`) belong to Pydantic types in `shared.types`. |
| NWS KMIA ingest orchestrator | `backend/src/ingestion/weather_status_writer.NWSKMIAClient` | `weather/nws_kmia_client.py` is a shim. |
| Streamlit dashboard helpers | `backend/src/console/data_helpers.py` (pure) + `backend/src/console/pages/*.py` (UI). `web_console.py` is the lightweight entry point. |
| Feature flags | `backend/src/shared/feature_flags.py` | LLM review defaults OFF; opt in with `KMIA_LLM_REVIEW_ENABLED=1`. |
| Concurrent JSONL persistence | `backend/src/storage/jsonl_store.JSONLStore` | `fcntl` advisory locks on every read/write. |

---

## 3. How to ship a change

1. **Read the invariants.** Open `backend/tests/test_refactor_invariants.py`
   first; it is shorter than you think (12 tests) and tells you what
   structural constraints you must preserve.
2. **Pick one concern per PR.** If you need to touch two modules in the
   canonical table, that is two PRs.
3. **Add a characterization test before you refactor.** If you are
   restructuring a function with no test coverage, write the test
   against current behavior, watch it pass, *then* refactor. The
   `test_signal_generator_helpers.py` file is a working example of this
   pattern.
4. **Run the gate.**
   ```bash
   cd backend
   PYTHONPATH=src python3 tests/run_tests.py
   ```
   The script prints `ALL TESTS PASSED.` on success. Anything else, even
   a single ERROR, means you are not done.
5. **Smoke the live workflow.** For changes that touch the paper-trading
   pipeline, run a dry invocation against the current artifacts:
   ```bash
   cd backend
   PYTHONPATH=src python3 -c "from paper_trading.signal_generator import generate_paper_signal; print(generate_paper_signal())"
   ```
   The output report must still contain the `safety` block with
   `no_real_trading: True`.
6. **Update [`docs/REFACTORING_PLAN.md`](docs/REFACTORING_PLAN.md)** if
   your change advances or alters a phase.
7. **Add or update an ADR** under `docs/adr/` if you made a structural
   decision (new module boundary, new invariant, new external
   dependency).

---

## 4. Language policy

All user-facing responses, commit messages, and documentation in this
repository are in **English** ([.cursor/rules/english-only.mdc](.cursor/rules/english-only.mdc)).
Do not default to another language regardless of the agent's global
defaults.

---

## 5. Things you should NOT do without explicit instruction

- Wire the LLM reviewer into the daily pipeline. It is intentionally
  deferred behind a feature flag (`shared.feature_flags.is_llm_review_enabled`).
- Add a new station, sensor source, or market type. The MVP is locked to
  KMIA + Kalshi daily max temperature contracts.
- Replace the file-based artifact persistence with a database for
  *ops* artifacts. The DB is used for *historical analytics* only.
- Touch `.cursor/rules/english-only.mdc` or the safety block at the
  bottom of every signal report.
- Force-push or amend a commit that has been pushed to remote.

---

## 6. Map of where to start when a thing breaks

| Symptom | First file to read |
|---|---|
| Dashboard tab renders wrong / blank | `backend/src/console/pages/<tab>.py` then `console/data_helpers.py` |
| Paper signal report is empty / `NO_SIGNAL` | `backend/src/paper_trading/signal_generator._load_event_forecast` and the NWS snapshot freshness gate (`weather.nws_snapshot_contract.assess_nws_snapshot`) |
| "Action is NO TRADE but I expect a BUY" | `backend/src/paper_trading/signal_generator._decide_paper_action`, then the weather gate |
| Edge / fee math looks off | `backend/src/trading/edge_engine.py` (single source of truth) |
| Wrong ORM model name in error | Check that the import uses the `*Record` suffix |
| `from src.X import ...` ImportError | Switch to the bare import (`from X import ...`) and run with `PYTHONPATH=backend/src` |

---

## 7. Quick reference — additional canonical docs

- [docs/REFACTORING_PLAN.md](docs/REFACTORING_PLAN.md) — phase ledger and rationale
- [docs/MVP_LOCKDOWN.md](docs/MVP_LOCKDOWN.md) — what is in / out of scope
- [docs/REAL_TRADING_GATE.md](docs/REAL_TRADING_GATE.md) — what would need to change to ever execute real orders (and why we are not doing that)
- [docs/adr/](docs/adr/) — accepted architecture decisions
- [CODE_GOVERNANCE.md](CODE_GOVERNANCE.md) — broader governance policies that pre-date the refactor

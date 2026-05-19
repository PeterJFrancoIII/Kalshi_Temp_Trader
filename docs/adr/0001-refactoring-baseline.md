# ADR-0001: Refactoring baseline and phase discipline

**Status:** Accepted  
**Date:** 2026-05-19

## Context

The KMIA predictor grew via multi-agent contributions. Duplication (Kalshi clients, ledgers, `REQUIRED_BINS`, import styles) and a large `web_console.py` increase maintenance cost. MVP lockdown forbids real trading and bin changes without review.

## Decision

1. Refactor in **phases** defined in [REFACTORING_PLAN.md](../REFACTORING_PLAN.md), starting at **Phase 0** (guardrails only).
2. **Behavior-preserving** merges before structural deletes (deletion test / deepening).
3. **Canonical sources:**
   - Bins: `backend/src/shared/types.py` → `REQUIRED_BINS`
   - Artifacts: `backend/src/shared/artifact_paths.py`
   - Kalshi read-only API: `backend/src/market_data/kalshi_public_client.py`
   - Paper account: `backend/src/paper_trading/paper_ledger.py` → `ledger.json`
4. Every phase ends with `bash scripts/run_tests.sh` green and safety grep clean.
5. No real-money execution paths; ADR required to revisit [REAL_TRADING_GATE.md](../REAL_TRADING_GATE.md).

## Consequences

- Short-term: small PRs, visible progress in REFACTORING_PLAN status table.
- Long-term: fewer drift bugs, clearer ownership for agents and humans.
- Risk: import churn; mitigated by Phase 1 before large merges.

## Baseline

- Test command: `bash scripts/run_tests.sh`
- Recorded passing: 2026-05-19 (full suite)
- Recorded passing after Phase 1 (import hygiene): 2026-05-19 (full suite + 3 new invariants)

---
name: risk-gate-auditor
description: invoke when editing risk_engine, gates, or evaluating trade signals
---

# Risk Gate Auditor

## Purpose
Ensure all paper signals fail closed unless safety data is present and valid.

## Instructions
1. **Fail-Closed Triggers**:
   - Missing weather timestamp blocks the signal.
   - Stale weather data blocks the signal.
   - Missing market price blocks the signal.
   - Missing ledger/PnL state blocks loss gates.
2. **Boundary Risk**: Near-boundary settlement risk can block or reduce confidence scores.
3. **Edge Computation**: Fee and slippage-adjusted edge must be computed before declaring eligibility.
4. **No Fallbacks**: Do not use synthetic fallbacks or defaults that bypass these gates.
5. **Read-Only Enforced**: Ensure no live trading execution, order functions, or HTTP write methods exist in the pipeline.

## Blockers / Fail-Closed Rules
- **Any Missing Safety Data**: Abort signal generation.
- **Real Trading Detected**: Block execution if any live trading code is found.

## Required Output Format
Every risk evaluation must produce a check list of gates evaluated and their pass/fail status, ending with a final `verdict`.

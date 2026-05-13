---
name: kalshi-agent-governance-rollup
description: invoke before any merge, push, branch consolidation, or readiness declaration
---

# Kalshi Agent Governance Rollup

## Purpose
Ensure multi-agent governance, phase review, and final roll-up are consistent.

## Instructions
1. **Ownership Boundaries**: Respect agent ownership boundaries as defined in `AGENT_WORKPLAN.md`.
2. **Reviewers**:
   - **Agent 1** reviews phase/local change sets and overall architecture.
   - **Agent 8** resolves cross-agent conflicts and provides final system-wide Go/No-Go authority for paper-evaluation readiness.
3. **No Claims Without Review**: Do not make commit/push or paper-evaluation readiness claims without the proper reviewer's approval.
4. **No Real Trading**: Verify no live trading code is introduced.

## Blockers / Fail-Closed Rules
- **Agent 8 Go/No-Go**: Missing Agent 8 approval blocks readiness declaration.
- **Test Failures**: Cannot proceed if required tests are failing.

## Required Output Format
Governance Rollup Report must include:
- inputs read
- files inspected
- files changed
- tests run
- safety findings
- lookahead findings
- risk findings
- gaps
- verdict
- machine-readable JSON summary

"""Feature flags for the KMIA Kalshi predictor.

This is the single source of truth for opt-in runtime features. Flags
default to safe / off. Tests can override values directly; production
deploys override via environment variables (truthy values are
``"1"``, ``"true"``, ``"yes"``, ``"on"``, case-insensitive).

Adding a new flag:
    1. Declare a module-level default constant here.
    2. Add an `is_<name>_enabled()` helper that consults the env var.
    3. Document the semantics in the docstring.
    4. Reference the flag from the code path it gates.

NO REAL TRADING EXECUTION.
"""

from __future__ import annotations

import os

# --- Truthy parsing -------------------------------------------------------

_TRUTHY = {"1", "true", "yes", "on", "t", "y"}


def _env_bool(name: str, default: bool) -> bool:
    """Return True if ``$name`` is set to a truthy value, else ``default``.

    Missing or empty env vars fall back to ``default``. Unknown values are
    treated as ``False`` (defensive).
    """
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in _TRUTHY


# --- LLM review (Phase 3.3) -----------------------------------------------

# LLM review is intentionally deferred for the current MVP. The validator
# in :mod:`llm.llm_reviewer` describes the contract any future LLM
# integration must satisfy, but no live LLM is called by the daily
# pipeline.
#
# When you wire a real LLM provider, set the env var
# ``KMIA_LLM_REVIEW_ENABLED=1`` and route the prediction through
# ``llm.llm_reviewer.validate_llm_review_output`` as a sanity gate.
LLM_REVIEW_ENABLED_ENV = "KMIA_LLM_REVIEW_ENABLED"


def is_llm_review_enabled() -> bool:
    """True if LLM review should run in the daily pipeline.

    Default is ``False``: the MVP runs deterministic rules-based models
    only. See :mod:`llm.llm_reviewer` for the validation contract a future
    LLM integration must satisfy.
    """
    return _env_bool(LLM_REVIEW_ENABLED_ENV, default=False)


__all__ = [
    "LLM_REVIEW_ENABLED_ENV",
    "is_llm_review_enabled",
]

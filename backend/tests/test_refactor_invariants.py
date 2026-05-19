"""
Refactor guardrails — structural invariants that should not regress.

Phase 0: REQUIRED_BINS uniqueness.
Phase 1: import hygiene under backend/src and backend/tests.
"""

import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = BACKEND_ROOT / "src"
BACKEND_TESTS = BACKEND_ROOT / "tests"
CANONICAL_BINS_FILE = BACKEND_SRC / "shared" / "types.py"


def test_required_bins_defined_only_in_shared_types():
    """REQUIRED_BINS must have a single literal definition (shared/types.py)."""
    pattern = re.compile(r"^\s*REQUIRED_BINS\s*=\s*\[", re.MULTILINE)
    definitions = []
    for py_file in BACKEND_SRC.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if pattern.search(text):
            definitions.append(py_file.relative_to(BACKEND_SRC))
    assert definitions == [Path("shared/types.py")], (
        "REQUIRED_BINS must only be defined in shared/types.py; "
        f"found definitions in: {definitions}"
    )


def test_canonical_bins_match_mvp_lockdown():
    """Bins align with MASTER_CONTEXT / MVP lockdown."""
    text = CANONICAL_BINS_FILE.read_text(encoding="utf-8")
    assert '">=87"' in text or "'>=87'" in text
    assert '"<=78"' in text or "'<=78'" in text


def _grep_lines(root: Path, regex: re.Pattern) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for py_file in root.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                hits.append((py_file.relative_to(BACKEND_ROOT), lineno, line.strip()))
    return hits


def test_no_src_dot_imports_in_backend_src():
    """`from src.X` / `import src.X` is forbidden under backend/src.

    Standard entrypoint is `PYTHONPATH=backend/src` with bare module imports
    (e.g. `from forecasting.X import ...`). `from src.X` only works when
    backend/ is on path, which is fragile and inconsistent.
    """
    pattern = re.compile(r"^\s*(from\s+src\.|import\s+src\.)")
    hits = _grep_lines(BACKEND_SRC, pattern)
    assert not hits, (
        "Found forbidden `from src.X` / `import src.X` in backend/src:\n"
        + "\n".join(f"  {p}:{ln}: {line}" for p, ln, line in hits)
    )


def test_no_src_dot_imports_in_backend_tests():
    """Same hygiene rule for backend/tests — bare imports only.

    Tests run with backend/src on path via run_tests.py bootstrap.
    """
    pattern = re.compile(r"^\s*(from\s+src\.|import\s+src\.)")
    hits = _grep_lines(BACKEND_TESTS, pattern)
    assert not hits, (
        "Found forbidden `from src.X` / `import src.X` in backend/tests:\n"
        + "\n".join(f"  {p}:{ln}: {line}" for p, ln, line in hits)
    )


def test_no_sys_path_insert_in_backend_src():
    """No `sys.path.insert` / `sys.path.append` under backend/src.

    Production modules must rely on PYTHONPATH being set by the launcher
    scripts (scripts/*.sh), not on runtime path mutation.
    """
    pattern = re.compile(r"sys\.path\.(insert|append)")
    hits = _grep_lines(BACKEND_SRC, pattern)
    assert not hits, (
        "Found forbidden sys.path mutation in backend/src:\n"
        + "\n".join(f"  {p}:{ln}: {line}" for p, ln, line in hits)
    )


def test_no_paper_trade_ledger_jsonl_reference_in_paper_trading():
    """The canonical production paper ledger is ledger.json via PaperLedger.

    Modules under backend/src/paper_trading/ must not reference the legacy
    ``paper_trade_ledger.jsonl`` filename — that path was always empty in
    production and reading it produced silently-wrong metrics.

    The backtesting coordinator legitimately writes per-run JSONL ledgers
    under its own run directory; that lives in `backtesting/`, not
    `paper_trading/`, and is therefore not subject to this invariant.
    """
    paper_trading_dir = BACKEND_SRC / "paper_trading"
    offenders = []
    for py_file in paper_trading_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if "paper_trade_ledger.jsonl" in text:
            offenders.append(py_file.relative_to(BACKEND_SRC))
    assert not offenders, (
        "paper_trading/ must not reference the legacy paper_trade_ledger.jsonl "
        f"filename; offenders: {offenders}. Use PaperLedger / "
        "shared.artifact_paths.PAPER_LEDGER_FILE instead."
    )


def test_single_kalshi_public_client_definition():
    """Only one `class KalshiPublicClient` definition allowed in backend/src.

    Canonical location is market_data/kalshi_public_client.py. kalshi/client.py
    is a deprecation shim that must only re-export, not redefine.
    """
    pattern = re.compile(r"^\s*class\s+KalshiPublicClient\b", re.MULTILINE)
    definitions = []
    for py_file in BACKEND_SRC.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if pattern.search(text):
            definitions.append(py_file.relative_to(BACKEND_SRC))
    assert definitions == [Path("market_data/kalshi_public_client.py")], (
        "KalshiPublicClient must only be defined in market_data/kalshi_public_client.py; "
        f"found definitions in: {definitions}"
    )

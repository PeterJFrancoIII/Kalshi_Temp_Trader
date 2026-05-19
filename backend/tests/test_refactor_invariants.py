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


def test_orm_models_use_record_suffix():
    """ORM models that collide with Pydantic types in shared.types must use
    the ``*Record`` suffix in production code.

    The Pydantic types in :mod:`shared.types` (``DailyPrediction``,
    ``WeatherSnapshot``, ``ClimiaReport``, ``Recommendation``) are
    different objects from the SQLAlchemy mappings in :mod:`db.models`.
    Sharing names led to confusing imports and risk of accidentally
    constructing the wrong one in tests / runtime code. Backward-compat
    aliases remain inside ``db/models.py`` itself, but no other module in
    ``backend/src`` may import the bare names from ``db.models``.
    """
    legacy_names = ("DailyPrediction", "WeatherSnapshot", "ClimiaReport")
    # Recommendation also collides but the bare name appears in
    # `recommendation.types` (a separate dataclass) for legitimate reasons,
    # so we only enforce on the three weather/prediction types here.
    pattern = re.compile(
        r"^\s*from\s+db\.models\s+import\s+([^\n]+)$", re.MULTILINE
    )
    offenders: list[tuple[Path, str]] = []
    for py_file in BACKEND_SRC.rglob("*.py"):
        if py_file.relative_to(BACKEND_SRC) == Path("db/models.py"):
            continue
        text = py_file.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            imported = match.group(1)
            for legacy in legacy_names:
                # Match the legacy name as a whole token (avoid matching
                # the *Record suffix variant).
                if re.search(rf"\b{legacy}\b(?!Record)", imported):
                    offenders.append(
                        (py_file.relative_to(BACKEND_SRC), legacy)
                    )
    assert not offenders, (
        "Production code under backend/src must import ORM rows via the "
        "*Record suffix (e.g. DailyPredictionRecord), not the bare names "
        "that collide with shared.types. Offenders: "
        f"{offenders}"
    )


def test_single_kalshi_fee_formula_definition():
    """The literal Kalshi fee formula must live in exactly one module.

    The taker fee ``0.07 * p * (1 - p)`` is a domain constant; multiple
    inline copies invite drift if Kalshi changes their fee schedule. The
    canonical definition is :func:`trading.edge_engine.calculate_kalshi_fee`.
    Other call sites must route through that helper.

    This invariant matches the *computational* literal — strings like
    ``"0.07 *"`` inside docstrings/comments are allowed (and grep finds
    them too), so the test specifically looks for an expression of the
    shape ``0.07 * <price> * (1 - <price>)`` in actual Python code.
    """
    # Match a multiplication of 0.07 by a price and (1 - price) factor,
    # which is the Kalshi fee formula shape regardless of variable name
    # used for the price.
    pattern = re.compile(
        r"0\.07\s*\*\s*[A-Za-z_][A-Za-z_0-9]*\s*\*\s*\(\s*1(?:\.0)?\s*-\s*[A-Za-z_][A-Za-z_0-9]*\s*\)"
    )
    hits: list[Path] = []
    for py_file in BACKEND_SRC.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        # Strip out triple-quoted docstrings and # comments before checking.
        without_docstrings = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
        without_docstrings = re.sub(r"'''.*?'''", "", without_docstrings, flags=re.DOTALL)
        code_only = "\n".join(
            line.split("#", 1)[0] for line in without_docstrings.splitlines()
        )
        if pattern.search(code_only):
            hits.append(py_file.relative_to(BACKEND_SRC))
    assert hits == [Path("trading/edge_engine.py")], (
        "The Kalshi fee formula `0.07 * p * (1 - p)` must be defined only in "
        "trading/edge_engine.py (via calculate_kalshi_fee). Inline copies "
        f"break the single-source-of-truth invariant. Found in: {hits}"
    )


def test_no_paper_trade_ledger_jsonl_reference_in_paper_trading():
    """The canonical production paper ledger is ledger.json via PaperLedger.

    Modules under backend/src/paper_trading/ must not reference the legacy
    ``paper_trade_ledger.jsonl`` filename in *executable code* — that path
    was always empty in production and reading it produced silently-wrong
    metrics.

    Docstrings and comments may still mention the filename for historical
    context; we strip those out before checking. The backtesting
    coordinator legitimately writes per-run JSONL ledgers under its own
    run directory; that lives in ``backtesting/``, not ``paper_trading/``,
    and is therefore not subject to this invariant.
    """
    paper_trading_dir = BACKEND_SRC / "paper_trading"
    offenders = []
    for py_file in paper_trading_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        # Strip triple-quoted docstrings and line comments before checking.
        code_only = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
        code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
        code_only = "\n".join(
            line.split("#", 1)[0] for line in code_only.splitlines()
        )
        if "paper_trade_ledger.jsonl" in code_only:
            offenders.append(py_file.relative_to(BACKEND_SRC))
    assert not offenders, (
        "paper_trading/ must not reference the legacy paper_trade_ledger.jsonl "
        f"filename in executable code; offenders: {offenders}. Use PaperLedger / "
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


def test_render_functions_live_under_console_pages_only():
    """``render_<tab>`` tab functions must live under console/pages/.

    Phase 3.1 split web_console.py into focused tab modules. The
    entry-point file should only *import* tab renderers, never *define*
    them — otherwise the file creeps back to its old 1.7k-line shape
    and the per-tab boundary erodes.

    The Streamlit multipage convention under ``backend/src/pages/`` is
    exempt: those files are auto-discovered standalone Streamlit pages,
    not tab renderers for the main console, and their internal
    ``render_*`` helpers are private to each page.
    """
    pattern = re.compile(r"^\s*def\s+render_[A-Za-z_]+\s*\(", re.MULTILINE)
    expected_dir = BACKEND_SRC / "console" / "pages"
    streamlit_multipage_dir = BACKEND_SRC / "pages"
    offenders = []
    for py_file in BACKEND_SRC.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if not pattern.search(text):
            continue
        # Skip Streamlit's auto-discovered multipage directory; those
        # files own their own internal render helpers.
        try:
            py_file.relative_to(streamlit_multipage_dir)
            continue
        except ValueError:
            pass
        if py_file.parent != expected_dir:
            offenders.append(py_file.relative_to(BACKEND_SRC))
    assert not offenders, (
        "render_* tab functions must live under console/pages/; "
        f"unexpected definitions found in: {offenders}. Move the render "
        "function to console/pages/<tab>.py and import it from web_console."
    )

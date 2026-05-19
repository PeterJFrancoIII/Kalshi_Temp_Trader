"""Streamlit dashboard components for the KMIA Kalshi predictor.

The legacy ``web_console.py`` module bundled ~1.7k lines of helpers,
data loaders, and tab renderers in a single file. This package owns
those pieces in focused modules:

- :mod:`console.data_helpers` — pure helpers (file IO, formatters,
  domain-aware extractors). No Streamlit calls except in
  :func:`safe_dataframe`, which renders via ``st.dataframe``.
- :mod:`console.pages` — one Streamlit tab per submodule.

``web_console.py`` is now a thin Streamlit entry point that wires the
sidebar and the eight tabs together. It also re-exports the helper
names so the existing test suite imports
(``from web_console import ...``) keep working.

NO REAL TRADING EXECUTION.
"""

__all__: list[str] = []

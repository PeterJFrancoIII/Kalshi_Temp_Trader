"""Configurable TWC vs NWS comparison view for the KMIA Streamlit console.

This module is intentionally UI-only: it does not place orders, size trades,
or mutate Kalshi/account state. It wraps an existing comparison payload or
provider forecast payload with persistent display settings.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
TWC_NWS_COMPARISON_CONFIG_PATH = CONFIG_DIR / "twc_nws_comparison_config.json"

DEFAULT_TWC_NWS_COMPARISON_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "station": "KMIA",
    "lead_time_start_hour": 1,
    "lead_time_end_hour": 48,
    "show_twc": True,
    "show_nws": True,
    "show_spread": True,
    "spread_mode": "signed",  # signed or absolute
    "temperature_unit": "F",
    "table_density": "standard",  # compact or standard
    "show_mae": True,
    "show_within_1f": False,
    "show_within_2f": False,
    "show_within_3f": True,
    "show_within_4f": False,
    "show_within_5f": False,
    "show_within_6f": False,
}

_NUMERIC_COLUMN_ALIASES = {
    "lead_hour": ["lead_hour", "hour", "lead_time", "lead_time_hour", "forecast_hour"],
    "twc_temp_f": ["twc_temp_f", "twc_forecast_f", "twc_temperature_f", "twc", "weather_company_f"],
    "nws_temp_f": ["nws_temp_f", "nws_forecast_f", "nws_temperature_f", "nws", "nbm_temp_f"],
    "twc_mae_f": ["twc_mae_f", "twc_mae", "weather_company_mae_f"],
    "nws_mae_f": ["nws_mae_f", "nws_mae", "nbm_mae_f"],
}

_ACCURACY_ALIAS_TEMPLATES = {
    "twc_within_{n}f_pct": [
        "twc_within_{n}f_pct",
        "twc_within_{n}f",
        "twc_pm{n}f_pct",
        "weather_company_within_{n}f_pct",
    ],
    "nws_within_{n}f_pct": [
        "nws_within_{n}f_pct",
        "nws_within_{n}f",
        "nws_pm{n}f_pct",
        "nbm_within_{n}f_pct",
    ],
}

_COMPARISON_PAYLOAD_KEYS = (
    "twc_nws_comparison",
    "twc_vs_nws_comparison",
    "forecast_comparison",
    "provider_comparison",
    "comparison_rows",
)

_TWC_PAYLOAD_KEYS = ("twc", "twc_forecast", "weather_company", "weather_company_forecast")
_NWS_PAYLOAD_KEYS = ("nws", "nws_forecast", "nbm", "nbm_forecast")


def _deep_merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(defaults)
    for key, value in overrides.items():
        if key in merged:
            merged[key] = value
    return merged


def load_twc_nws_comparison_config(
    config_path: Path = TWC_NWS_COMPARISON_CONFIG_PATH,
) -> dict[str, Any]:
    """Load persisted display config, falling back safely to defaults."""
    if not config_path.exists():
        return deepcopy(DEFAULT_TWC_NWS_COMPARISON_CONFIG)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = json.load(f)
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULT_TWC_NWS_COMPARISON_CONFIG)

    if not isinstance(raw_config, dict):
        return deepcopy(DEFAULT_TWC_NWS_COMPARISON_CONFIG)

    return _deep_merge(DEFAULT_TWC_NWS_COMPARISON_CONFIG, raw_config)


def save_twc_nws_comparison_config(
    config: dict[str, Any],
    config_path: Path = TWC_NWS_COMPARISON_CONFIG_PATH,
) -> None:
    """Persist display config to disk."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized = _deep_merge(DEFAULT_TWC_NWS_COMPARISON_CONFIG, config)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sanitized, f, indent=2, sort_keys=True)
        f.write("\n")


def reset_twc_nws_comparison_config(
    config_path: Path = TWC_NWS_COMPARISON_CONFIG_PATH,
) -> dict[str, Any]:
    """Reset persisted display config to the standard layout."""
    config = deepcopy(DEFAULT_TWC_NWS_COMPARISON_CONFIG)
    save_twc_nws_comparison_config(config, config_path=config_path)
    return config


def render_twc_nws_comparison_settings(
    config: dict[str, Any],
    config_path: Path = TWC_NWS_COMPARISON_CONFIG_PATH,
) -> dict[str, Any]:
    """Render the user settings panel and persist changes."""
    updated = _deep_merge(DEFAULT_TWC_NWS_COMPARISON_CONFIG, config)

    with st.expander("TWC vs NWS View Settings", expanded=False):
        range_start, range_end = st.slider(
            "Lead time range",
            min_value=1,
            max_value=48,
            value=(int(updated["lead_time_start_hour"]), int(updated["lead_time_end_hour"])),
            step=1,
            key="twc_nws_lead_time_range",
        )

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            updated["show_twc"] = st.checkbox("Show TWC", value=bool(updated["show_twc"]), key="twc_nws_show_twc")
            updated["show_mae"] = st.checkbox("Show MAE", value=bool(updated["show_mae"]), key="twc_nws_show_mae")
        with col_b:
            updated["show_nws"] = st.checkbox("Show NWS", value=bool(updated["show_nws"]), key="twc_nws_show_nws")
            updated["show_within_3f"] = st.checkbox(
                "Show +/-3F accuracy",
                value=bool(updated["show_within_3f"]),
                key="twc_nws_show_within_3f_summary",
            )
        with col_c:
            updated["show_spread"] = st.checkbox("Show spread", value=bool(updated["show_spread"]), key="twc_nws_show_spread")
            updated["table_density"] = st.radio(
                "Table density",
                options=["compact", "standard"],
                index=0 if updated["table_density"] == "compact" else 1,
                horizontal=True,
                key="twc_nws_table_density",
            )

        updated["spread_mode"] = st.radio(
            "Spread mode",
            options=["signed", "absolute"],
            index=0 if updated["spread_mode"] == "signed" else 1,
            horizontal=True,
            key="twc_nws_spread_mode",
        )

        advanced_cols = st.columns(6)
        for idx, threshold in enumerate([1, 2, 3, 4, 5, 6]):
            flag = f"show_within_{threshold}f"
            with advanced_cols[idx]:
                updated[flag] = st.checkbox(
                    f"+/-{threshold}F",
                    value=bool(updated[flag]),
                    key=f"twc_nws_{flag}_{threshold}_{idx}",
                )

        updated["lead_time_start_hour"] = int(range_start)
        updated["lead_time_end_hour"] = int(range_end)

        if st.button("Reset TWC vs NWS layout", key="twc_nws_reset_layout"):
            updated = reset_twc_nws_comparison_config(config_path=config_path)
            st.success("TWC vs NWS layout reset to standard.")
            st.rerun()

    save_twc_nws_comparison_config(updated, config_path=config_path)
    return updated


def _as_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, pd.DataFrame):
        return payload.to_dict("records")
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("rows", "data", "forecasts", "hourly", "lead_hours"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        return [payload]
    return []


def _find_first_key(data: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.replace("%", "").replace("F", "").replace("°", "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for canonical, aliases in _NUMERIC_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in row:
                normalized[canonical] = _coerce_float(row.get(alias))
                break

    for threshold in [1, 2, 3, 4, 5, 6]:
        for canonical_template, alias_templates in _ACCURACY_ALIAS_TEMPLATES.items():
            canonical = canonical_template.format(n=threshold)
            for alias_template in alias_templates:
                alias = alias_template.format(n=threshold)
                if alias in row:
                    normalized[canonical] = _coerce_float(row.get(alias))
                    break

    for key, value in row.items():
        normalized.setdefault(key, value)

    return normalized


def _merge_provider_rows(twc_payload: Any, nws_payload: Any) -> list[dict[str, Any]]:
    twc_rows = [_normalize_row(row) for row in _as_rows(twc_payload)]
    nws_rows = [_normalize_row(row) for row in _as_rows(nws_payload)]

    merged: dict[int, dict[str, Any]] = {}
    for row in twc_rows:
        lead_hour = int(row.get("lead_hour") or len(merged) + 1)
        merged.setdefault(lead_hour, {"lead_hour": lead_hour})
        for key, value in row.items():
            if key == "lead_hour":
                continue
            if key.startswith("twc_"):
                merged[lead_hour][key] = value
            elif key in ("temp_f", "forecast_f", "temperature_f"):
                merged[lead_hour]["twc_temp_f"] = value

    for row in nws_rows:
        lead_hour = int(row.get("lead_hour") or len(merged) + 1)
        merged.setdefault(lead_hour, {"lead_hour": lead_hour})
        for key, value in row.items():
            if key == "lead_hour":
                continue
            if key.startswith("nws_"):
                merged[lead_hour][key] = value
            elif key in ("temp_f", "forecast_f", "temperature_f"):
                merged[lead_hour]["nws_temp_f"] = value

    return [merged[key] for key in sorted(merged)]


def extract_twc_nws_comparison_rows(source_data: Any) -> list[dict[str, Any]]:
    """Extract comparison rows from common console payload shapes."""
    if isinstance(source_data, pd.DataFrame):
        return [_normalize_row(row) for row in source_data.to_dict("records")]
    if isinstance(source_data, list):
        return [_normalize_row(row) for row in source_data if isinstance(row, dict)]
    if not isinstance(source_data, dict):
        return []

    comparison_payload = _find_first_key(source_data, _COMPARISON_PAYLOAD_KEYS)
    if comparison_payload is not None:
        return [_normalize_row(row) for row in _as_rows(comparison_payload)]

    twc_payload = _find_first_key(source_data, _TWC_PAYLOAD_KEYS)
    nws_payload = _find_first_key(source_data, _NWS_PAYLOAD_KEYS)
    if twc_payload is not None or nws_payload is not None:
        return _merge_provider_rows(twc_payload, nws_payload)

    return []


def build_twc_nws_comparison_dataframe(source_data: Any, config: dict[str, Any]) -> pd.DataFrame:
    """Build a filtered display dataframe without changing comparison math."""
    rows = extract_twc_nws_comparison_rows(source_data)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "lead_hour" not in df.columns:
        df.insert(0, "lead_hour", range(1, len(df) + 1))

    df["lead_hour"] = pd.to_numeric(df["lead_hour"], errors="coerce")
    df = df.dropna(subset=["lead_hour"])
    df["lead_hour"] = df["lead_hour"].astype(int)

    start_hour = int(config.get("lead_time_start_hour", 1))
    end_hour = int(config.get("lead_time_end_hour", 48))
    df = df[(df["lead_hour"] >= start_hour) & (df["lead_hour"] <= end_hour)].copy()

    for temp_col in ("twc_temp_f", "nws_temp_f"):
        if temp_col in df.columns:
            df[temp_col] = pd.to_numeric(df[temp_col], errors="coerce")

    if config.get("show_spread") and {"twc_temp_f", "nws_temp_f"}.issubset(df.columns):
        spread = df["twc_temp_f"] - df["nws_temp_f"]
        if config.get("spread_mode") == "absolute":
            spread = spread.abs()
        df["twc_minus_nws_spread_f"] = spread

    columns = ["lead_hour"]
    if config.get("show_twc") and "twc_temp_f" in df.columns:
        columns.append("twc_temp_f")
    if config.get("show_nws") and "nws_temp_f" in df.columns:
        columns.append("nws_temp_f")
    if config.get("show_spread") and "twc_minus_nws_spread_f" in df.columns:
        columns.append("twc_minus_nws_spread_f")

    if config.get("show_mae"):
        for col in ["twc_mae_f", "nws_mae_f"]:
            if col in df.columns:
                columns.append(col)

    for threshold in [1, 2, 3, 4, 5, 6]:
        if config.get(f"show_within_{threshold}f"):
            for col in [f"twc_within_{threshold}f_pct", f"nws_within_{threshold}f_pct"]:
                if col in df.columns:
                    columns.append(col)

    columns = [col for col in columns if col in df.columns]
    return df[columns]


def render_twc_nws_comparison(source_data: Any, config: dict[str, Any] | None = None) -> None:
    """Render the configurable TWC vs NWS comparison module."""
    st.header("TWC vs NWS Comparison")
    st.caption("Display-only forecast comparison. No trading/account actions are performed here.")

    if config is None:
        config = load_twc_nws_comparison_config()
    config = render_twc_nws_comparison_settings(config)

    df = build_twc_nws_comparison_dataframe(source_data, config)
    if df.empty:
        st.info(
            "No TWC vs NWS comparison rows found yet. Expected one of: "
            "twc_nws_comparison, twc_vs_nws_comparison, forecast_comparison, "
            "provider_comparison, or separate twc/nws forecast payloads."
        )
        with st.expander("Current TWC vs NWS view config"):
            st.json(config)
        return

    column_labels = {
        "lead_hour": "Lead Hour",
        "twc_temp_f": "TWC Temp F",
        "nws_temp_f": "NWS Temp F",
        "twc_minus_nws_spread_f": "TWC - NWS Spread F",
        "twc_mae_f": "TWC MAE F",
        "nws_mae_f": "NWS MAE F",
    }
    for threshold in [1, 2, 3, 4, 5, 6]:
        column_labels[f"twc_within_{threshold}f_pct"] = f"TWC +/-{threshold}F %"
        column_labels[f"nws_within_{threshold}f_pct"] = f"NWS +/-{threshold}F %"

    display_df = df.rename(columns={k: v for k, v in column_labels.items() if k in df.columns})
    height = 420 if config.get("table_density") == "compact" else "content"
    st.dataframe(display_df, width="stretch", hide_index=True, height=height)

    with st.expander("Current TWC vs NWS view config"):
        st.json(config)

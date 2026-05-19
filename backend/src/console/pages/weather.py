"""Weather / NWS tab — live snapshot + freshness gate telemetry."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from console.data_helpers import (
    extract_nws_observation_rows,
    format_num,
    format_temp,
)


def render_weather_nws(w_data, n_data):
    st.header("🌦️ Weather / NWS Live Data")
    st.error("🚨 **NO REAL TRADING EXECUTION — DRY-RUN ONLY**")

    from weather.nws_snapshot_contract import assess_nws_snapshot
    try:
        gate = assess_nws_snapshot(n_data)
    except Exception as e:
        gate = {
            "available": False,
            "allow_paper_recommendations": False,
            "status": "ERROR",
            "no_trade_reason": f"Assessment failed: {e}",
            "warnings": [f"Assessment failed: {e}"],
            "latest_observation_time": None,
            "fetched_at_utc": None,
            "observation_age_minutes": None,
        }

    gate_status = gate.get("status", "UNKNOWN")
    gate_emoji = {"OK": "🟢", "STALE": "🟡", "ERROR": "🔴", "MISSING": "⚪"}.get(gate_status, "❓")
    allow_recommendations = gate.get("allow_paper_recommendations", False)
    allow_emoji = "✅ ALLOWED" if allow_recommendations else "❌ BLOCKED"
    age = gate.get("observation_age_minutes")
    age_str = f"{age:.1f} minutes" if age is not None else "N/A"

    st.subheader("🌤️ Weather Freshness (NWS Gate)")
    gcol1, gcol2, gcol3 = st.columns(3)
    with gcol1:
        st.metric("Gate Status", f"{gate_emoji} {gate_status}")
    with gcol2:
        st.metric("Trading Recommendations", allow_emoji)
    with gcol3:
        st.metric("Observation Age", age_str)

    if not allow_recommendations:
        st.error(f"⚠️ **Gate Blocking Reason:** {gate.get('no_trade_reason') or 'No-trade reason unspecified.'}")
    elif gate.get("warnings"):
        for warning in gate["warnings"]:
            st.warning(f"⚠️ {warning}")

    st.divider()

    if n_data:
        st.subheader("NWS Live Snapshot Metrics")

        nc1, nc2, nc3, nc4 = st.columns(4)
        nc1.metric("Current Temp", format_temp(n_data.get('current_temp_f')))
        nc2.metric("Observed Max Today", format_temp(n_data.get('observed_max_so_far_f')))
        nc3.metric("Wind", f"{n_data.get('wind_direction_compass', '—')} {format_num(n_data.get('wind_speed_mph'), unit='mph')}")
        nc4.metric("Stale Data Indicator", "Yes" if n_data.get("stale_data") else "No")

        st.write(f"**Latest Observation Time:** {n_data.get('latest_observation_time', 'N/A')} (UTC)")
        if n_data.get("wind_gust_mph"):
            st.write(f"**Recent Gust:** {n_data.get('wind_gust_mph')} mph")
        if n_data.get("clouds_x100ft"):
            st.write(f"**Clouds:** {n_data.get('clouds_x100ft')}")

        st.subheader("Recent Observations (KMIA)")
        obs_rows = extract_nws_observation_rows(n_data)
        if obs_rows:
            df_obs = pd.DataFrame(obs_rows)
            display_columns = [
                "time_et",
                "temperature_f",
                "dewpoint_f",
                "relative_humidity_pct",
                "wind_direction_compass",
                "wind_direction_degrees",
                "wind_speed_mph",
                "wind_gust_mph",
                "sea_level_pressure_mb",
                "barometric_pressure_mb",
                "precipitation_last_hour_in",
                "clouds_x100ft",
            ]
            display_cols = [c for c in display_columns if c in df_obs.columns]
            df_display = df_obs[display_cols].copy()

            if "temperature_f" in df_display.columns:
                df_display["temperature_f"] = df_display["temperature_f"].apply(format_temp)
            if "dewpoint_f" in df_display.columns:
                df_display["dewpoint_f"] = df_display["dewpoint_f"].apply(format_temp)
            if "relative_humidity_pct" in df_display.columns:
                df_display["relative_humidity_pct"] = df_display["relative_humidity_pct"].apply(lambda x: format_num(x, unit="%"))
            if "wind_speed_mph" in df_display.columns:
                df_display["wind_speed_mph"] = df_display["wind_speed_mph"].apply(lambda x: format_num(x, unit="mph"))
            if "wind_gust_mph" in df_display.columns:
                df_display["wind_gust_mph"] = df_display["wind_gust_mph"].apply(lambda x: format_num(x, unit="mph"))
            if "sea_level_pressure_mb" in df_display.columns:
                df_display["sea_level_pressure_mb"] = df_display["sea_level_pressure_mb"].apply(lambda x: format_num(x, unit="mb"))
            if "barometric_pressure_mb" in df_display.columns:
                df_display["barometric_pressure_mb"] = df_display["barometric_pressure_mb"].apply(lambda x: format_num(x, unit="mb"))
            if "precipitation_last_hour_in" in df_display.columns:
                df_display["precipitation_last_hour_in"] = df_display["precipitation_last_hour_in"].apply(
                    lambda x: f"{float(x):.2f} in" if x is not None and x != "N/A" and x != "" else "—"
                )

            st.dataframe(df_display, width="stretch", hide_index=True)
        else:
            st.warning("NWS snapshot loaded, but no parsed observation rows were found.")
            if isinstance(n_data, dict):
                st.caption("Available NWS snapshot keys: " + ", ".join(n_data.keys()))

        if n_data.get("warnings"):
            st.warning(" | ".join(n_data.get("warnings")))

        with st.expander("Links & Raw JSON"):
            st.write(f"- [NWS Time Series (KMIA)]({n_data.get('timeseries_source_url')})")
            st.write(f"- [API Observations URL]({n_data.get('api_observations_url')})")
            st.json(n_data)
    else:
        st.info("No live NWS snapshot found. Run `bash scripts/update_nws_live_data.sh`.")

    if w_data:
        st.subheader("Daily Weather Ingestion Status")
        with st.expander("View Daily Weather Status JSON"):
            st.json(w_data)


__all__ = ["render_weather_nws"]

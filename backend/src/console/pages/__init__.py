"""Streamlit tab renderers for the KMIA web console.

Each submodule exposes exactly one ``render_<tab>`` function. The
top-level ``web_console.py`` builds the sidebar and the tab strip, then
dispatches to these renderers.

NO REAL TRADING EXECUTION.
"""

from console.pages.active_forecasts import render_active_forecasts
from console.pages.backtesting import render_backtesting
from console.pages.calibration import render_calibration_learning
from console.pages.command_center import render_command_center
from console.pages.kalshi_market import render_kalshi_market_console
from console.pages.paper_trading import render_paper_trading
from console.pages.system_health import render_system_health
from console.pages.weather import render_weather_nws

__all__ = [
    "render_active_forecasts",
    "render_backtesting",
    "render_calibration_learning",
    "render_command_center",
    "render_kalshi_market_console",
    "render_paper_trading",
    "render_system_health",
    "render_weather_nws",
]

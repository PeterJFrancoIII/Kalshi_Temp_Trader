# KMIA Python Dashboard Plan

This document outlines the Python-only reporting strategy for KMIA temperature forecasts.

## Strategy

To maintain a Python-first, lightweight architecture, the dashboard is implemented as a modular report generator that outputs structured Markdown and HTML.

### Core Module: `report_generator.py`

The `KMIAForecastReport` class in `backend/src/dashboard/report_generator.py` is the central component. It takes a structured data dictionary and provides two output methods:

1.  **`to_markdown()`**: Ideal for automated logs, CLI output, or viewing directly in IDEs like VS Code or PyCharm.
2.  **`to_html()`**: Provides a premium, browser-viewable experience with built-in styling, charts (simulated via tables), and clear layouts.

## Data Schema

The report generator expects a dictionary with the following structure:

```json
{
  "station": "KMIA",
  "date": "YYYY-MM-DD",
  "best_single_number_f": 84,
  "probability_bins": {
    "<=78": 0.00,
    "79-80": 0.05,
    "81-82": 0.20,
    "83-84": 0.55,
    "85-86": 0.15,
    ">=87": 0.05
  },
  "observed_max_so_far_f": 83,
  "current_temp_f": 82,
  "forecast_high_f": 84,
  "confidence": "high",
  "main_drivers": [],
  "warnings": []
}
```

## Dynamic Market-Bin Requirement for Future HITL Allocation

The future HITL capital-allocation dashboard must **not** treat the example `probability_bins` above as the trading source of truth.

For allocation and trading decisions, the source of truth is the active Kalshi market snapshot for the selected target date. The dashboard must discover and use the actual available contract bins for that specific market/date.

Examples:

- If the operator selects the May 10 market, allocation must use the active May 10 contract bins.
- If the operator selects the May 12 market, allocation must use the active May 12 contract bins.
- If a future market uses different interval widths or boundary values, the allocation table must reflect those live contract bins.

The model may keep an internal forecast distribution over temperature, but the final displayed/actionable bins must be derived from the live market contracts. Fixed bins such as `<=79`, `80-81`, `82-83`, `84-85`, `86-87`, and `>=88` may be used only as a fallback display format or testing fixture when no active market snapshot is available. They must not override the real market contract structure.

Recommended future schema for allocation-ready bins:

```json
{
  "target_date": "YYYY-MM-DD",
  "market_source": "kalshi_snapshot",
  "market_bins": [
    {
      "ticker": "...",
      "market_title": "...",
      "bin_label": "84-85",
      "low_f": 84,
      "high_f": 85,
      "inclusive_low": true,
      "inclusive_high": true,
      "yes_bid": 0.41,
      "yes_ask": 0.45,
      "last_price": 0.43,
      "model_probability": 0.34,
      "market_probability": 0.45,
      "edge": -0.11
    }
  ],
  "warnings": []
}
```

Acceptance criteria for the future HITL dashboard:

1. The operator can select a target market date.
2. The dashboard loads active contracts for that selected date.
3. The allocation table rows match the actual available contract bins for that selected date.
4. Forecast probability mass is integrated/mapped into those actual contract intervals.
5. Any contract whose bin cannot be parsed is shown in a warning table and excluded from buy recommendations.
6. If no live market snapshot is available, the dashboard may show fallback bins, but must label them as fallback/non-actionable.

## How to Generate Reports

```python
from backend.src.dashboard.report_generator import KMIAForecastReport

# Initialize with data
data = { ... }
report = KMIAForecastReport(data)

# Save as HTML
with open("forecast_report.html", "w") as f:
    f.write(report.to_html())

# Save as Markdown
with open("forecast_report.md", "w") as f:
    f.write(report.to_markdown())
```

## Future Considerations

- **Streamlit Integration**: If interactive features or real-time plotting are required, this module can be easily wrapped in a Streamlit app.
- **Automated Email/Slack**: The HTML output is self-contained and suitable for automated delivery.

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

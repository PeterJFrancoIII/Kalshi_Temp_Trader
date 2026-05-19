import os
from typing import Dict, List, Any
from datetime import datetime

from shared.types import REQUIRED_BINS as CANONICAL_REQUIRED_BINS


class KMIAForecastReport:
    """Generates Python-based reports for KMIA temperature forecasts."""

    REQUIRED_BINS = CANONICAL_REQUIRED_BINS

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self._validate_data()

    def _validate_data(self):
        """Ensures the data has all required fields."""
        required_fields = [
            "station", "date", "best_single_number_f", 
            "probability_bins", "observed_max_so_far_f", 
            "current_temp_f", "confidence"
        ]
        for field in required_fields:
            if field not in self.data:
                raise ValueError(f"Missing required field: {field}")
        
        # Verify bins
        for bin_name in self.REQUIRED_BINS:
            if bin_name not in self.data["probability_bins"]:
                raise ValueError(f"Missing required bin: {bin_name}")

    def to_markdown(self) -> str:
        """Generates a Markdown version of the report."""
        d = self.data
        md = []
        md.append(f"# KMIA Forecast Report — {d['date']}")
        md.append(f"**Station:** {d['station']}")
        md.append(f"**Model Version:** {d.get('model_version', 'rules_v1')}")
        md.append(f"**Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        md.append("## Core Estimates")
        md.append(f"- **Best Single-Number Estimate:** {d['best_single_number_f']}°F")
        md.append(f"- **Confidence:** {d['confidence'].upper()}")
        md.append(f"- **Forecast High:** {d.get('forecast_high_f', 'N/A')}°F\n")
        
        md.append("## Live Observations")
        md.append(f"- **Current Temperature:** {d['current_temp_f']}°F")
        md.append(f"- **Observed Max So Far:** {d['observed_max_so_far_f']}°F\n")
        
        md.append("## Probability Bins")
        md.append("| Bin | Probability |")
        md.append("| :--- | :--- |")
        for bin_name in self.REQUIRED_BINS:
            prob = d["probability_bins"][bin_name]
            md.append(f"| {bin_name} | {prob * 100:.1f}% |")
        md.append("")
        
        if d.get("main_drivers"):
            md.append("## Main Drivers")
            for driver in d["main_drivers"]:
                md.append(f"- {driver}")
            md.append("")
            
        if d.get("warnings"):
            md.append("## Warnings")
            for warning in d["warnings"]:
                md.append(f"- ⚠️ {warning}")
            md.append("")
            
        return "\n".join(md)

    def to_html(self) -> str:
        """Generates a simple HTML version of the report."""
        d = self.data
        bins_html = "".join([
            f"<tr><td>{b}</td><td>{d['probability_bins'][b]*100:.1f}%</td></tr>"
            for b in self.REQUIRED_BINS
        ])
        
        drivers_html = "".join([f"<li>{dr}</li>" for dr in d.get("main_drivers", [])])
        warnings_html = "".join([f"<li>⚠️ {w}</li>" for w in d.get("warnings", [])])

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>KMIA Forecast - {d['date']}</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 20px auto; padding: 20px; color: #333; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; }}
        .metric-box {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .metric {{ background: #f8f9fa; padding: 15px; border-radius: 8px; flex: 1; border: 1px solid #dee2e6; }}
        .metric h3 {{ margin: 0 0 10px 0; font-size: 14px; color: #6c757d; text-transform: uppercase; }}
        .value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; }}
        .warning {{ color: #d9534f; list-style: none; }}
    </style>
</head>
<body>
    <h1>KMIA Forecast Dashboard</h1>
    <p><strong>Date:</strong> {d['date']} | <strong>Station:</strong> {d['station']} | <strong>Model:</strong> {d.get('model_version', 'rules_v1')}</p>
    
    <div class="metric-box">
        <div class="metric">
            <h3>Best Estimate</h3>
            <div class="value">{d['best_single_number_f']}°F</div>
        </div>
        <div class="metric">
            <h3>Confidence</h3>
            <div class="value">{d['confidence'].upper()}</div>
        </div>
        <div class="metric">
            <h3>Observed Max</h3>
            <div class="value">{d['observed_max_so_far_f']}°F</div>
        </div>
    </div>

    <h2>Probability Bins</h2>
    <table>
        <thead><tr><th>Bin</th><th>Probability</th></tr></thead>
        <tbody>{bins_html}</tbody>
    </table>

    <div style="display: flex; gap: 40px; margin-top: 30px;">
        <div style="flex: 1;">
            <h3>Main Drivers</h3>
            <ul>{drivers_html}</ul>
        </div>
        <div style="flex: 1;">
            <h3>Warnings</h3>
            <ul class="warning">{warnings_html}</ul>
        </div>
    </div>
    
    <p style="font-size: 12px; color: #999; margin-top: 50px; text-align: center;">
        Generated by KMIA Forecast System | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</body>
</html>
"""
        return html

class ModelComparisonReport:
    """Generates reports comparing two different forecast models."""

    REQUIRED_BINS = CANONICAL_REQUIRED_BINS

    def __init__(self, v1_data: Dict[str, Any], v2_data: Dict[str, Any]):
        self.v1 = v1_data
        self.v2 = v2_data

    def to_markdown(self) -> str:
        md = []
        md.append(f"# Model Comparison Report — {self.v1['date']}")
        md.append(f"**Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        md.append("## Summary Comparison")
        md.append("| Metric | Rules v1 | Rules v2 | Difference |")
        md.append("| :--- | :--- | :--- | :--- |")
        md.append(f"| Best Estimate | {self.v1['best_single_number_f']}°F | {self.v2['best_single_number_f']}°F | {self.v2['best_single_number_f'] - self.v1['best_single_number_f']}°F |")
        
        v1_peak = max(self.v1['probability_bins'], key=self.v1['probability_bins'].get)
        v2_peak = max(self.v2['probability_bins'], key=self.v2['probability_bins'].get)
        md.append(f"| Top Bin | {v1_peak} | {v2_peak} | {'SAME' if v1_peak == v2_peak else 'DIFF'} |")
        md.append("")
        
        md.append("## Probability Distributions")
        md.append("| Bin | Rules v1 | Rules v2 | Abs Diff |")
        md.append("| :--- | :--- | :--- | :--- |")
        for b in self.REQUIRED_BINS:
            p1 = self.v1['probability_bins'][b]
            p2 = self.v2['probability_bins'][b]
            diff = abs(p2 - p1)
            md.append(f"| {b} | {p1*100:.1f}% | {p2*100:.1f}% | {diff*100:.1f}% |")
        md.append("")
        
        return "\n".join(md)

    def to_html(self) -> str:
        v1_peak = max(self.v1['probability_bins'], key=self.v1['probability_bins'].get)
        v2_peak = max(self.v2['probability_bins'], key=self.v2['probability_bins'].get)
        
        rows_html = "".join([
            f"<tr><td>{b}</td><td>{self.v1['probability_bins'][b]*100:.1f}%</td><td>{self.v2['probability_bins'][b]*100:.1f}%</td><td>{abs(self.v2['probability_bins'][b]-self.v1['probability_bins'][b])*100:.1f}%</td></tr>"
            for b in self.REQUIRED_BINS
        ])

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Model Comparison - {self.v1['date']}</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; max-width: 900px; margin: 20px auto; padding: 20px; color: #333; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; }}
        .highlight {{ font-weight: bold; color: #007bff; }}
    </style>
</head>
<body>
    <h1>KMIA Model Comparison</h1>
    <p><strong>Date:</strong> {self.v1['date']} | <strong>Station:</strong> {self.v1['station']}</p>
    
    <h2>Side-by-Side Summary</h2>
    <table>
        <thead>
            <tr><th>Metric</th><th>Rules v1</th><th>Rules v2 (Climatology)</th></tr>
        </thead>
        <tbody>
            <tr><td>Best Estimate</td><td>{self.v1['best_single_number_f']}°F</td><td>{self.v2['best_single_number_f']}°F</td></tr>
            <tr><td>Top Bin</td><td>{v1_peak}</td><td>{v2_peak}</td></tr>
            <tr><td>Confidence</td><td>{self.v1['confidence'].upper()}</td><td>{self.v2['confidence'].upper()}</td></tr>
        </tbody>
    </table>

    <h2>Probability Distributions</h2>
    <table>
        <thead>
            <tr><th>Bin</th><th>Rules v1</th><th>Rules v2</th><th>Abs Diff</th></tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <p style="font-size: 12px; color: #999; margin-top: 50px; text-align: center;">
        Generated by KMIA Forecast System | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</body>
</html>
"""
        return html

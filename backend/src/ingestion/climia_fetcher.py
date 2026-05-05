import os
import requests
from datetime import datetime

NWS_CLIMIA_URL = "https://forecast.weather.gov/product.php?site=MFL&issuedby=MIA&product=CLI&format=txt&version=1&glossary=0"

def fetch_climia_report(url: str = NWS_CLIMIA_URL, save_raw: bool = True) -> str:
    """
    Fetches the latest CLIMIA report from the NWS website using requests.
    """
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 KalshiWeatherBot/1.0'}, timeout=10)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        raise RuntimeError(f"Failed to fetch CLIMIA report: {e}")
        
    # NWS text products usually have the raw text inside a <pre> tag.
    # Let's extract everything inside the first <pre> block.
    # If no <pre> tag, just return the raw text.
    start_idx = html_content.find("<pre")
    if start_idx != -1:
        start_idx = html_content.find(">", start_idx) + 1
        end_idx = html_content.find("</pre>", start_idx)
        raw_text = html_content[start_idx:end_idx].strip()
    else:
        # Fallback if no <pre> block is found (e.g., format=txt actually returns plain text)
        raw_text = html_content.strip()
        
    if save_raw:
        # Determine paths
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        raw_dir = os.path.join(base_dir, "data", "samples", "climia")
        os.makedirs(raw_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(raw_dir, f"climia_raw_{timestamp}.txt")
        with open(filepath, "w") as f:
            f.write(raw_text)
            
    return raw_text

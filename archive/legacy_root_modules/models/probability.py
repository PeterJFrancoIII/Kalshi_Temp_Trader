from typing import Dict
from scipy.stats import norm

class ProbabilityModel:
    """Handles the probability distribution logic and the Zeroing Rule for Kalshi bins."""
    
    def __init__(self):
        # Kalshi Bins: <=78, 79-80, 81-82, 83-84, 85-86, >=87
        self.bins = [
            {"name": "<=78", "upper": 78.5},
            {"name": "79-80", "upper": 80.5},
            {"name": "81-82", "upper": 82.5},
            {"name": "83-84", "upper": 84.5},
            {"name": "85-86", "upper": 86.5},
            {"name": ">=87", "upper": float('inf')}
        ]
        
    def generate_probabilities(self, forecast_mean: float, std_dev: float, observed_max_so_far: float) -> Dict[str, float]:
        """
        Generates probability bins enforcing the rule that any bin strictly below
        the observed_max_so_far receives exactly 0.0 probability.
        """
        # 1. Truncate the distribution base
        effective_mean = max(forecast_mean, observed_max_so_far)
        
        raw_probs = []
        prev_cdf = 0.0
        
        for b in self.bins:
            if b["upper"] == float('inf'):
                prob = 1.0 - prev_cdf
            else:
                prob = norm.cdf(b["upper"], loc=effective_mean, scale=std_dev) - prev_cdf
                
            raw_probs.append(prob)
            prev_cdf += prob
            
        # 2. Apply Zeroing Rule strictly
        bin_probs = {}
        for i, b in enumerate(self.bins):
            # If the top of the bin is less than the observed max, it's impossible to settle here.
            # E.g., if max_so_far = 81, bin <=78 (upper 78.5) is impossible. 
            # bin 79-80 (upper 80.5) is impossible.
            if b["upper"] < observed_max_so_far:
                bin_probs[b["name"]] = 0.0
            else:
                bin_probs[b["name"]] = max(0.0, raw_probs[i])
                
        # 3. Normalize remaining probabilities to 1.0
        total_valid_prob = sum(bin_probs.values())
        if total_valid_prob > 0:
            for k in bin_probs:
                bin_probs[k] = round(bin_probs[k] / total_valid_prob, 4)
        else:
            # Failsafe if something goes mathematically wrong, dump it into the highest possible bin
            for k in bin_probs:
                bin_probs[k] = 0.0
            bin_probs[">=" + str(int(observed_max_so_far))] = 1.0 # Pseudo-handling
            
        return bin_probs

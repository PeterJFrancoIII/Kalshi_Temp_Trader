def calculate_implied_probability(yes_ask: int) -> float:
    """
    Calculates the implied probability from the yes_ask price (in cents).
    """
    return round(yes_ask / 100.0, 4)

def calculate_edge(model_prob: float, implied_prob: float) -> float:
    """
    Calculates the raw edge before fees.
    """
    return round(model_prob - implied_prob, 4)

def calculate_kalshi_fee(price: float) -> float:
    """
    Calculates the Kalshi taker fee in probability terms (0 to 1).
    Formula: 0.07 * price * (1 - price)
    """
    return round(0.07 * price * (1.0 - price), 4)

def calculate_edge_after_fees(edge: float, fee: float) -> float:
    """
    Calculates the edge after deducting fees.
    """
    return round(edge - fee, 4)

def calculate_confidence_adjusted_edge(edge: float, confidence: str) -> float:
    """
    Adjusts the edge based on model confidence.
    """
    confidence = confidence.lower()
    if confidence == "high":
        return round(edge * 1.0, 4)
    elif confidence == "medium":
        return round(edge * 0.5, 4)
    elif confidence == "low":
        return round(edge * 0.1, 4)
    return 0.0

from enum import Enum
from typing import Dict, List
from dataclasses import dataclass, field

class Action(str, Enum):
    WATCH = "WATCH"
    TRADE_CANDIDATE = "TRADE_CANDIDATE"
    REJECT = "REJECT"

@dataclass
class MarketSnapshot:
    bin_name: str
    yes_ask: int  # in cents, e.g., 45 for 45 cents
    yes_bid: int
    liquidity: int  # number of contracts available at the ask
    market_ts: int  # timestamp of the market data

@dataclass
class RecommendationInput:
    station: str
    date: str
    model_probabilities: Dict[str, float]
    confidence: str
    prediction_ts: int  # timestamp of the prediction
    market_snapshots: List[MarketSnapshot]

@dataclass
class Recommendation:
    bin_name: str
    action: Action
    reason: str
    model_probability: float
    market_ask_probability: float
    edge_before_fees: float
    edge_after_fees: float
    confidence_adjusted_edge: float
    spread: float
    estimated_fee: float

@dataclass
class RecommendationResult:
    station: str
    date: str
    recommendations: List[Recommendation]

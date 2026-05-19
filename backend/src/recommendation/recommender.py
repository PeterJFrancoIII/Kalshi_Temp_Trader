import time
from typing import List, Set
from .types import RecommendationInput, RecommendationResult, Recommendation, Action
from . import ev
from . import gates

VALID_BINS: Set[str] = {"<=78", "79-80", "81-82", "83-84", "85-86", ">=87"}

def generate_recommendations(
    input_data: RecommendationInput,
    current_ts: int = None,
    max_data_age_seconds: int = 300,
    max_spread_cents: int = 10,
    min_liquidity: int = 10,
    min_trade_edge: float = 0.05
) -> RecommendationResult:
    """
    Evaluates market snapshots against model probabilities to generate trading recommendations.
    """
    if current_ts is None:
        current_ts = int(time.time())
        
    recommendations: List[Recommendation] = []
    
    # Check prediction confidence at the top level
    conf_ok, conf_reason = gates.check_confidence(input_data.confidence)
    
    for snapshot in input_data.market_snapshots:
        # Initial defaults
        action = Action.WATCH
        reason = ""
        
        # Mapping check
        mapping_ok, mapping_reason = gates.check_market_mapping(snapshot.bin_name, VALID_BINS)
        
        # EV calculations (math lives in trading.edge_engine; see recommendation.ev)
        model_prob = input_data.model_probabilities.get(snapshot.bin_name, 0.0)
        market_ask_prob = ev.calculate_implied_probability(snapshot.yes_ask)
        edge_before_fees = ev.calculate_edge(model_prob, market_ask_prob)

        estimated_fee = ev.calculate_kalshi_fee(market_ask_prob)
        edge_after_fees = ev.calculate_edge_after_fees(edge_before_fees, estimated_fee)
        
        adj_edge = ev.calculate_confidence_adjusted_edge(edge_after_fees, input_data.confidence)
        spread = round((snapshot.yes_ask - snapshot.yes_bid) / 100.0, 4)
        
        # Construct base recommendation
        rec = Recommendation(
            bin_name=snapshot.bin_name,
            action=action,
            reason=reason,
            model_probability=model_prob,
            market_ask_probability=market_ask_prob,
            edge_before_fees=edge_before_fees,
            edge_after_fees=edge_after_fees,
            confidence_adjusted_edge=adj_edge,
            spread=spread,
            estimated_fee=estimated_fee
        )
        
        # Apply sequential gates
        if not mapping_ok:
            rec.action = Action.REJECT
            rec.reason = mapping_reason
            recommendations.append(rec)
            continue
            
        if not conf_ok:
            rec.action = Action.REJECT
            rec.reason = conf_reason
            recommendations.append(rec)
            continue
            
        stale_ok, stale_reason = gates.check_data_staleness(
            input_data.prediction_ts, snapshot.market_ts, current_ts, max_data_age_seconds
        )
        if not stale_ok:
            rec.action = Action.REJECT
            rec.reason = stale_reason
            recommendations.append(rec)
            continue
            
        spread_ok, spread_reason = gates.check_spread(snapshot.yes_ask, snapshot.yes_bid, max_spread_cents)
        if not spread_ok:
            rec.action = Action.REJECT
            rec.reason = spread_reason
            recommendations.append(rec)
            continue
            
        liq_ok, liq_reason = gates.check_liquidity(snapshot.liquidity, min_liquidity)
        if not liq_ok:
            rec.action = Action.REJECT
            rec.reason = liq_reason
            recommendations.append(rec)
            continue
            
        if edge_after_fees <= 0:
            rec.action = Action.REJECT
            rec.reason = f"No positive edge after fees: {edge_after_fees:.4f}"
            recommendations.append(rec)
            continue
            
        # If we reach here, it's at least a WATCH. Let's check for TRADE_CANDIDATE
        trade_ok, trade_reason = gates.check_edge_threshold(edge_after_fees, min_trade_edge)
        if trade_ok:
            rec.action = Action.TRADE_CANDIDATE
            rec.reason = "Passes all gates and meets edge threshold"
        else:
            rec.action = Action.WATCH
            rec.reason = f"Positive edge but below threshold ({edge_after_fees:.4f} < {min_trade_edge:.4f})"
            
        recommendations.append(rec)
        
    return RecommendationResult(
        station=input_data.station,
        date=input_data.date,
        recommendations=recommendations
    )

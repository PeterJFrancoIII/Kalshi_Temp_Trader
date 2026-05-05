import time
import os
import uuid
from datetime import datetime, date
from recommendation.types import RecommendationInput, MarketSnapshot, Action
from recommendation.recommender import generate_recommendations
from recommendation.ev import calculate_implied_probability, calculate_kalshi_fee
from calibration.metrics import score_prediction
from forecasting.bin_converter import temp_to_bin
from paper_trading.persistence import save_recommendation, load_recommendations
from paper_trading.simulator import simulate_fill_from_snapshot, settle_paper_trade

def test_full_pipeline_dry_run():
    """
    End-to-end dry-run:
    - observed_max_so_far_f = 82
    - forecast bins (heuristic centered at 83-84)
    - mock Kalshi market for 81-82
    - run recommendation
    - verify valid WATCH/TRADE_CANDIDATE/REJECT output
    """
    current_ts = int(time.time())
    
    # 1. Forecast bins (manually constructed for test)
    # If observed max is 82, <=78 and 79-80 must be 0.
    model_probs = {
        "<=78": 0.0,
        "79-80": 0.0,
        "81-82": 0.2,
        "83-84": 0.6,
        "85-86": 0.15,
        ">=87": 0.05
    }
    
    # 2. Mock Kalshi market for 83-84
    # Let's say model says 60%, and market says 45 cents.
    # Edge = 0.60 - 0.45 = 0.15
    # Fee at 0.45 = 0.07 * 0.45 * 0.55 = 0.0173
    # Edge after fees = 0.15 - 0.0173 = 0.1327 (Passes 0.05 threshold)
    
    snapshot_83_84 = MarketSnapshot(
        bin_name="83-84",
        yes_ask=45,
        yes_bid=40,
        liquidity=100,
        market_ts=current_ts - 60
    )
    
    input_data = RecommendationInput(
        station="KMIA",
        date=date(2026, 5, 3),
        model_probabilities=model_probs,
        confidence="high",
        prediction_ts=current_ts - 120,
        market_snapshots=[snapshot_83_84]
    )
    
    result = generate_recommendations(input_data, current_ts=current_ts)
    
    assert len(result.recommendations) == 1
    rec = result.recommendations[0]
    assert rec.bin_name == "83-84"
    assert rec.action == Action.TRADE_CANDIDATE
    assert "Passes all gates" in rec.reason
    
    # 3. Verify no order placement (implicitly checked by verifying recommendation object content)
    # and ensuring Action is as expected.

def test_unit_consistency():
    """
    Unit consistency:
    - Kalshi ask price 55 cents becomes 0.55
    - fee at 0.50 is 0.0175
    - fee at 0.55 is 0.07 * 0.55 * 0.45
    """
    # Price to probability
    assert calculate_implied_probability(55) == 0.55
    
    # Fee at 0.50
    fee_50 = calculate_kalshi_fee(0.50)
    assert fee_50 == 0.0175 # 0.07 * 0.5 * 0.5 = 0.0175
    
    # Fee at 0.55
    fee_55 = calculate_kalshi_fee(0.55)
    expected_55 = round(0.07 * 0.55 * 0.45, 4)
    assert fee_55 == expected_55

def test_safety_rejections():
    """
    Safety:
    - uncertain mapping rejects
    - invalid bins reject
    - wide spread rejects
    - missing depth rejects
    """
    current_ts = int(time.time())
    model_probs = {b: 1/6 for b in ["<=78", "79-80", "81-82", "83-84", "85-86", ">=87"]}
    
    # Wide Spread (15c > 10c limit)
    snapshot_wide = MarketSnapshot(
        bin_name="81-82",
        yes_ask=55,
        yes_bid=40,
        liquidity=100,
        market_ts=current_ts
    )
    
    # Low Liquidity (5 < 10 limit)
    snapshot_low_liq = MarketSnapshot(
        bin_name="81-82",
        yes_ask=42,
        yes_bid=40,
        liquidity=5,
        market_ts=current_ts
    )
    
    # Uncertain Mapping
    snapshot_uncertain = MarketSnapshot(
        bin_name="UNKNOWN",
        yes_ask=42,
        yes_bid=40,
        liquidity=100,
        market_ts=current_ts
    )
    
    input_data = RecommendationInput(
        station="KMIA",
        date=date(2026, 5, 3),
        model_probabilities=model_probs,
        confidence="high",
        prediction_ts=current_ts,
        market_snapshots=[snapshot_wide, snapshot_low_liq, snapshot_uncertain]
    )
    
    result = generate_recommendations(input_data, current_ts=current_ts)
    
    recs = {r.bin_name: r for r in result.recommendations}
    
    assert recs["81-82"].action == Action.REJECT
    assert "Spread too wide" in recs["81-82"].reason or "Liquidity too low" in recs["81-82"].reason
    
    # Wait, the snapshots for 81-82 are processed sequentially.
    # The first one is wide spread.
    # The second one is low liq.
    
    assert result.recommendations[0].bin_name == "81-82"
    assert result.recommendations[0].action == Action.REJECT
    assert "Spread too wide" in result.recommendations[0].reason
    
    assert result.recommendations[1].bin_name == "81-82"
    assert result.recommendations[1].action == Action.REJECT
    assert "Liquidity too low" in result.recommendations[1].reason
    
    assert result.recommendations[2].bin_name == "UNKNOWN"
    assert result.recommendations[2].action == Action.REJECT
    assert "Uncertain market mapping" in result.recommendations[2].reason

def test_settlement_consistency():
    """
    Settlement:
    - final high 82 scores actual_bin = 81-82
    """
    model_probs = {
        "<=78": 0.05,
        "79-80": 0.15,
        "81-82": 0.50,
        "83-84": 0.20,
        "85-86": 0.05,
        ">=87": 0.05
    }
    
    score = score_prediction(model_probs, 82)
    assert score["actual_bin"] == "81-82"
    assert score["top_bin_hit"] is True
    
    score_78 = score_prediction(model_probs, 78)
    assert score_78["actual_bin"] == "<=78"
    
    score_87 = score_prediction(model_probs, 87)
    assert score_87["actual_bin"] == ">=87"

def test_full_pipeline_with_paper_trading():
    """
    End-to-end dry-run with paper trading:
    - observed_max_so_far_f = 82
    - forecast bins (heuristic centered at 83-84)
    - mock Kalshi market for 83-84
    - run recommendation
    - persist paper trade candidate
    - settle with final high 82
    - verify scoring and paper PnL
    - verify no real order placement
    """
    current_ts = int(time.time())
    test_storage = "backend/tests/test_pipeline_trades.jsonl"
    if os.path.exists(test_storage):
        os.remove(test_storage)
    
    # 1. Forecast bins
    model_probs = {
        "<=78": 0.0,
        "79-80": 0.0,
        "81-82": 0.2,
        "83-84": 0.6,
        "85-86": 0.15,
        ">=87": 0.05
    }
    
    # 2. Mock Kalshi market for 83-84
    snapshot_83_84 = MarketSnapshot(
        bin_name="83-84",
        yes_ask=45,
        yes_bid=40,
        liquidity=100,
        market_ts=current_ts - 60
    )
    
    input_data = RecommendationInput(
        station="KMIA",
        date=date(2026, 5, 3),
        model_probabilities=model_probs,
        confidence="high",
        prediction_ts=current_ts - 120,
        market_snapshots=[snapshot_83_84]
    )
    
    # 3. Run Recommendation
    result = generate_recommendations(input_data, current_ts=current_ts)
    rec = result.recommendations[0]
    assert rec.action == Action.TRADE_CANDIDATE
    
    # 4. Persist paper trade candidate
    trade_id = str(uuid.uuid4())
    paper_record = {
        "id": trade_id,
        "date": "2026-05-03",
        "target_bin": rec.bin_name,
        "recommendation_action": rec.action.value,
        "simulated_side": "YES",
        "status": "PENDING",
        "created_at": datetime.utcnow().isoformat()
    }
    save_recommendation(paper_record, path=test_storage)
    
    # 5. Simulate Fill
    market_raw = {
        "ticker": "KMIA-T83-84",
        "yes_ask": 45,
        "no_ask": 56,
        "liquidity": 100
    }
    filled_record = simulate_fill_from_snapshot(paper_record, market_raw)
    assert filled_record["status"] == "FILLED"
    assert filled_record["entry_price"] == 45
    
    # 6. Settle with final high 82 (This trade on 83-84 should LOSE)
    settled_record = settle_paper_trade(filled_record, actual_high=82)
    assert settled_record["status"] == "SETTLED"
    assert settled_record["settlement_result"] == "LOSS"
    assert settled_record["net_pnl"] == -45
    
    # 7. Verify scoring logic (for the same outcome)
    score = score_prediction(model_probs, 82)
    assert score["actual_bin"] == "81-82"
    assert score["top_bin_hit"] is False # Top was 83-84
    
    if os.path.exists(test_storage):
        os.remove(test_storage)

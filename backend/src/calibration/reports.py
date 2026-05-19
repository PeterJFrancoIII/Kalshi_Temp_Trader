from typing import Dict, Any
from sqlalchemy.orm import Session
from db.models import (
    DailyPredictionRecord,
    ClimiaReportRecord,
    Settlement,
    CalibrationMetric,
)
from calibration.metrics import score_prediction

def process_settlements_for_date(db: Session, date_str: str) -> int:
    """
    Finds a CLIMIA report for the date, settles all daily predictions for that date,
    computes metrics, and saves them to the DB.
    Returns the number of settled predictions.
    """
    climia = (
        db.query(ClimiaReportRecord)
        .filter(ClimiaReportRecord.date == date_str)
        .order_by(ClimiaReportRecord.id.desc())
        .first()
    )
    if not climia or climia.max_temp_f is None:
        return 0

    predictions = (
        db.query(DailyPredictionRecord)
        .filter(DailyPredictionRecord.date == date_str)
        .outerjoin(Settlement)
        .filter(Settlement.id == None)
        .all()
    )
    
    settled_count = 0
    actual_temp = climia.max_temp_f
    
    for pred in predictions:
        # Build probabilities dict
        probs = {
            "<=78": pred.prob_le_78,
            "79-80": pred.prob_79_80,
            "81-82": pred.prob_81_82,
            "83-84": pred.prob_83_84,
            "85-86": pred.prob_85_86,
            ">=87": pred.prob_ge_87
        }
        
        # Compute metrics
        metrics_data = score_prediction(probs, actual_temp)
        
        # Create Settlement
        settlement = Settlement(
            prediction_id=pred.id,
            climia_report_id=climia.id,
            date=date_str,
            actual_high_f=actual_temp,
            actual_bin=metrics_data["actual_bin"]
        )
        db.add(settlement)
        db.flush() # to get settlement.id
        
        metric = CalibrationMetric(
            settlement_id=settlement.id,
            brier_score=metrics_data["brier_score"],
            log_loss=metrics_data["log_loss"],
            absolute_error=abs(pred.best_single_number_f - actual_temp),
            top_predicted_bin=metrics_data["top_predicted_bin"],
            winning_bin=metrics_data["actual_bin"],
            top_bin_hit=metrics_data["top_bin_hit"]
        )
        db.add(metric)
        settled_count += 1
        
    db.commit()
    return settled_count

def generate_calibration_summary(db: Session, station: str = "KMIA") -> Dict[str, Any]:
    """
    Fetch all calibration metrics for a station and calculate aggregate stats.
    """
    from calibration.metrics import calculate_aggregate_stats
    
    metrics = (
        db.query(CalibrationMetric)
        .join(Settlement)
        .join(DailyPredictionRecord)
        .filter(DailyPredictionRecord.station == station)
        .all()
    )
    
    if not metrics:
        return {}
        
    metrics_data = [
        {
            "brier_score": m.brier_score,
            "log_loss": m.log_loss,
            "top_bin_hit": m.top_bin_hit
        }
        for m in metrics
    ]
    
    return calculate_aggregate_stats(metrics_data)

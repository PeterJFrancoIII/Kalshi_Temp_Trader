import argparse
import logging
import os
import json
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, List
from dateutil import tz

# Standard entrypoint: `python -m scheduler.run_daily_prediction` with
# PYTHONPATH=backend/src (see scripts/run_daily_prediction.sh). The DB layer
# is optional; absent SQLAlchemy install or DB config, dry-run mode still works.
try:
    from db.session import SessionLocal, init_db
    from db.models import (
        LiveObservation,
        ForecastSnapshot,
        WeatherSnapshotRecord,
        DailyPredictionRecord,
        ValidationStatus,
        ClimiaReportRecord,
    )
except ImportError:
    SessionLocal = None
    init_db = lambda: None
    LiveObservation = None
    ForecastSnapshot = None
    WeatherSnapshotRecord = None
    DailyPredictionRecord = None
    ValidationStatus = None
    ClimiaReportRecord = None

from features.pipeline_inputs import build_dry_run_features
from forecasting.rules_model import forecast_daily_high_bins, validate_probability_bins
from forecasting.rules_model_v2 import forecast_daily_high_bins_v2
from dashboard.report_generator import KMIAForecastReport

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed/reports/"))
HISTORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed/history/kmia_daily_history.jsonl"))

def load_history_records() -> List[Dict[str, Any]]:
    """Loads historical records from JSONL file for v2 climatology."""
    records = []
    logger.info(f"History path resolved to: {HISTORY_FILE}")
    logger.info(f"History file exists: {os.path.exists(HISTORY_FILE)}")
    if not os.path.exists(HISTORY_FILE):
        logger.warning(f"History file missing at {HISTORY_FILE}. Model v2 will use fallback behavior.")
        return records

    try:
        with open(HISTORY_FILE, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        logger.info(f"Loaded {len(records)} historical records for v2 integration.")
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
    return records

def save_reports(prediction_data: Dict[str, Any], report_dir: str):
    """Generates and saves Markdown and HTML reports."""
    os.makedirs(report_dir, exist_ok=True)
    
    report = KMIAForecastReport(prediction_data)
    
    date_str = prediction_data["date"]
    model_ver = prediction_data.get("model_version", "v1")
    timestamp = datetime.now().strftime("%H%M%S")
    base_filename = f"kmia_forecast_{date_str}_{model_ver}_{timestamp}"
    
    # Markdown
    md_content = report.to_markdown()
    md_path = os.path.join(report_dir, f"{base_filename}.md")
    with open(md_path, "w") as f:
        f.write(md_content)
    
    # HTML
    html_content = report.to_html()
    html_path = os.path.join(report_dir, f"{base_filename}.html")
    with open(html_path, "w") as f:
        f.write(html_content)
    
    # JSON (added for risk engine and signal generator compliance)
    json_data = prediction_data.copy()
    if "generated_at_utc" not in json_data:
        json_data["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    
    json_path = os.path.join(report_dir, f"{base_filename}.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    
    logger.info(f"Reports saved to {report_dir}")
    logger.info(f"  MD: {os.path.basename(md_path)}")
    logger.info(f"  HTML: {os.path.basename(html_path)}")
    logger.info(f"  JSON: {os.path.basename(json_path)}")
    
    return md_path, html_path, json_path

def run_prediction_pipeline(
    target_date: Optional[date] = None, 
    force: bool = False, 
    dry_run: bool = False,
    model_name: str = "rules_v2_climatology",
    compare_models: bool = False
):
    """
    Orchestrates a single prediction run.
    1. Fetches latest data (or uses mocks if dry_run).
    2. Runs forecasting model(s).
    3. Validates output.
    4. Generates and saves reports.
    5. Saves results to DB (if not dry_run).
    """
    if target_date is None:
        target_date = datetime.now().date()
    
    logger.info(f"Starting prediction pipeline for {target_date} (Dry Run: {dry_run}, Model: {model_name}, Compare: {compare_models})...")
    
    if dry_run:
        features = build_dry_run_features(target_date)
        logger.info(
            "Dry-run features: forecast_high_f=%s, observed_max=%s, current_temp=%s",
            features["forecast_high_f"],
            features["observed_max_so_far_f"],
            features["current_temp_f"],
        )
    else:
        if SessionLocal is None:
            logger.error("Database session not available. Use --dry-run for testing.")
            return

        db = SessionLocal()
        try:
            # Idempotency Check
            from sqlalchemy import desc
            if not force:
                recent_prediction = (
                    db.query(DailyPredictionRecord)
                    .filter(
                        DailyPredictionRecord.date == target_date.isoformat(),
                        DailyPredictionRecord.model_version == model_name,
                    )
                    .order_by(desc(DailyPredictionRecord.created_at))
                    .first()
                )
                
                if recent_prediction:
                    time_since = datetime.now() - recent_prediction.created_at
                    if time_since.total_seconds() < 900: # 15 minutes
                        logger.warning(f"Recent {model_name} prediction for {target_date} found. Skipping.")
                        return
            
            # Fetch Latest Data
            latest_obs = db.query(LiveObservation).filter(
                LiveObservation.station == "KMIA"
            ).order_by(desc(LiveObservation.timestamp)).first()
            
            if not latest_obs:
                logger.error("No live observations found in DB.")
                return
                
            latest_forecast = db.query(ForecastSnapshot).filter(
                ForecastSnapshot.date == target_date.isoformat(),
                ForecastSnapshot.station == "KMIA"
            ).order_by(desc(ForecastSnapshot.fetched_at)).first()
            
            latest_climia = (
                db.query(ClimiaReportRecord)
                .filter(ClimiaReportRecord.station == "KMIA")
                .order_by(desc(ClimiaReportRecord.fetched_at))
                .first()
            )

            # Fetch recent observations (limit 20) for RH tie-breaker logic
            recent_obs = db.query(LiveObservation).filter(
                LiveObservation.station == "KMIA"
            ).order_by(desc(LiveObservation.timestamp)).limit(20).all()
            
            recent_obs_list = []
            for obs in recent_obs:
                recent_obs_list.append({
                    "timestamp": obs.timestamp.isoformat() if obs.timestamp else None,
                    "temperature_f": obs.temperature_f,
                    "observed_max_so_far_f": obs.observed_max_so_far_f,
                    "dewpoint_f": obs.dewpoint_f,
                    "wind_direction": obs.wind_direction,
                    "wind_speed_mph": obs.wind_speed_mph,
                    "rain_flag": obs.rain_flag,
                    "thunderstorm_flag": obs.thunderstorm_flag,
                    "overcast_flag": obs.overcast_flag,
                })

            features = {
                "observed_max_so_far_f": int(latest_obs.observed_max_so_far_f),
                "current_temp_f": int(latest_obs.temperature_f),
                "forecast_high_f": int(latest_forecast.forecast_high_f) if latest_forecast else 85,
                "normal_high_f": latest_climia.normal_high_f if latest_climia else 82,
                "recent_rain_flag": latest_obs.rain_flag,
                "thunderstorm_flag": latest_obs.thunderstorm_flag,
                "overcast_flag": latest_obs.overcast_flag,
                "current_time_et": datetime.now(tz.gettz('US/Eastern')),
                "live_data_stale": (datetime.now(timezone.utc) - latest_obs.timestamp.replace(tzinfo=timezone.utc)).total_seconds() > 3600,
                "target_date": target_date.isoformat(),
                "recent_observations": recent_obs_list
            }
        except Exception as e:
            logger.error(f"Error fetching data from DB: {e}")
            db.close()
            raise e
        finally:
            if not dry_run:
                db.close()

    # Load history for v2 if needed
    history = []
    if model_name == "rules_v2_climatology" or compare_models:
        history = load_history_records()

    # Determine models to run
    models_to_run = []
    if compare_models:
        models_to_run = ["rules_v1", "rules_v2_climatology"]
    else:
        models_to_run = [model_name]

    outputs = []
    for m in models_to_run:
        if m == "rules_v1":
            # Call v1 (original forecast_daily_high_bins)
            # v1 doesn't accept target_date, so we copy and pop
            v1_features = features.copy()
            v1_features.pop("target_date", None)
            out = forecast_daily_high_bins(**v1_features)
            out["model_version"] = "rules_v1"
        else:
            # Call v2
            out = forecast_daily_high_bins_v2(features, history)
            # model_version is already set to rules_v2_climatology in v2
            
        out["date"] = target_date.isoformat()
        validate_probability_bins(out["probability_bins"])
        outputs.append(out)

    # Comparison Logic
    if compare_models and len(outputs) == 2:
        generate_comparison_report(outputs[0], outputs[1], REPORT_DIR)

    # Save reports and DB for the primary model (last one in list if not comparing, or both if needed)
    for out in outputs:
        save_reports(out, REPORT_DIR)
        
        # Save to DB if not dry run
        if not dry_run and SessionLocal is not None:
            save_prediction_to_db(out)

def save_prediction_to_db(prediction_output: Dict[str, Any]):
    """Saves a single prediction to the database."""
    db = SessionLocal()
    try:
        target_date = date.fromisoformat(prediction_output["date"])
        run_id = f"kmia_{target_date.strftime('%Y%m%d')}_{prediction_output['model_version']}_{datetime.now().strftime('%H%M%S')}"
        
        daily_pred = DailyPredictionRecord(
            run_id=run_id,
            date=prediction_output["date"],
            station="KMIA",
            model_version=prediction_output["model_version"],
            best_single_number_f=prediction_output["best_single_number_f"],
            prob_le_78=prediction_output["probability_bins"].get("<=78", 0.0),
            prob_79_80=prediction_output["probability_bins"].get("79-80", 0.0),
            prob_81_82=prediction_output["probability_bins"].get("81-82", 0.0),
            prob_83_84=prediction_output["probability_bins"].get("83-84", 0.0),
            prob_85_86=prediction_output["probability_bins"].get("85-86", 0.0),
            prob_ge_87=prediction_output["probability_bins"].get(">=87", 0.0),
            confidence=prediction_output["confidence"],
            main_drivers=prediction_output["main_drivers"],
            warnings=prediction_output["warnings"],
            status=ValidationStatus.PENDING
        )
        db.add(daily_pred)
        db.commit()
        logger.info(f"Successfully saved {prediction_output['model_version']} prediction to database.")
    except Exception as e:
        logger.error(f"Error saving to DB: {e}")
        db.rollback()
    finally:
        db.close()

def generate_comparison_report(v1_out: Dict[str, Any], v2_out: Dict[str, Any], report_dir: str):
    """Generates a side-by-side comparison report."""
    from dashboard.report_generator import ModelComparisonReport
    os.makedirs(report_dir, exist_ok=True)
    
    comparison = ModelComparisonReport(v1_out, v2_out)
    date_str = v1_out["date"]
    timestamp = datetime.now().strftime("%H%M%S")
    base_filename = f"kmia_comparison_{date_str}_{timestamp}"
    
    md_content = comparison.to_markdown()
    with open(os.path.join(report_dir, f"{base_filename}.md"), "w") as f:
        f.write(md_content)
        
    html_content = comparison.to_html()
    with open(os.path.join(report_dir, f"{base_filename}.html"), "w") as f:
        f.write(html_content)
        
    logger.info(f"Comparison reports saved as {base_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Daily Prediction Pipeline")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--force", action="store_true", help="Force run even if a recent prediction exists")
    parser.add_argument("--dry-run", action="store_true", help="Run with mock data and skip DB storage")
    parser.add_argument("--init-db", action="store_true", help="Initialize database tables")
    parser.add_argument("--model", type=str, choices=["rules_v1", "rules_v2_climatology"], default="rules_v2_climatology", help="Forecast model to use")
    parser.add_argument("--compare-models", action="store_true", help="Run both v1 and v2 and generate comparison")
    
    args = parser.parse_args()
    
    if args.init_db and not args.dry_run:
        logger.info("Initializing database...")
        init_db()
        
    target_dt = None
    if args.date:
        target_dt = datetime.strptime(args.date, "%Y-%m-%d").date()
        
    run_prediction_pipeline(target_dt, args.force, args.dry_run, args.model, args.compare_models)

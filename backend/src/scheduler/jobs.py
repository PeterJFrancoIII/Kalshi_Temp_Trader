import logging
import os
import json
import time
from datetime import datetime, timedelta
import pytz
from sqlalchemy.orm import Session
from ..db.session import SessionLocal
from ..db.models import LiveObservation, ClimiaReport, DailyPrediction, Settlement, CalibrationMetric
from ..ingestion.kmia_live_fetcher import fetch_wrh_timeseries
from ..ingestion.kmia_obhistory_parser import parse_wrh_timeseries
from ..calibration.reports import process_settlements_for_date

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("scheduler")

ET = pytz.timezone('US/Eastern')

def refresh_live_observations():
    """Fetches latest KMIA live data and stores in DB."""
    logger.info("Starting live observation refresh...")
    db = SessionLocal()
    try:
        raw_json = fetch_wrh_timeseries("KMIA")
        if not raw_json:
            logger.error("Failed to fetch WRH timeseries")
            return
            
        parsed_obs = parse_wrh_timeseries(raw_json)
        if not parsed_obs:
            logger.warning("No observations parsed from WRH JSON")
            return
            
        latest = parsed_obs[-1]
        existing = db.query(LiveObservation).filter(LiveObservation.timestamp == latest.timestamp).first()
        if not existing:
            today_start = latest.timestamp.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0)
            today_obs = [o.temperature_f for o in parsed_obs if o.timestamp >= today_start and o.temperature_f is not None]
            observed_max = max(today_obs) if today_obs else latest.temperature_f
            
            new_obs = LiveObservation(
                timestamp=latest.timestamp,
                station="KMIA",
                temperature_f=latest.temperature_f,
                observed_max_so_far_f=observed_max,
                dewpoint_f=latest.dewpoint_f,
                wind_direction=str(latest.wind_direction) if latest.wind_direction else None,
                wind_speed_mph=latest.wind_speed_mph,
                weather_condition=latest.weather_condition,
                rain_flag="rain" in (latest.weather_condition or "").lower(),
                thunderstorm_flag="thunder" in (latest.weather_condition or "").lower(),
                overcast_flag="overcast" in (latest.weather_condition or "").lower()
            )
            db.add(new_obs)
            db.commit()
            logger.info(f"Saved new observation for {latest.timestamp}")
    except Exception as e:
        logger.error(f"Error in refresh_live_observations: {e}")
        db.rollback()
    finally:
        db.close()

def run_midnight_prediction():
    """Triggers the daily prediction logic."""
    logger.info("Running scheduled daily prediction...")
    # Assuming Agent 11 provides a module or script for this
    # For now we'll call the entrypoint script
    try:
        import subprocess
        subprocess.run(["python3", "-m", "src.scheduler.run_daily_prediction"], check=True)
    except Exception as e:
        logger.error(f"Failed to run daily prediction: {e}")

def run_settlement_check():
    """Checks for CLIMIA and settles previous day."""
    logger.info("Checking for settlements...")
    db = SessionLocal()
    try:
        # Check yesterday and today (in case CLIMIA posts early or late)
        yesterday = (datetime.now(ET) - timedelta(days=1)).strftime("%Y-%m-%d")
        today = datetime.now(ET).strftime("%Y-%m-%d")
        
        for date_str in [yesterday, today]:
            count = process_settlements_for_date(db, date_str)
            if count > 0:
                logger.info(f"Settled {count} predictions for {date_str}")
    except Exception as e:
        logger.error(f"Error in settlement check: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KMIA Operations Scheduler")
    parser.add_argument("--loop", action="store_true", help="Run in a loop")
    args = parser.parse_args()

    if args.loop:
        logger.info("Starting scheduler loop...")
        last_live = 0
        last_settle = 0
        last_prediction_date = None
        
        while True:
            now = datetime.now(ET)
            now_ts = now.timestamp()
            
            # Live Refresh every 10 mins
            if now_ts - last_live >= 600:
                refresh_live_observations()
                last_live = now_ts
            
            # Settlement Check every 30 mins
            if now_ts - last_settle >= 1800:
                run_settlement_check()
                last_settle = now_ts
                
            # Midnight Prediction (run once after 00:05 ET)
            today_str = now.strftime("%Y-%m-%d")
            if last_prediction_date != today_str and now.hour == 0 and now.minute >= 5:
                run_midnight_prediction()
                last_prediction_date = today_str
                
            time.sleep(60)
    else:
        # Run one-off if needed
        pass

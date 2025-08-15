from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

from src.prediction_engine import FPLPredictionEngine
from src.data.fpl_api import FPLDataFetcher

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FPLUpdateScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.prediction_engine = FPLPredictionEngine()
        self.fpl_fetcher = FPLDataFetcher()
        
    def update_player_data(self):
        try:
            logger.info("Starting scheduled player data update")
            
            bootstrap_data = self.fpl_fetcher.get_bootstrap_data()
            
            current_gw = None
            for event in bootstrap_data['events']:
                if event['is_current']:
                    current_gw = event['id']
                    break
            
            if current_gw:
                self.prediction_engine.update_with_live_data(current_gw)
            
            predictions = self.prediction_engine.get_player_predictions(horizon_gameweeks=5)
            
            logger.info(f"Updated predictions for {len(predictions)} players")
            
        except Exception as e:
            logger.error(f"Error in scheduled update: {e}")
    
    def retrain_models(self):
        try:
            logger.info("Starting scheduled model retraining")
            
            self.prediction_engine.train_models(force_retrain=True)
            
            logger.info("Model retraining completed")
            
        except Exception as e:
            logger.error(f"Error in model retraining: {e}")
    
    def check_gameweek_deadline(self):
        try:
            bootstrap_data = self.fpl_fetcher.get_bootstrap_data()
            
            for event in bootstrap_data['events']:
                if event['is_next']:
                    deadline = datetime.fromisoformat(event['deadline_time'].replace('Z', '+00:00'))
                    time_until = deadline - datetime.now(deadline.tzinfo)
                    
                    if time_until.total_seconds() < 3600:
                        logger.warning(f"Gameweek {event['id']} deadline in less than 1 hour!")
                        self.send_deadline_notification(event)
                    
                    break
                    
        except Exception as e:
            logger.error(f"Error checking deadline: {e}")
    
    def send_deadline_notification(self, event: dict):
        logger.info(f"Deadline approaching for Gameweek {event['id']}: {event['deadline_time']}")
    
    def start(self):
        self.scheduler.add_job(
            func=self.update_player_data,
            trigger=CronTrigger(hour=1, minute=0),
            id='daily_update',
            name='Daily player data update',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            func=self.update_player_data,
            trigger=CronTrigger(hour='*/6'),
            id='periodic_update',
            name='6-hour data refresh',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            func=self.retrain_models,
            trigger=CronTrigger(day_of_week='mon', hour=3, minute=0),
            id='weekly_retrain',
            name='Weekly model retraining',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            func=self.check_gameweek_deadline,
            trigger=CronTrigger(hour='*/1'),
            id='deadline_check',
            name='Hourly deadline check',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduler started with all jobs configured")
    
    def stop(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    def get_jobs(self):
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs

if __name__ == "__main__":
    scheduler = FPLUpdateScheduler()
    scheduler.start()
    
    try:
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        while True:
            import time
            time.sleep(60)
            
            jobs = scheduler.get_jobs()
            logger.info(f"Active jobs: {len(jobs)}")
            
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        scheduler.stop()
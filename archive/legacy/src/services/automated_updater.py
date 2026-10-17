import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import Dict
import asyncio
from pathlib import Path
import json

from ..data.live_data_manager import LiveDataManager
from ..pytorch_prediction_engine import PyTorchFPLPredictionEngine
from ..models.team_optimizer import TeamOptimizer

logger = logging.getLogger(__name__)

class AutomatedUpdater:
    def __init__(self, 
                 update_interval_minutes: int = 60,
                 retrain_interval_days: int = 7):
        self.live_data_manager = LiveDataManager()
        self.prediction_engine = PyTorchFPLPredictionEngine()
        self.team_optimizer = TeamOptimizer()
        
        self.update_interval_minutes = update_interval_minutes
        self.retrain_interval_days = retrain_interval_days
        
        self.status_file = Path("./data/updater_status.json")
        self.last_retrain = None
        
    def load_status(self):
        """Load the last update status"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    status = json.load(f)
                    if 'last_retrain' in status and status['last_retrain']:
                        self.last_retrain = datetime.fromisoformat(status['last_retrain'])
        except Exception as e:
            logger.error(f"Error loading status: {e}")
    
    def save_status(self):
        """Save the current update status"""
        try:
            status = {
                'last_update': datetime.now().isoformat(),
                'last_retrain': self.last_retrain.isoformat() if self.last_retrain else None,
                'update_interval_minutes': self.update_interval_minutes,
                'retrain_interval_days': self.retrain_interval_days
            }
            
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving status: {e}")
    
    def update_live_data(self) -> Dict:
        """Update live FPL data"""
        try:
            logger.info("Starting scheduled live data update...")
            
            result = self.live_data_manager.update_live_data()
            
            if result['success']:
                logger.info("Live data update completed successfully")
                
                # Generate fresh predictions with new data
                self.generate_fresh_predictions()
                
            else:
                logger.error(f"Live data update failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in scheduled live data update: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_fresh_predictions(self):
        """Generate new predictions with latest data"""
        try:
            logger.info("Generating fresh predictions with updated data...")
            
            # Get current player data
            cached_data = self.live_data_manager.get_cached_data()
            
            if 'players' in cached_data:
                players_df = cached_data['players']
                
                # Generate predictions for all current players
                predictions = []
                for _, player in players_df.iterrows():
                    try:
                        prediction = self.prediction_engine.predict_player_points(
                            player_id=player['id'],
                            player_data=player.to_dict()
                        )
                        predictions.append({
                            'player_id': player['id'],
                            'name': f"{player['first_name']} {player['second_name']}",
                            'predicted_points': prediction,
                            'current_form': player.get('form', 0),
                            'price': player['now_cost'] / 10,
                            'team': player.get('name_team', ''),
                            'position': player.get('position', ''),
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.warning(f"Failed to predict for player {player['id']}: {e}")
                        continue
                
                # Save predictions
                predictions_file = Path("./data/live_cache/latest_predictions.json")
                with open(predictions_file, 'w') as f:
                    json.dump(predictions, f, indent=2)
                
                logger.info(f"Generated predictions for {len(predictions)} players")
                
        except Exception as e:
            logger.error(f"Error generating fresh predictions: {e}")
    
    def should_retrain_model(self) -> bool:
        """Check if model needs retraining"""
        if self.last_retrain is None:
            return True
        
        days_since_retrain = (datetime.now() - self.last_retrain).days
        return days_since_retrain >= self.retrain_interval_days
    
    def retrain_model(self) -> Dict:
        """Retrain the prediction model with latest data"""
        try:
            logger.info("Starting model retraining...")
            
            # Retrain the model
            result = self.prediction_engine.train_model()
            
            if result.get('success', False):
                self.last_retrain = datetime.now()
                self.save_status()
                logger.info("Model retraining completed successfully")
            else:
                logger.error(f"Model retraining failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in model retraining: {e}")
            return {'success': False, 'error': str(e)}
    
    def weekly_optimization_update(self):
        """Weekly team optimization with latest insights"""
        try:
            logger.info("Running weekly team optimization...")
            
            # Get latest data
            cached_data = self.live_data_manager.get_cached_data()
            
            if 'players' in cached_data:
                players_df = cached_data['players']
                
                # Incorporate injury status
                if 'injuries' in cached_data:
                    injury_data = cached_data['injuries']
                    
                    # Filter out injured/suspended players
                    available_players = []
                    for _, player in players_df.iterrows():
                        player_id = str(player['id'])
                        if player_id in injury_data:
                            injury_info = injury_data[player_id]
                            if injury_info['is_available'] and injury_info.get('chance_of_playing', 100) > 75:
                                available_players.append(player)
                        else:
                            available_players.append(player)
                    
                    if available_players:
                        available_df = pd.DataFrame(available_players)
                        logger.info(f"Optimizing with {len(available_df)} available players")
                        
                        # Run optimization
                        optimal_team = self.team_optimizer.optimize_team(available_df)
                        
                        # Save weekly recommendations
                        recommendations = {
                            'gameweek': self.live_data_manager.get_current_gameweek(),
                            'optimal_team': optimal_team,
                            'timestamp': datetime.now().isoformat(),
                            'players_considered': len(available_df),
                            'injured_excluded': len(players_df) - len(available_df)
                        }
                        
                        recommendations_file = Path("./data/live_cache/weekly_recommendations.json")
                        with open(recommendations_file, 'w') as f:
                            json.dump(recommendations, f, indent=2)
                        
                        logger.info("Weekly optimization completed")
            
        except Exception as e:
            logger.error(f"Error in weekly optimization: {e}")
    
    def run_all_updates(self):
        """Run all scheduled updates"""
        try:
            logger.info("Running all scheduled updates...")
            
            # Update live data
            self.update_live_data()
            
            # Check if model needs retraining
            if self.should_retrain_model():
                self.retrain_model()
            
            # Run weekly optimization
            self.weekly_optimization_update()
            
            # Save status
            self.save_status()
            
            logger.info("All scheduled updates completed")
            
        except Exception as e:
            logger.error(f"Error in scheduled updates: {e}")
    
    def setup_scheduler(self):
        """Setup the automated scheduler"""
        logger.info("Setting up automated scheduler...")
        
        # Load previous status
        self.load_status()
        
        # Schedule regular data updates (every hour)
        schedule.every().hour.do(self.update_live_data)
        
        # Schedule weekly optimization (every Tuesday at 10 AM)
        schedule.every().tuesday.at("10:00").do(self.weekly_optimization_update)
        
        # Schedule model retraining (every Sunday at 2 AM)
        schedule.every().sunday.at("02:00").do(self.retrain_model)
        
        # Schedule comprehensive update (every 6 hours)
        schedule.every(6).hours.do(self.run_all_updates)
        
        logger.info("Scheduler setup completed")
    
    def run_scheduler(self):
        """Run the scheduler continuously"""
        logger.info("Starting automated updater...")
        
        self.setup_scheduler()
        
        # Run initial update
        self.run_all_updates()
        
        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def run_single_update(self):
        """Run a single update cycle (for testing)"""
        logger.info("Running single update cycle...")
        self.load_status()
        self.run_all_updates()
        logger.info("Single update cycle completed")

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('./logs/automated_updater.log'),
            logging.StreamHandler()
        ]
    )
    
    updater = AutomatedUpdater()
    updater.run_scheduler()
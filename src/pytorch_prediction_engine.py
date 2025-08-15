import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import joblib
from pathlib import Path

from src.data.fpl_api import FPLDataFetcher
from src.data.external_datasets import ExternalDatasets
from src.models.pytorch_cnn_predictor import PyTorchPlayerPredictor
from src.models.sentiment_analyzer import PlayerSentimentAnalyzer
from src.models.team_optimizer import FPLTeamOptimizer

logger = logging.getLogger(__name__)

class PyTorchFPLPredictionEngine:
    def __init__(self, model_dir: str = "./models", use_sentiment: bool = False):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.fpl_fetcher = FPLDataFetcher()
        self.external_data = ExternalDatasets()
        self.cnn_predictor = PyTorchPlayerPredictor()
        self.team_optimizer = FPLTeamOptimizer()
        
        self.use_sentiment = use_sentiment
        if use_sentiment:
            self.sentiment_analyzer = PlayerSentimentAnalyzer()
        
        self.predictions_cache = {}
        self.last_update = None
        
    def train_models(self, force_retrain: bool = False):
        """Train the PyTorch CNN model"""
        model_path = self.model_dir / "pytorch_model.pth"
        
        if model_path.exists() and not force_retrain:
            logger.info("Loading existing PyTorch model")
            try:
                self.cnn_predictor.load_model(str(self.model_dir))
                logger.info("Model loaded successfully")
                return
            except Exception as e:
                logger.warning(f"Failed to load existing model: {e}. Training new model.")
        
        logger.info("Training new PyTorch CNN model")
        
        try:
            # Get training data
            logger.info("Fetching training data...")
            training_data = self.external_data.get_training_data()
            logger.info(f"Training data shape: {training_data.shape}")
            
            if len(training_data) < 1000:
                logger.warning("Limited training data available. Results may be suboptimal.")
            
            # Split data chronologically
            split_date = pd.to_datetime('2024-01-01')
            training_data['kickoff_time'] = pd.to_datetime(training_data['kickoff_time'])
            
            train_df = training_data[training_data['kickoff_time'] < split_date]
            val_df = training_data[training_data['kickoff_time'] >= split_date]
            
            logger.info(f"Train set: {len(train_df)} records, Validation set: {len(val_df)} records")
            
            if len(train_df) == 0 or len(val_df) == 0:
                logger.warning("Insufficient data split. Using 80/20 random split.")
                shuffled = training_data.sample(frac=1, random_state=42)
                split_idx = int(0.8 * len(shuffled))
                train_df = shuffled.iloc[:split_idx]
                val_df = shuffled.iloc[split_idx:]
            
            # Build and train model
            self.cnn_predictor.build_model()
            history = self.cnn_predictor.train(train_df, val_df, epochs=50)
            
            # Save model
            self.cnn_predictor.save_model(str(self.model_dir))
            
            # Save training history
            joblib.dump(history, self.model_dir / "training_history.pkl")
            logger.info("Model training completed and saved")
            
            return history
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            logger.info("Will use baseline predictions instead")
            return None
    
    def get_player_predictions(self, horizon_gameweeks: int = 5) -> Dict[int, float]:
        """Get predictions for all players"""
        if self.predictions_cache and self.last_update:
            if datetime.now() - self.last_update < timedelta(hours=1):
                return self.predictions_cache
        
        logger.info("Generating player predictions")
        
        players_df = self.fpl_fetcher.get_all_players_data()
        predictions = {}
        
        # Check if model is trained
        model_available = self.cnn_predictor.model is not None
        if not model_available:
            logger.info("CNN model not available, trying to load existing model...")
            try:
                self.cnn_predictor.load_model(str(self.model_dir))
                model_available = True
                logger.info("Model loaded successfully")
            except:
                logger.warning("No trained model found. Using baseline predictions.")
        
        for _, player in players_df.iterrows():
            player_id = player['id']
            
            try:
                if model_available and player['minutes'] > 180:  # Only use ML for players with significant minutes
                    try:
                        player_history = self.fpl_fetcher.get_player_detailed_stats(player_id)
                        
                        if len(player_history) >= self.cnn_predictor.sequence_length:
                            # Use CNN prediction
                            ml_predictions = self.cnn_predictor.predict_multiple_gameweeks(
                                player_history, 
                                horizon_gameweeks
                            )
                            base_prediction = np.mean(ml_predictions)
                        else:
                            # Fallback to baseline for insufficient data
                            base_prediction = self._get_baseline_prediction(player)
                    except Exception as e:
                        logger.debug(f"ML prediction failed for player {player_id}: {e}")
                        base_prediction = self._get_baseline_prediction(player)
                else:
                    # Use baseline prediction
                    base_prediction = self._get_baseline_prediction(player)
                
                # Apply sentiment analysis if enabled
                if self.use_sentiment and player['minutes'] > 180:
                    try:
                        sentiment_data = self.sentiment_analyzer.get_aggregated_sentiment(
                            player['web_name'],
                            player.get('name_team', '')
                        )
                        sentiment_modifier = 1 + (sentiment_data['sentiment_score'] * 0.1)
                        base_prediction *= sentiment_modifier
                    except Exception as e:
                        logger.debug(f"Sentiment analysis failed for player {player_id}: {e}")
                
                predictions[player_id] = max(0, base_prediction)
                
            except Exception as e:
                logger.warning(f"Error predicting for player {player_id}: {e}")
                predictions[player_id] = self._get_baseline_prediction(player)
        
        self.predictions_cache = predictions
        self.last_update = datetime.now()
        
        logger.info(f"Generated predictions for {len(predictions)} players")
        return predictions
    
    def _get_baseline_prediction(self, player: pd.Series) -> float:
        """Fallback prediction based on current season stats"""
        try:
            if player['total_points'] > 0 and player['minutes'] > 0:
                # Points per 90 minutes, adjusted for expected playing time
                points_per_90 = (player['total_points'] / player['minutes']) * 90
                expected_minutes = 75  # Average expected minutes per game
                base_prediction = points_per_90 * (expected_minutes / 90)
                
                # Adjust by form if available
                if 'form' in player and player['form'] > 0:
                    form_modifier = max(0.5, min(1.5, float(player['form']) / 5.0))
                    base_prediction *= form_modifier
                
                return base_prediction
            else:
                # Position-based average for new/unused players
                position_avg = {
                    'GK': 2.5,
                    'DEF': 3.5,
                    'MID': 4.5,
                    'FWD': 4.0
                }
                return position_avg.get(player.get('position', 'MID'), 3.0)
        except Exception as e:
            logger.debug(f"Baseline prediction error: {e}")
            return 3.0
    
    def optimize_team_selection(self, budget: float = 100.0) -> Dict:
        """Optimize team selection using predictions"""
        logger.info("Optimizing team selection")
        
        players_df = self.fpl_fetcher.get_all_players_data()
        predictions = self.get_player_predictions()
        
        optimal_squad = self.team_optimizer.optimize_squad(players_df, predictions)
        
        # Get single gameweek predictions for starting 11
        gameweek_predictions = self.get_single_gameweek_predictions()
        starting_11 = self.team_optimizer.optimize_starting_11(
            optimal_squad['squad'],
            gameweek_predictions
        )
        
        return {
            'squad': optimal_squad,
            'starting_11': starting_11,
            'total_predicted_points': optimal_squad['predicted_points']
        }
    
    def get_single_gameweek_predictions(self) -> Dict[int, float]:
        """Get single gameweek predictions"""
        players_df = self.fpl_fetcher.get_all_players_data()
        predictions = {}
        
        model_available = self.cnn_predictor.model is not None
        
        for _, player in players_df.iterrows():
            player_id = player['id']
            
            try:
                if model_available and player['minutes'] > 180:
                    try:
                        player_history = self.fpl_fetcher.get_player_detailed_stats(player_id)
                        
                        if len(player_history) >= self.cnn_predictor.sequence_length:
                            prediction = self.cnn_predictor.predict(player_history)
                        else:
                            prediction = self._get_baseline_prediction(player)
                    except:
                        prediction = self._get_baseline_prediction(player)
                else:
                    prediction = self._get_baseline_prediction(player)
                
                predictions[player_id] = max(0, prediction)
                
            except Exception as e:
                predictions[player_id] = self._get_baseline_prediction(player)
        
        return predictions
    
    def get_transfer_suggestions(self, 
                                current_team_id: int,
                                gameweek: int,
                                free_transfers: int = 1) -> Dict:
        """Get transfer suggestions"""
        try:
            current_picks = self.fpl_fetcher.get_gameweek_picks(current_team_id, gameweek)
            current_squad = []
            
            players_df = self.fpl_fetcher.get_all_players_data()
            
            for pick in current_picks['picks']:
                player_data = players_df[players_df['id'] == pick['element']].iloc[0]
                current_squad.append({
                    'id': pick['element'],
                    'name': player_data['web_name'],
                    'position': player_data['position'],
                    'team': player_data['team'],
                    'price': player_data['now_cost'] / 10
                })
            
            predictions = self.get_player_predictions()
            bank = current_picks.get('entry_history', {}).get('bank', 0) / 10
            
            suggestions = self.team_optimizer.suggest_transfers(
                current_squad,
                players_df,
                predictions,
                free_transfers,
                bank
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting transfer suggestions: {e}")
            return {'error': str(e)}
    
    def update_with_live_data(self, gameweek: int):
        """Update with live gameweek data"""
        logger.info(f"Updating with live gameweek {gameweek} data")
        
        try:
            live_data = self.fpl_fetcher.get_live_gameweek_data(gameweek)
            
            for element_id, element_data in live_data['elements'].items():
                stats = element_data['stats']
                logger.debug(f"Player {element_id} scored {stats.get('total_points', 0)} points")
            
            # Clear cache to force refresh
            self.predictions_cache = {}
            self.last_update = None
            
        except Exception as e:
            logger.error(f"Error updating with live data: {e}")
    
    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        info = {
            'model_type': 'PyTorch CNN',
            'model_loaded': self.cnn_predictor.model is not None,
            'device': self.cnn_predictor.device,
            'sequence_length': self.cnn_predictor.sequence_length,
            'feature_dim': self.cnn_predictor.feature_dim,
            'sentiment_analysis': self.use_sentiment
        }
        
        # Try to get training history
        try:
            history_path = self.model_dir / "training_history.pkl"
            if history_path.exists():
                history = joblib.load(history_path)
                info['last_training'] = {
                    'epochs': len(history['train_loss']),
                    'final_train_loss': history['train_loss'][-1] if history['train_loss'] else None,
                    'final_val_loss': history['val_loss'][-1] if history['val_loss'] else None
                }
        except:
            pass
        
        return info
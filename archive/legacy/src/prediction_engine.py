import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import joblib
from pathlib import Path

from src.data.fpl_api import FPLDataFetcher
from src.data.external_datasets import ExternalDatasets
from src.models.cnn_predictor import CNNPlayerPredictor
from src.models.sentiment_analyzer import PlayerSentimentAnalyzer
from src.models.team_optimizer import FPLTeamOptimizer

logger = logging.getLogger(__name__)

class FPLPredictionEngine:
    def __init__(self, model_dir: str = "./models", use_sentiment: bool = True):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.fpl_fetcher = FPLDataFetcher()
        self.external_data = ExternalDatasets()
        self.cnn_predictor = CNNPlayerPredictor()
        self.team_optimizer = FPLTeamOptimizer()
        
        self.use_sentiment = use_sentiment
        if use_sentiment:
            self.sentiment_analyzer = PlayerSentimentAnalyzer()
        
        self.predictions_cache = {}
        self.last_update = None
        
    def train_models(self, force_retrain: bool = False):
        model_path = self.model_dir / "cnn_model.h5"
        
        if model_path.exists() and not force_retrain:
            logger.info("Loading existing model")
            self.cnn_predictor.load_model(str(self.model_dir))
            return
        
        logger.info("Training new model")
        
        training_data = self.external_data.get_training_data()
        
        split_date = pd.to_datetime('2024-01-01')
        train_df = training_data[pd.to_datetime(training_data['kickoff_time']) < split_date]
        val_df = training_data[pd.to_datetime(training_data['kickoff_time']) >= split_date]
        
        self.cnn_predictor.build_model()
        history = self.cnn_predictor.train(train_df, val_df, epochs=50)
        
        self.cnn_predictor.save_model(str(self.model_dir))
        
        joblib.dump(history.history, self.model_dir / "training_history.pkl")
        logger.info("Model training completed")
    
    def get_player_predictions(self, horizon_gameweeks: int = 5) -> Dict[int, float]:
        if self.predictions_cache and self.last_update:
            if datetime.now() - self.last_update < timedelta(hours=1):
                return self.predictions_cache
        
        logger.info("Generating player predictions")
        
        players_df = self.fpl_fetcher.get_all_players_data()
        predictions = {}
        
        for _, player in players_df.iterrows():
            player_id = player['id']
            
            try:
                player_history = self.fpl_fetcher.get_player_detailed_stats(player_id)
                
                if len(player_history) < self.cnn_predictor.sequence_length:
                    base_prediction = self._get_baseline_prediction(player)
                else:
                    base_prediction = np.mean(
                        self.cnn_predictor.predict_multiple_gameweeks(
                            player_history, 
                            horizon_gameweeks
                        )
                    )
                
                if self.use_sentiment and player['minutes'] > 180:
                    sentiment_data = self.sentiment_analyzer.get_aggregated_sentiment(
                        player['web_name'],
                        player['name_team']
                    )
                    sentiment_modifier = 1 + (sentiment_data['sentiment_score'] * 0.1)
                    base_prediction *= sentiment_modifier
                
                predictions[player_id] = base_prediction
                
            except Exception as e:
                logger.warning(f"Error predicting for player {player_id}: {e}")
                predictions[player_id] = self._get_baseline_prediction(player)
        
        self.predictions_cache = predictions
        self.last_update = datetime.now()
        
        return predictions
    
    def _get_baseline_prediction(self, player: pd.Series) -> float:
        if player['total_points'] > 0 and player['minutes'] > 0:
            points_per_minute = player['total_points'] / player['minutes']
            return points_per_minute * 90 * 0.7
        else:
            position_avg = {
                'GK': 2.0,
                'DEF': 3.5,
                'MID': 4.5,
                'FWD': 4.0
            }
            return position_avg.get(player['position'], 3.0)
    
    def optimize_team_selection(self, budget: float = 100.0) -> Dict:
        logger.info("Optimizing team selection")
        
        players_df = self.fpl_fetcher.get_all_players_data()
        predictions = self.get_player_predictions()
        
        optimal_squad = self.team_optimizer.optimize_squad(players_df, predictions)
        
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
        players_df = self.fpl_fetcher.get_all_players_data()
        predictions = {}
        
        for _, player in players_df.iterrows():
            player_id = player['id']
            
            try:
                player_history = self.fpl_fetcher.get_player_detailed_stats(player_id)
                
                if len(player_history) >= self.cnn_predictor.sequence_length:
                    prediction = self.cnn_predictor.predict(player_history)
                else:
                    prediction = self._get_baseline_prediction(player)
                
                predictions[player_id] = prediction
                
            except Exception as e:
                predictions[player_id] = self._get_baseline_prediction(player)
        
        return predictions
    
    def get_transfer_suggestions(self, 
                                current_team_id: int,
                                gameweek: int,
                                free_transfers: int = 1) -> Dict:
        
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
        logger.info(f"Updating with live gameweek {gameweek} data")
        
        live_data = self.fpl_fetcher.get_live_gameweek_data(gameweek)
        
        for element_id, element_data in live_data['elements'].items():
            stats = element_data['stats']
            logger.debug(f"Player {element_id} scored {stats.get('total_points', 0)} points")
        
        self.predictions_cache = {}
        self.last_update = None
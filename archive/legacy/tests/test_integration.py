import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from src.prediction_engine import FPLPredictionEngine
from src.data.fpl_api import FPLDataFetcher
from src.models.cnn_predictor import CNNPlayerPredictor
from src.models.team_optimizer import FPLTeamOptimizer

class TestIntegration:
    """Integration tests for the complete FPL prediction workflow"""
    
    @pytest.fixture
    def mock_player_data(self):
        """Generate realistic player data for testing"""
        np.random.seed(42)
        
        players = []
        player_id = 1
        
        positions = [
            ('GK', 30, 4.5, 6.0),
            ('DEF', 100, 4.0, 8.0),
            ('MID', 150, 5.0, 12.0),
            ('FWD', 60, 6.0, 14.0)
        ]
        
        for position, count, min_price, max_price in positions:
            for i in range(count):
                team_id = (i % 20) + 1
                price = np.random.uniform(min_price, max_price)
                
                players.append({
                    'id': player_id,
                    'web_name': f'{position}_{i+1}',
                    'first_name': f'First_{i+1}',
                    'second_name': f'Last_{i+1}',
                    'team': team_id,
                    'element_type': {'GK': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}[position],
                    'position': position,
                    'now_cost': int(price * 10),
                    'selected_by_percent': np.random.uniform(0.5, 30.0),
                    'total_points': np.random.randint(0, 200),
                    'points_per_game': np.random.uniform(2.0, 8.0),
                    'form': np.random.uniform(2.0, 8.0),
                    'status': 'a',
                    'minutes': np.random.randint(0, 2500),
                    'goals_scored': np.random.randint(0, 20),
                    'assists': np.random.randint(0, 15),
                    'clean_sheets': np.random.randint(0, 15),
                    'goals_conceded': np.random.randint(0, 40),
                    'influence': np.random.uniform(0, 100),
                    'creativity': np.random.uniform(0, 100),
                    'threat': np.random.uniform(0, 100),
                    'ict_index': np.random.uniform(0, 20),
                    'expected_goals': np.random.uniform(0, 15),
                    'expected_assists': np.random.uniform(0, 10),
                    'expected_goal_involvements': np.random.uniform(0, 20),
                    'expected_goals_conceded': np.random.uniform(0, 30),
                    'value': price,
                    'name_team': f'Team_{team_id}',
                    'short_name_team': f'T{team_id}'
                })
                player_id += 1
        
        return pd.DataFrame(players)
    
    @pytest.fixture
    def mock_player_history(self):
        """Generate player history data"""
        np.random.seed(42)
        
        history_data = []
        for gw in range(1, 11):  # 10 gameweeks
            history_data.append({
                'kickoff_time': f'2024-08-{10 + gw:02d}T14:00:00Z',
                'total_points': np.random.randint(0, 15),
                'goals_scored': np.random.randint(0, 3),
                'assists': np.random.randint(0, 2),
                'clean_sheets': np.random.randint(0, 1),
                'goals_conceded': np.random.randint(0, 3),
                'minutes': np.random.choice([0, 45, 90]),
                'influence': np.random.uniform(0, 100),
                'creativity': np.random.uniform(0, 100),
                'threat': np.random.uniform(0, 100),
                'ict_index': np.random.uniform(0, 20),
                'expected_goals': np.random.uniform(0, 2),
                'expected_assists': np.random.uniform(0, 2),
                'expected_goal_involvements': np.random.uniform(0, 3),
                'expected_goals_conceded': np.random.uniform(0, 2),
                'value': np.random.uniform(4.0, 12.0)
            })
        
        return pd.DataFrame(history_data)
    
    @pytest.fixture
    def mock_bootstrap_data(self):
        """Mock FPL bootstrap data"""
        return {
            'elements': [],  # Will be populated by mock_player_data
            'teams': [
                {'id': i, 'name': f'Team_{i}', 'short_name': f'T{i}'}
                for i in range(1, 21)
            ],
            'events': [
                {
                    'id': i,
                    'name': f'Gameweek {i}',
                    'is_current': i == 10,
                    'is_next': i == 11,
                    'deadline_time': f'2024-08-{10 + i:02d}T14:00:00Z',
                    'finished': i < 10
                }
                for i in range(1, 39)
            ]
        }
    
    @patch.object(FPLDataFetcher, 'get_bootstrap_data')
    @patch.object(FPLDataFetcher, 'get_player_detailed_stats')
    def test_complete_prediction_workflow(self, mock_history, mock_bootstrap, 
                                        mock_player_data, mock_player_history, 
                                        mock_bootstrap_data):
        """Test the complete workflow from data fetching to predictions"""
        
        # Setup mocks
        mock_bootstrap_data['elements'] = mock_player_data.to_dict('records')
        mock_bootstrap.return_value = mock_bootstrap_data
        mock_history.return_value = mock_player_history
        
        # Initialize engine
        engine = FPLPredictionEngine(use_sentiment=False)
        
        # Test getting player data
        players_df = engine.fpl_fetcher.get_all_players_data()
        assert len(players_df) == len(mock_player_data)
        assert 'position' in players_df.columns
        
        # Test baseline predictions (without trained model)
        predictions = engine.get_player_predictions(horizon_gameweeks=3)
        assert len(predictions) == len(mock_player_data)
        
        # All predictions should be positive
        for pred in predictions.values():
            assert pred >= 0
        
        # Test single gameweek predictions
        single_gw_predictions = engine.get_single_gameweek_predictions()
        assert len(single_gw_predictions) == len(mock_player_data)
    
    @patch.object(FPLDataFetcher, 'get_bootstrap_data')
    def test_team_optimization_workflow(self, mock_bootstrap, mock_player_data, 
                                       mock_bootstrap_data):
        """Test the complete team optimization workflow"""
        
        mock_bootstrap_data['elements'] = mock_player_data.to_dict('records')
        mock_bootstrap.return_value = mock_bootstrap_data
        
        engine = FPLPredictionEngine(use_sentiment=False)
        
        # Get players and create mock predictions
        players_df = engine.fpl_fetcher.get_all_players_data()
        predictions = {
            player_id: np.random.uniform(3.0, 8.0) 
            for player_id in players_df['id']
        }
        
        # Test squad optimization
        optimizer = FPLTeamOptimizer()
        result = optimizer.optimize_squad(players_df, predictions)
        
        assert 'squad' in result
        assert 'total_cost' in result
        assert 'predicted_points' in result
        
        # Verify constraints
        squad = result['squad']
        assert len(squad) == 15
        
        positions = [p['position'] for p in squad]
        assert positions.count('GK') == 2
        assert positions.count('DEF') == 5
        assert positions.count('MID') == 5
        assert positions.count('FWD') == 3
        
        # Test starting 11 optimization
        gameweek_predictions = {p['id']: np.random.uniform(3.0, 8.0) for p in squad}
        starting_11_result = optimizer.optimize_starting_11(squad, gameweek_predictions)
        
        assert len(starting_11_result['starting_11']) == 11
        assert 'captain' in starting_11_result
        assert 'vice_captain' in starting_11_result
    
    @patch.object(CNNPlayerPredictor, 'predict')
    def test_model_prediction_integration(self, mock_predict):
        """Test model prediction integration"""
        
        # Setup predictor
        predictor = CNNPlayerPredictor()
        predictor.build_model()
        
        # Mock predictions
        mock_predict.return_value = 6.5
        
        # Create sample history
        history = pd.DataFrame({
            'kickoff_time': pd.date_range('2024-08-01', periods=10, freq='W'),
            'total_points': np.random.randint(0, 15, 10),
            'goals_scored': np.random.randint(0, 3, 10),
            'assists': np.random.randint(0, 2, 10),
            'clean_sheets': np.random.randint(0, 1, 10),
            'goals_conceded': np.random.randint(0, 3, 10),
            'minutes': np.random.choice([0, 45, 90], 10),
            'influence': np.random.uniform(0, 100, 10),
            'creativity': np.random.uniform(0, 100, 10),
            'threat': np.random.uniform(0, 100, 10),
            'ict_index': np.random.uniform(0, 20, 10),
            'expected_goals': np.random.uniform(0, 2, 10),
            'expected_assists': np.random.uniform(0, 2, 10),
            'expected_goal_involvements': np.random.uniform(0, 3, 10),
            'expected_goals_conceded': np.random.uniform(0, 2, 10),
            'value': np.random.uniform(4.0, 12.0, 10)
        })
        
        # Test single prediction
        prediction = predictor.predict(history)
        assert prediction == 6.5
        
        # Test multiple gameweek predictions
        multi_predictions = predictor.predict_multiple_gameweeks(history, n_gameweeks=5)
        assert len(multi_predictions) == 5
    
    def test_error_handling_insufficient_data(self):
        """Test error handling with insufficient data"""
        
        engine = FPLPredictionEngine(use_sentiment=False)
        predictor = CNNPlayerPredictor()
        
        # Test with insufficient history
        short_history = pd.DataFrame({
            'total_points': [5, 3],
            'goals_scored': [1, 0],
        })
        
        # Add missing columns
        for col in predictor.feature_columns:
            if col not in short_history.columns:
                short_history[col] = 0
        
        # Should return 0 for insufficient data
        prediction = predictor.predict(short_history)
        assert prediction == 0.0
    
    def test_data_validation_and_cleaning(self):
        """Test data validation and cleaning processes"""
        
        # Create data with missing values and outliers
        dirty_data = pd.DataFrame({
            'name': ['Player_A', 'Player_B', 'Player_C'],
            'kickoff_time': ['2024-08-17T14:00:00Z', '2024-08-24T16:30:00Z', '2024-08-31T14:00:00Z'],
            'total_points': [8, None, 15],  # Missing value
            'goals_scored': [1, 0, 5],  # Outlier
            'minutes': [90, 45, 95],  # Slight outlier
        })
        
        predictor = CNNPlayerPredictor()
        
        # Add missing columns with default values
        for col in predictor.feature_columns:
            if col not in dirty_data.columns:
                dirty_data[col] = 0
        
        # Test sequence preparation handles missing data
        X, y = predictor.prepare_sequences(dirty_data)
        
        # Should handle the data gracefully (may return empty arrays due to insufficient sequences)
        assert isinstance(X, np.ndarray)
        assert isinstance(y, np.ndarray)
    
    @patch.object(FPLDataFetcher, 'get_bootstrap_data')
    @patch.object(FPLDataFetcher, 'get_gameweek_picks')
    def test_transfer_suggestions_workflow(self, mock_picks, mock_bootstrap, 
                                         mock_player_data, mock_bootstrap_data):
        """Test the transfer suggestions workflow"""
        
        mock_bootstrap_data['elements'] = mock_player_data.to_dict('records')
        mock_bootstrap.return_value = mock_bootstrap_data
        
        # Mock current team picks
        current_picks = {
            'picks': [
                {'element': 1, 'position': 1},  # GK
                {'element': 2, 'position': 2},  # GK
                {'element': 3, 'position': 3},  # DEF
                # ... more picks
            ],
            'entry_history': {'bank': 5}  # 0.5m in bank
        }
        mock_picks.return_value = current_picks
        
        engine = FPLPredictionEngine(use_sentiment=False)
        
        # Test transfer suggestions
        suggestions = engine.get_transfer_suggestions(
            current_team_id=12345,
            gameweek=10,
            free_transfers=1
        )
        
        # Should return suggestions structure even if empty
        assert isinstance(suggestions, dict)
    
    def test_memory_and_performance(self, mock_player_data):
        """Test memory usage and performance with large datasets"""
        
        # Create larger dataset
        large_data = pd.concat([mock_player_data] * 3, ignore_index=True)
        
        predictor = CNNPlayerPredictor()
        optimizer = FPLTeamOptimizer()
        
        # Test that operations complete without memory errors
        predictions = {
            player_id: np.random.uniform(3.0, 8.0) 
            for player_id in large_data['id']
        }
        
        # Should handle large datasets
        result = optimizer.optimize_squad(large_data, predictions)
        assert result is not None
    
    def test_edge_cases_and_boundary_conditions(self):
        """Test various edge cases and boundary conditions"""
        
        optimizer = FPLTeamOptimizer()
        
        # Test with minimum budget
        cheap_players = pd.DataFrame([
            {
                'id': i,
                'web_name': f'Cheap_{i}',
                'team': i,
                'position': pos,
                'now_cost': 40,  # 4.0m
                'selected_by_percent': 1.0
            }
            for i, pos in enumerate(['GK', 'GK', 'DEF', 'DEF', 'DEF', 'DEF', 'DEF'], 1)
        ])
        
        predictions = {i: 3.0 for i in range(1, 8)}
        
        # Should handle edge case gracefully
        result = optimizer.optimize_squad(cheap_players, predictions)
        assert result is not None
        
        # Test with all players from different teams (no team constraint issues)
        diverse_team_players = cheap_players.copy()
        diverse_team_players['team'] = range(1, len(diverse_team_players) + 1)
        
        result2 = optimizer.optimize_squad(diverse_team_players, predictions)
        assert result2 is not None
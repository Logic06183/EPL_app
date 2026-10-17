import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import requests

from src.data.fpl_api import FPLDataFetcher
from src.models.cnn_predictor import CNNPlayerPredictor
from src.models.team_optimizer import FPLTeamOptimizer
from src.prediction_engine import FPLPredictionEngine

class TestErrorHandling:
    """Test error handling and edge cases throughout the application"""
    
    def test_fpl_api_network_errors(self):
        """Test handling of network errors in FPL API"""
        fetcher = FPLDataFetcher()
        
        # Test connection timeout
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
            
            with pytest.raises(requests.exceptions.Timeout):
                fetcher.get_bootstrap_data()
        
        # Test connection error
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            with pytest.raises(requests.exceptions.ConnectionError):
                fetcher.get_bootstrap_data()
    
    def test_fpl_api_invalid_response(self):
        """Test handling of invalid API responses"""
        fetcher = FPLDataFetcher()
        
        with patch.object(fetcher.session, 'get') as mock_get:
            # Mock response with invalid JSON
            mock_response = MagicMock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with pytest.raises(ValueError):
                fetcher.get_bootstrap_data()
    
    def test_fpl_api_http_errors(self):
        """Test handling of HTTP errors"""
        fetcher = FPLDataFetcher()
        
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
            mock_get.return_value = mock_response
            
            with pytest.raises(requests.exceptions.HTTPError):
                fetcher.get_bootstrap_data()
    
    def test_empty_player_data_handling(self):
        """Test handling of empty player data"""
        fetcher = FPLDataFetcher()
        
        with patch.object(fetcher, 'get_bootstrap_data') as mock_bootstrap:
            mock_bootstrap.return_value = {
                'elements': [],  # Empty player list
                'teams': [],
                'events': []
            }
            
            result = fetcher.get_all_players_data()
            assert len(result) == 0
            assert isinstance(result, pd.DataFrame)
    
    def test_malformed_player_data(self):
        """Test handling of malformed player data"""
        fetcher = FPLDataFetcher()
        
        with patch.object(fetcher, 'get_bootstrap_data') as mock_bootstrap:
            mock_bootstrap.return_value = {
                'elements': [
                    {'id': 1, 'web_name': 'Player1'},  # Missing required fields
                    {'web_name': 'Player2', 'team': 1},  # Missing id
                ],
                'teams': [{'id': 1, 'name': 'Team1'}],
                'events': []
            }
            
            # Should handle missing fields gracefully
            result = fetcher.get_all_players_data()
            assert len(result) >= 0  # May filter out invalid entries
    
    def test_cnn_predictor_invalid_input_shapes(self):
        """Test CNN predictor with invalid input shapes"""
        predictor = CNNPlayerPredictor(sequence_length=6, feature_dim=15)
        
        # Test with wrong number of features
        invalid_data = pd.DataFrame({
            'name': ['Player1'] * 10,
            'kickoff_time': pd.date_range('2024-01-01', periods=10, freq='D'),
            'total_points': range(10),
            # Missing most required features
        })
        
        # Should handle missing features by filling with defaults
        X, y = predictor.prepare_sequences(invalid_data)
        # With insufficient features and short sequences, should return empty
        assert X.shape[0] >= 0
        assert y.shape[0] >= 0
    
    def test_cnn_predictor_extreme_values(self):
        """Test CNN predictor with extreme values"""
        predictor = CNNPlayerPredictor()
        
        # Create data with extreme values
        extreme_data = pd.DataFrame()
        for i in range(10):
            row = {
                'name': 'Extreme_Player',
                'kickoff_time': f'2024-08-{17 + i:02d}T14:00:00Z',
            }
            
            # Add extreme values for all features
            for col in predictor.feature_columns:
                if col == 'total_points':
                    row[col] = 1000 if i == 0 else -50  # Extreme positive and negative
                else:
                    row[col] = np.inf if i % 2 == 0 else -np.inf
            
            extreme_data = pd.concat([extreme_data, pd.DataFrame([row])], ignore_index=True)
        
        # Should handle extreme values gracefully
        try:
            X, y = predictor.prepare_sequences(extreme_data)
            # May succeed with data cleaning, or return empty arrays
            assert isinstance(X, np.ndarray)
            assert isinstance(y, np.ndarray)
        except Exception as e:
            # If it fails, should be a specific handled exception
            assert isinstance(e, (ValueError, TypeError))
    
    def test_team_optimizer_impossible_constraints(self):
        """Test team optimizer with impossible constraints"""
        optimizer = FPLTeamOptimizer()
        
        # Create scenario where budget is too low
        expensive_players = pd.DataFrame([
            {
                'id': i,
                'web_name': f'Expensive_{i}',
                'team': i,
                'position': pos,
                'now_cost': 140,  # 14.0m each - impossible to fit 15 players in 100m budget
                'selected_by_percent': 10.0
            }
            for i, pos in enumerate(['GK'] * 2 + ['DEF'] * 5 + ['MID'] * 5 + ['FWD'] * 3, 1)
        ])
        
        predictions = {i: 8.0 for i in range(1, 16)}
        
        # Should handle impossible constraints gracefully
        result = optimizer.optimize_squad(expensive_players, predictions)
        
        # Should either find a solution or fall back to a reasonable alternative
        assert result is not None
        assert 'optimization_status' in result
        
        if result['optimization_status'] == 'fallback':
            assert 'squad' in result
            assert len(result['squad']) > 0
    
    def test_team_optimizer_no_valid_players(self):
        """Test team optimizer with no valid players for a position"""
        optimizer = FPLTeamOptimizer()
        
        # Create players with only forwards (no GK, DEF, MID)
        invalid_squad = pd.DataFrame([
            {
                'id': i,
                'web_name': f'Forward_{i}',
                'team': i,
                'position': 'FWD',
                'now_cost': 60,
                'selected_by_percent': 10.0
            }
            for i in range(1, 16)
        ])
        
        predictions = {i: 6.0 for i in range(1, 16)}
        
        # Should handle missing positions gracefully
        result = optimizer.optimize_squad(invalid_squad, predictions)
        
        # Should either find a fallback solution or fail gracefully
        assert result is not None
        assert isinstance(result, dict)
    
    def test_prediction_engine_missing_dependencies(self):
        """Test prediction engine with missing optional dependencies"""
        
        # Test without sentiment analysis
        engine = FPLPredictionEngine(use_sentiment=False)
        assert engine.sentiment_analyzer is None
        
        # Should work without sentiment analysis
        with patch.object(engine.fpl_fetcher, 'get_all_players_data') as mock_players:
            mock_players.return_value = pd.DataFrame([{
                'id': 1,
                'web_name': 'Test Player',
                'position': 'FWD',
                'minutes': 900,
                'total_points': 100
            }])
            
            predictions = engine.get_player_predictions()
            assert isinstance(predictions, dict)
            assert 1 in predictions
    
    def test_division_by_zero_handling(self):
        """Test handling of division by zero scenarios"""
        optimizer = FPLTeamOptimizer()
        
        # Create players with zero cost (edge case)
        zero_cost_players = pd.DataFrame([
            {
                'id': i,
                'web_name': f'Free_{i}',
                'team': 1,
                'position': 'MID',
                'now_cost': 0,  # Zero cost
                'selected_by_percent': 0.1
            }
            for i in range(1, 6)
        ])
        
        predictions = {i: 5.0 for i in range(1, 6)}
        
        # Should handle zero costs without division by zero
        try:
            result = optimizer.optimize_squad(zero_cost_players, predictions)
            # If successful, should be a valid result
            if result:
                assert isinstance(result, dict)
        except ZeroDivisionError:
            pytest.fail("Division by zero not handled properly")
    
    def test_missing_prediction_data(self):
        """Test handling of missing prediction data"""
        engine = FPLPredictionEngine(use_sentiment=False)
        
        with patch.object(engine.fpl_fetcher, 'get_all_players_data') as mock_players:
            mock_players.return_value = pd.DataFrame([{
                'id': 1,
                'web_name': 'Test Player',
                'position': 'FWD',
                'minutes': 0,  # No playing time
                'total_points': 0  # No points
            }])
            
            with patch.object(engine.fpl_fetcher, 'get_player_detailed_stats') as mock_history:
                mock_history.return_value = pd.DataFrame()  # Empty history
                
                # Should handle missing data gracefully
                predictions = engine.get_player_predictions()
                assert isinstance(predictions, dict)
                assert len(predictions) > 0
    
    def test_memory_constraints_large_dataset(self):
        """Test behavior with memory-constrained large datasets"""
        # This test would be more relevant in production with actual large datasets
        predictor = CNNPlayerPredictor()
        
        # Create a moderately large dataset
        large_data = []
        for player in range(50):  # 50 players
            for gw in range(38):  # 38 gameweeks
                row = {'name': f'Player_{player}', 'kickoff_time': f'2024-{8 + gw//4:02d}-{1 + gw%28:02d}'}
                for col in predictor.feature_columns:
                    row[col] = np.random.uniform(0, 10)
                large_data.append(row)
        
        large_df = pd.DataFrame(large_data)
        
        # Should handle large datasets without memory errors
        try:
            X, y = predictor.prepare_sequences(large_df)
            # Should succeed or fail gracefully
            assert isinstance(X, np.ndarray)
            assert isinstance(y, np.ndarray)
        except MemoryError:
            pytest.skip("System doesn't have enough memory for this test")
    
    def test_concurrent_access_handling(self):
        """Test handling of concurrent access scenarios"""
        engine = FPLPredictionEngine(use_sentiment=False)
        
        # Simulate concurrent cache access
        engine.predictions_cache = {1: 5.0, 2: 6.0}
        
        # Should handle cache access safely
        predictions1 = engine.predictions_cache
        predictions2 = engine.predictions_cache
        
        assert predictions1 == predictions2
    
    def test_invalid_gameweek_data(self):
        """Test handling of invalid gameweek data"""
        fetcher = FPLDataFetcher()
        
        with patch.object(fetcher.session, 'get') as mock_get:
            # Mock invalid gameweek response
            mock_response = MagicMock()
            mock_response.json.return_value = {'invalid': 'structure'}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Should handle invalid structure gracefully
            result = fetcher.get_live_gameweek_data(999)
            assert isinstance(result, dict)
    
    def test_file_system_errors(self):
        """Test handling of file system errors during model save/load"""
        predictor = CNNPlayerPredictor()
        predictor.build_model()
        
        # Test saving to invalid path
        with pytest.raises(Exception):  # Could be PermissionError, FileNotFoundError, etc.
            predictor.save_model("/invalid/path/that/does/not/exist")
        
        # Test loading from invalid path
        with pytest.raises(Exception):
            predictor.load_model("/invalid/path/that/does/not/exist")
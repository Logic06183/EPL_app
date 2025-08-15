import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
from src.api.main import app

client = TestClient(app)

class TestFPLAPI:
    
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data
        assert data["version"] == "1.0.0"
    
    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "models_loaded" in data
        assert data["status"] == "healthy"
    
    @patch('src.api.main.prediction_engine')
    @patch('src.api.main.fpl_fetcher')
    def test_get_all_player_predictions(self, mock_fetcher, mock_engine):
        # Mock the prediction engine
        mock_engine.get_player_predictions.return_value = {
            1: 8.5,
            2: 6.2,
            3: 7.1
        }
        
        # Mock the FPL fetcher
        mock_players_df = pd.DataFrame([
            {'id': 1, 'web_name': 'Player1', 'name_team': 'Arsenal', 'position': 'FWD', 'now_cost': 100},
            {'id': 2, 'web_name': 'Player2', 'name_team': 'Liverpool', 'position': 'MID', 'now_cost': 80},
            {'id': 3, 'web_name': 'Player3', 'name_team': 'Chelsea', 'position': 'DEF', 'now_cost': 60}
        ])
        mock_fetcher.get_all_players_data.return_value = mock_players_df
        
        response = client.get("/players/predictions?top_n=3")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
        
        # Check first player (should be highest predicted points)
        first_player = data[0]
        assert "player_id" in first_player
        assert "player_name" in first_player
        assert "predicted_points" in first_player
        assert "confidence" in first_player
        assert first_player["predicted_points"] == 8.5
    
    @patch('src.api.main.prediction_engine')
    @patch('src.api.main.fpl_fetcher')
    def test_get_player_details(self, mock_fetcher, mock_engine):
        player_id = 123
        
        # Mock player data
        mock_players_df = pd.DataFrame([{
            'id': player_id,
            'web_name': 'Test Player',
            'name_team': 'Arsenal',
            'position': 'FWD',
            'now_cost': 100,
            'total_points': 150,
            'points_per_game': 7.5,
            'selected_by_percent': 25.5,
            'form': 8.2,
            'status': 'a'
        }])
        mock_fetcher.get_all_players_data.return_value = mock_players_df
        
        # Mock player history
        mock_history_df = pd.DataFrame([
            {'total_points': 8, 'minutes': 90, 'kickoff_time': '2024-08-17'},
            {'total_points': 6, 'minutes': 90, 'kickoff_time': '2024-08-24'}
        ])
        mock_fetcher.get_player_detailed_stats.return_value = mock_history_df
        
        # Mock predictions
        mock_engine.cnn_predictor.predict_multiple_gameweeks.return_value = [8.0, 7.5, 6.0, 9.0, 7.0]
        
        response = client.get(f"/players/{player_id}/details")
        assert response.status_code == 200
        
        data = response.json()
        assert "player_info" in data
        assert "predictions" in data
        assert "recent_performance" in data
        
        player_info = data["player_info"]
        assert player_info["id"] == player_id
        assert player_info["name"] == "Test Player"
        assert player_info["team"] == "Arsenal"
        
        predictions = data["predictions"]
        assert "next_5_gameweeks" in predictions
        assert "average" in predictions
        assert len(predictions["next_5_gameweeks"]) == 5
    
    def test_get_player_details_not_found(self):
        with patch('src.api.main.fpl_fetcher') as mock_fetcher:
            mock_fetcher.get_all_players_data.return_value = pd.DataFrame()
            
            response = client.get("/players/999/details")
            assert response.status_code == 404
            assert "Player not found" in response.json()["detail"]
    
    @patch('src.api.main.prediction_engine')
    def test_optimize_squad(self, mock_engine):
        # Mock the optimization result
        mock_result = {
            'squad': {
                'squad': [
                    {'id': 1, 'name': 'Player1', 'position': 'GK', 'price': 5.0, 'predicted_points': 120},
                    {'id': 2, 'name': 'Player2', 'position': 'DEF', 'price': 6.0, 'predicted_points': 140}
                ],
                'total_cost': 85.5,
                'predicted_points': 1250,
                'optimization_status': 'optimal'
            }
        }
        mock_engine.optimize_team_selection.return_value = mock_result
        
        request_data = {"budget": 100.0}
        response = client.post("/optimize/squad", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "squad" in data
        assert "total_cost" in data
        assert "predicted_points" in data
        assert "optimization_status" in data
        assert data["optimization_status"] == "optimal"
    
    @patch('src.api.main.prediction_engine')
    def test_optimize_starting_eleven(self, mock_engine):
        # Mock gameweek predictions
        mock_engine.get_single_gameweek_predictions.return_value = {
            1: 4.5, 2: 5.0, 3: 6.0
        }
        
        # Mock starting 11 optimization
        mock_result = {
            'starting_11': [
                {'id': 1, 'name': 'Player1', 'position': 'GK'},
                {'id': 2, 'name': 'Player2', 'position': 'DEF'}
            ],
            'formation': {'GK': 1, 'DEF': 4, 'MID': 3, 'FWD': 3},
            'captain': {'id': 3, 'name': 'Captain'},
            'vice_captain': {'id': 2, 'name': 'Vice'},
            'bench': [{'id': 4, 'name': 'Bench1'}],
            'predicted_points': 65.5
        }
        mock_engine.team_optimizer.optimize_starting_11.return_value = mock_result
        
        squad_data = [
            {'id': 1, 'name': 'Player1', 'position': 'GK'},
            {'id': 2, 'name': 'Player2', 'position': 'DEF'}
        ]
        
        response = client.post("/optimize/starting11", json=squad_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "starting_11" in data
        assert "formation" in data
        assert "captain" in data
        assert "vice_captain" in data
    
    @patch('src.api.main.prediction_engine')
    def test_suggest_transfers(self, mock_engine):
        mock_suggestions = {
            'suggested_transfers': [
                {
                    'out': {'id': 1, 'name': 'Player1'},
                    'in': {'id': 2, 'name': 'Player2'},
                    'points_gain': 2.5,
                    'cost': 0.5
                }
            ],
            'wildcard_suggestion': {
                'recommended': False,
                'points_improvement': 5.0
            }
        }
        mock_engine.get_transfer_suggestions.return_value = mock_suggestions
        
        request_data = {
            'team_id': 12345,
            'gameweek': 10,
            'free_transfers': 1
        }
        
        response = client.post("/transfers/suggest", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "suggested_transfers" in data
        assert "wildcard_suggestion" in data
        assert len(data["suggested_transfers"]) == 1
    
    @patch('src.api.main.fpl_fetcher')
    def test_get_current_gameweek(self, mock_fetcher):
        mock_bootstrap_data = {
            'events': [
                {'id': 10, 'name': 'Gameweek 10', 'is_current': True, 'deadline_time': '2024-08-17T14:00:00Z', 'finished': False},
                {'id': 11, 'name': 'Gameweek 11', 'is_current': False, 'deadline_time': '2024-08-24T14:00:00Z', 'finished': False}
            ]
        }
        mock_fetcher.get_bootstrap_data.return_value = mock_bootstrap_data
        
        response = client.get("/gameweek/current")
        assert response.status_code == 200
        
        data = response.json()
        assert "gameweek" in data
        assert "name" in data
        assert "deadline" in data
        assert data["gameweek"] == 10
        assert data["is_current"] == True
    
    @patch('src.api.main.fpl_fetcher')
    def test_get_current_gameweek_no_current(self, mock_fetcher):
        # Test when no gameweek is marked as current
        mock_bootstrap_data = {
            'events': [
                {'id': 10, 'name': 'Gameweek 10', 'is_current': False, 'is_next': True, 'deadline_time': '2024-08-17T14:00:00Z'},
                {'id': 11, 'name': 'Gameweek 11', 'is_current': False, 'is_next': False, 'deadline_time': '2024-08-24T14:00:00Z'}
            ]
        }
        mock_fetcher.get_bootstrap_data.return_value = mock_bootstrap_data
        
        response = client.get("/gameweek/current")
        assert response.status_code == 200
        
        data = response.json()
        assert data["gameweek"] == 10  # Should pick the next gameweek
    
    @patch('src.api.main.prediction_engine')
    def test_retrain_models(self, mock_engine):
        response = client.post("/models/retrain")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "background" in data["message"]
    
    def test_api_error_handling(self):
        # Test with invalid endpoint
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404
    
    @patch('src.api.main.prediction_engine')
    def test_prediction_endpoint_error(self, mock_engine):
        # Test when prediction engine raises an exception
        mock_engine.get_player_predictions.side_effect = Exception("Prediction error")
        
        response = client.get("/players/predictions")
        assert response.status_code == 500
        assert "Prediction error" in response.json()["detail"]
    
    def test_invalid_request_data(self):
        # Test with invalid JSON data
        response = client.post("/optimize/squad", json={"invalid": "data"})
        # Should still work with default values or handle gracefully
        assert response.status_code in [200, 422, 500]  # Different possible outcomes
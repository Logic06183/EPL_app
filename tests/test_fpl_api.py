import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import requests
from src.data.fpl_api import FPLDataFetcher

class TestFPLDataFetcher:
    
    @pytest.fixture
    def fetcher(self):
        return FPLDataFetcher()
    
    def test_initialization(self, fetcher):
        assert fetcher.base_url == "https://fantasy.premierleague.com/api"
        assert fetcher.session is not None
    
    @patch('requests.Session.get')
    def test_get_bootstrap_data_success(self, mock_get, fetcher):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'elements': [{'id': 1, 'web_name': 'Test Player'}],
            'teams': [{'id': 1, 'name': 'Test Team'}],
            'events': [{'id': 1, 'name': 'Gameweek 1'}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetcher.get_bootstrap_data()
        
        assert 'elements' in result
        assert 'teams' in result
        assert 'events' in result
        assert result['elements'][0]['id'] == 1
    
    @patch('requests.Session.get')
    def test_get_bootstrap_data_failure(self, mock_get, fetcher):
        mock_get.side_effect = requests.RequestException("API Error")
        
        with pytest.raises(requests.RequestException):
            fetcher.get_bootstrap_data()
    
    @patch('requests.Session.get')
    def test_get_player_history(self, mock_get, fetcher):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'history': [
                {'total_points': 8, 'minutes': 90, 'goals_scored': 1},
                {'total_points': 2, 'minutes': 90, 'goals_scored': 0}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetcher.get_player_history(123)
        
        assert 'history' in result
        assert len(result['history']) == 2
        assert result['history'][0]['total_points'] == 8
    
    @patch('requests.Session.get')
    def test_get_fixtures(self, mock_get, fetcher):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 1, 'team_h': 1, 'team_a': 2, 'event': 1},
            {'id': 2, 'team_h': 3, 'team_a': 4, 'event': 1}
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetcher.get_fixtures()
        
        assert len(result) == 2
        assert result[0]['team_h'] == 1
    
    @patch('requests.Session.get')
    def test_get_fixtures_with_gameweek(self, mock_get, fetcher):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 1, 'team_h': 1, 'team_a': 2, 'event': 5}
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetcher.get_fixtures(gameweek=5)
        
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs['params'] == {'event': 5}
    
    @patch.object(FPLDataFetcher, 'get_bootstrap_data')
    def test_get_all_players_data(self, mock_bootstrap, fetcher):
        mock_bootstrap.return_value = {
            'elements': [
                {'id': 1, 'web_name': 'Player1', 'team': 1, 'element_type': 4},
                {'id': 2, 'web_name': 'Player2', 'team': 2, 'element_type': 3}
            ],
            'teams': [
                {'id': 1, 'name': 'Arsenal', 'short_name': 'ARS'},
                {'id': 2, 'name': 'Liverpool', 'short_name': 'LIV'}
            ]
        }
        
        result = fetcher.get_all_players_data()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'position' in result.columns
        assert result.iloc[0]['position'] == 'FWD'  # element_type 4 = FWD
        assert result.iloc[1]['position'] == 'MID'  # element_type 3 = MID
    
    @patch.object(FPLDataFetcher, 'get_player_history')
    def test_get_player_detailed_stats(self, mock_history, fetcher):
        mock_history.return_value = {
            'history': [
                {
                    'kickoff_time': '2024-08-17T14:00:00Z',
                    'total_points': 8,
                    'minutes': 90
                },
                {
                    'kickoff_time': '2024-08-24T16:30:00Z',
                    'total_points': 2,
                    'minutes': 45
                }
            ]
        }
        
        result = fetcher.get_player_detailed_stats(123)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'kickoff_time' in result.columns
        assert pd.api.types.is_datetime64_any_dtype(result['kickoff_time'])
        
        # Check if sorted by kickoff_time
        assert result.iloc[0]['total_points'] == 8
    
    def test_position_mapping(self, fetcher):
        position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        
        for element_type, position in position_map.items():
            with patch.object(fetcher, 'get_bootstrap_data') as mock_bootstrap:
                mock_bootstrap.return_value = {
                    'elements': [{'id': 1, 'element_type': element_type, 'team': 1}],
                    'teams': [{'id': 1, 'name': 'Test', 'short_name': 'TST'}]
                }
                
                result = fetcher.get_all_players_data()
                assert result.iloc[0]['position'] == position
import pytest
import os
import tempfile
import pandas as pd
import numpy as np
from unittest.mock import patch

# Set test environment
os.environ['TESTING'] = 'True'

@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def sample_fpl_bootstrap():
    """Sample FPL bootstrap data"""
    return {
        'elements': [
            {
                'id': 1,
                'web_name': 'Haaland',
                'first_name': 'Erling',
                'second_name': 'Haaland',
                'team': 11,
                'element_type': 4,
                'now_cost': 150,
                'selected_by_percent': '45.2',
                'total_points': 180,
                'points_per_game': '9.5',
                'form': '8.2',
                'status': 'a',
                'minutes': 1800,
                'goals_scored': 20,
                'assists': 5,
                'clean_sheets': 0,
                'goals_conceded': 0,
                'influence': '95.2',
                'creativity': '45.8',
                'threat': '88.9',
                'ict_index': '18.5',
                'expected_goals': '18.5',
                'expected_assists': '4.2',
                'expected_goal_involvements': '22.7',
                'expected_goals_conceded': '0.0',
                'value': 15.0
            },
            {
                'id': 2,
                'web_name': 'Salah',
                'first_name': 'Mohamed',
                'second_name': 'Salah',
                'team': 12,
                'element_type': 3,
                'now_cost': 130,
                'selected_by_percent': '38.7',
                'total_points': 165,
                'points_per_game': '8.7',
                'form': '7.8',
                'status': 'a',
                'minutes': 1890,
                'goals_scored': 15,
                'assists': 12,
                'clean_sheets': 0,
                'goals_conceded': 0,
                'influence': '88.4',
                'creativity': '92.1',
                'threat': '85.3',
                'ict_index': '17.8',
                'expected_goals': '14.2',
                'expected_assists': '11.8',
                'expected_goal_involvements': '26.0',
                'expected_goals_conceded': '0.0',
                'value': 13.0
            }
        ],
        'teams': [
            {'id': 11, 'name': 'Manchester City', 'short_name': 'MCI'},
            {'id': 12, 'name': 'Liverpool', 'short_name': 'LIV'}
        ],
        'events': [
            {
                'id': 1,
                'name': 'Gameweek 1',
                'is_current': False,
                'is_next': False,
                'deadline_time': '2024-08-17T10:00:00Z',
                'finished': True
            },
            {
                'id': 10,
                'name': 'Gameweek 10',
                'is_current': True,
                'is_next': False,
                'deadline_time': '2024-10-19T10:00:00Z',
                'finished': False
            },
            {
                'id': 11,
                'name': 'Gameweek 11',
                'is_current': False,
                'is_next': True,
                'deadline_time': '2024-10-26T10:00:00Z',
                'finished': False
            }
        ]
    }

@pytest.fixture
def sample_player_history():
    """Sample player history data"""
    return pd.DataFrame([
        {
            'kickoff_time': '2024-08-17T14:00:00Z',
            'total_points': 8,
            'goals_scored': 1,
            'assists': 0,
            'clean_sheets': 0,
            'goals_conceded': 2,
            'minutes': 90,
            'influence': 75.5,
            'creativity': 25.2,
            'threat': 85.3,
            'ict_index': 15.2,
            'expected_goals': 0.8,
            'expected_assists': 0.2,
            'expected_goal_involvements': 1.0,
            'expected_goals_conceded': 1.8,
            'value': 15.0
        },
        {
            'kickoff_time': '2024-08-24T16:30:00Z',
            'total_points': 12,
            'goals_scored': 2,
            'assists': 1,
            'clean_sheets': 0,
            'goals_conceded': 1,
            'minutes': 90,
            'influence': 92.1,
            'creativity': 45.8,
            'threat': 95.2,
            'ict_index': 18.8,
            'expected_goals': 1.5,
            'expected_assists': 0.8,
            'expected_goal_involvements': 2.3,
            'expected_goals_conceded': 1.2,
            'value': 15.0
        }
    ])

@pytest.fixture
def sample_training_data():
    """Generate sample training data for model testing"""
    np.random.seed(42)
    
    data = []
    players = ['Haaland', 'Salah', 'Kane', 'Son', 'De Bruyne']
    
    for player in players:
        for gameweek in range(1, 21):  # 20 gameweeks
            data.append({
                'name': player,
                'kickoff_time': f'2024-08-{17 + (gameweek-1)*7:02d}T14:00:00Z',
                'total_points': np.random.randint(0, 15),
                'goals_scored': np.random.randint(0, 3),
                'assists': np.random.randint(0, 2),
                'clean_sheets': np.random.randint(0, 1),
                'goals_conceded': np.random.randint(0, 3),
                'minutes': np.random.choice([0, 45, 90]),
                'influence': np.random.uniform(20, 100),
                'creativity': np.random.uniform(10, 100),
                'threat': np.random.uniform(15, 100),
                'ict_index': np.random.uniform(5, 20),
                'expected_goals': np.random.uniform(0, 2),
                'expected_assists': np.random.uniform(0, 2),
                'expected_goal_involvements': np.random.uniform(0, 3),
                'expected_goals_conceded': np.random.uniform(0, 2),
                'value': np.random.uniform(5.0, 15.0)
            })
    
    return pd.DataFrame(data)

@pytest.fixture
def mock_sentiment_data():
    """Mock sentiment analysis data"""
    return {
        'player_name': 'Haaland',
        'sentiment_score': 0.25,
        'sentiment_label': 'positive',
        'sample_size': 150,
        'positive_ratio': 0.65,
        'negative_ratio': 0.15,
        'sources': {
            'twitter': 100,
            'news': 50
        },
        'recent_headlines': [
            'Haaland scores hat-trick in training',
            'City striker looking sharp',
            'Norwegian forward ready for weekend'
        ]
    }

@pytest.fixture(autouse=True)
def disable_external_calls():
    """Disable external API calls during testing"""
    with patch('requests.Session.get') as mock_get:
        mock_get.side_effect = Exception("External API calls disabled in tests")
        yield mock_get

@pytest.fixture
def mock_tensorflow_model():
    """Mock TensorFlow model for testing"""
    with patch('tensorflow.keras.models.Sequential') as mock_model:
        mock_instance = mock_model.return_value
        mock_instance.compile.return_value = None
        mock_instance.fit.return_value.history = {'loss': [0.5, 0.3], 'val_loss': [0.6, 0.4]}
        mock_instance.predict.return_value = np.array([[6.5]])
        mock_instance.save.return_value = None
        yield mock_instance

@pytest.fixture
def optimization_test_data():
    """Data specifically for testing optimization algorithms"""
    players = []
    
    # Create a balanced set of players for optimization testing
    positions_data = [
        ('GK', 5, 45, 55),    # 5 goalkeepers, 4.5-5.5m
        ('DEF', 15, 40, 70),  # 15 defenders, 4.0-7.0m
        ('MID', 20, 50, 120), # 20 midfielders, 5.0-12.0m
        ('FWD', 10, 60, 140)  # 10 forwards, 6.0-14.0m
    ]
    
    player_id = 1
    for position, count, min_cost, max_cost in positions_data:
        for i in range(count):
            players.append({
                'id': player_id,
                'web_name': f'{position}_{i+1}',
                'team': (player_id % 20) + 1,  # Distribute across 20 teams
                'position': position,
                'now_cost': np.random.randint(min_cost, max_cost),
                'selected_by_percent': np.random.uniform(1.0, 30.0),
                'total_points': np.random.randint(50, 200),
                'points_per_game': np.random.uniform(3.0, 8.0),
                'form': np.random.uniform(3.0, 8.0),
                'status': 'a'
            })
            player_id += 1
    
    return pd.DataFrame(players)

@pytest.fixture
def realistic_predictions():
    """Generate realistic prediction scores for testing"""
    def _generate_predictions(player_df):
        predictions = {}
        for _, player in player_df.iterrows():
            # Base prediction on position and current points
            base_score = {
                'GK': np.random.uniform(3.0, 6.0),
                'DEF': np.random.uniform(3.5, 7.0),
                'MID': np.random.uniform(4.0, 9.0),
                'FWD': np.random.uniform(4.5, 10.0)
            }.get(player.get('position', 'MID'), 5.0)
            
            # Add some randomness
            predictions[player['id']] = base_score + np.random.uniform(-1.0, 1.0)
        
        return predictions
    
    return _generate_predictions

# Configure pytest
def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "api: marks tests as API tests")
import pytest
import numpy as np
import pandas as pd
import tempfile
import os
from unittest.mock import patch, MagicMock
from src.models.cnn_predictor import CNNPlayerPredictor

class TestCNNPlayerPredictor:
    
    @pytest.fixture
    def predictor(self):
        return CNNPlayerPredictor(sequence_length=6, feature_dim=15)
    
    @pytest.fixture
    def sample_data(self):
        np.random.seed(42)
        
        data = []
        players = ['Player_A', 'Player_B', 'Player_C']
        
        for player in players:
            for i in range(10):  # 10 gameweeks per player
                row = {
                    'name': player,
                    'kickoff_time': f'2024-08-{17 + i:02d}T14:00:00Z',
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
                }
                data.append(row)
        
        return pd.DataFrame(data)
    
    def test_initialization(self, predictor):
        assert predictor.sequence_length == 6
        assert predictor.feature_dim == 15
        assert predictor.model is None
        assert len(predictor.feature_columns) == 15
    
    def test_build_model(self, predictor):
        model = predictor.build_model()
        
        assert model is not None
        assert predictor.model is not None
        assert len(model.layers) > 0
        
        # Check input shape
        expected_input_shape = (6, 15)
        assert model.input_shape[1:] == expected_input_shape
        
        # Check output shape (should be 1 for single point prediction)
        assert model.output_shape[1:] == (1,)
    
    def test_prepare_sequences(self, predictor, sample_data):
        X, y = predictor.prepare_sequences(sample_data)
        
        assert isinstance(X, np.ndarray)
        assert isinstance(y, np.ndarray)
        assert X.ndim == 3  # (samples, sequence_length, features)
        assert y.ndim == 1  # (samples,)
        
        # Each player has 10 gameweeks, so should have 4 sequences (10-6)
        # With 3 players: 3 * 4 = 12 sequences
        assert X.shape[0] == 12
        assert X.shape[1] == 6  # sequence_length
        assert X.shape[2] == 15  # feature_dim
        assert y.shape[0] == 12
    
    def test_prepare_sequences_insufficient_data(self, predictor):
        # Create data with insufficient history
        short_data = pd.DataFrame({
            'name': ['Player_X'] * 3,
            'kickoff_time': ['2024-08-17T14:00:00Z', '2024-08-18T14:00:00Z', '2024-08-19T14:00:00Z'],
            'total_points': [5, 3, 8]
        })
        
        # Add missing columns with default values
        for col in predictor.feature_columns:
            if col not in short_data.columns:
                short_data[col] = 0
        
        X, y = predictor.prepare_sequences(short_data)
        
        # Should return empty arrays since not enough data
        assert X.shape[0] == 0
        assert y.shape[0] == 0
    
    @patch('tensorflow.keras.models.Model.fit')
    def test_train(self, mock_fit, predictor, sample_data):
        # Mock the fit method to avoid actual training
        mock_history = MagicMock()
        mock_history.history = {'loss': [0.5, 0.3], 'val_loss': [0.6, 0.4]}
        mock_fit.return_value = mock_history
        
        # Split data
        split_idx = len(sample_data) // 2
        train_df = sample_data.iloc[:split_idx]
        val_df = sample_data.iloc[split_idx:]
        
        predictor.build_model()
        history = predictor.train(train_df, val_df, epochs=2)
        
        assert history == mock_history
        mock_fit.assert_called_once()
    
    def test_predict_insufficient_history(self, predictor):
        # Test with insufficient history
        short_history = pd.DataFrame({
            'total_points': [5, 3],
            'goals_scored': [1, 0],
        })
        
        # Add missing columns
        for col in predictor.feature_columns:
            if col not in short_history.columns:
                short_history[col] = 0
        
        prediction = predictor.predict(short_history)
        assert prediction == 0.0
    
    @patch.object(CNNPlayerPredictor, 'predict')
    def test_predict_multiple_gameweeks(self, mock_predict, predictor, sample_data):
        mock_predict.side_effect = [5.0, 4.5, 6.0, 3.5, 7.0]
        
        player_history = sample_data[sample_data['name'] == 'Player_A']
        predictions = predictor.predict_multiple_gameweeks(player_history, n_gameweeks=5)
        
        assert len(predictions) == 5
        assert predictions == [5.0, 4.5, 6.0, 3.5, 7.0]
        assert mock_predict.call_count == 5
    
    def test_save_and_load_model(self, predictor):
        with tempfile.TemporaryDirectory() as temp_dir:
            predictor.build_model()
            
            # Save model
            predictor.save_model(temp_dir)
            
            # Check files exist
            assert os.path.exists(os.path.join(temp_dir, 'cnn_model.h5'))
            assert os.path.exists(os.path.join(temp_dir, 'scaler.pkl'))
            
            # Create new predictor and load model
            new_predictor = CNNPlayerPredictor(sequence_length=6, feature_dim=15)
            new_predictor.load_model(temp_dir)
            
            assert new_predictor.model is not None
            assert new_predictor.scaler is not None
    
    def test_feature_columns_completeness(self, predictor):
        expected_features = [
            'total_points', 'goals_scored', 'assists', 'clean_sheets',
            'goals_conceded', 'minutes', 'influence', 'creativity', 
            'threat', 'ict_index', 'expected_goals', 'expected_assists',
            'expected_goal_involvements', 'expected_goals_conceded', 'value'
        ]
        
        assert predictor.feature_columns == expected_features
        assert len(predictor.feature_columns) == predictor.feature_dim
    
    def test_model_architecture(self, predictor):
        model = predictor.build_model()
        
        # Check for expected layer types
        layer_types = [type(layer).__name__ for layer in model.layers]
        
        assert 'Conv1D' in layer_types
        assert 'BatchNormalization' in layer_types
        assert 'MaxPooling1D' in layer_types
        assert 'Dense' in layer_types
        assert 'Dropout' in layer_types
    
    def test_prediction_bounds(self, predictor, sample_data):
        # Mock model prediction
        predictor.build_model()
        
        with patch.object(predictor.model, 'predict') as mock_predict:
            # Test negative prediction gets clipped to 0
            mock_predict.return_value = np.array([[-2.5]])
            
            player_history = sample_data[sample_data['name'] == 'Player_A'].tail(6)
            prediction = predictor.predict(player_history)
            
            assert prediction == 0.0  # Should be clipped to 0
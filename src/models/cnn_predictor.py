import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
import numpy as np
import pandas as pd
from typing import Tuple, List
from sklearn.preprocessing import StandardScaler
import joblib
import logging

logger = logging.getLogger(__name__)

class CNNPlayerPredictor:
    def __init__(self, sequence_length: int = 6, feature_dim: int = 15):
        self.sequence_length = sequence_length
        self.feature_dim = feature_dim
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = [
            'total_points', 'goals_scored', 'assists', 'clean_sheets',
            'goals_conceded', 'minutes', 'influence', 'creativity', 
            'threat', 'ict_index', 'expected_goals', 'expected_assists',
            'expected_goal_involvements', 'expected_goals_conceded', 'value'
        ]
        
    def build_model(self) -> keras.Model:
        model = models.Sequential([
            layers.Conv1D(
                filters=64, 
                kernel_size=3, 
                activation='relu',
                input_shape=(self.sequence_length, self.feature_dim)
            ),
            layers.BatchNormalization(),
            layers.MaxPooling1D(pool_size=2),
            
            layers.Conv1D(filters=128, kernel_size=3, activation='relu'),
            layers.BatchNormalization(),
            layers.GlobalMaxPooling1D(),
            
            layers.Dense(256, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(64, activation='relu'),
            
            layers.Dense(1, activation='linear')
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae', 'mape']
        )
        
        self.model = model
        return model
    
    def prepare_sequences(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        df = df.sort_values(['name', 'kickoff_time'])
        
        X, y = [], []
        
        for player in df['name'].unique():
            player_data = df[df['name'] == player]
            
            if len(player_data) < self.sequence_length + 1:
                continue
            
            features = player_data[self.feature_columns].fillna(0).values
            
            for i in range(len(features) - self.sequence_length):
                X.append(features[i:i + self.sequence_length])
                y.append(features[i + self.sequence_length, 0])
        
        return np.array(X), np.array(y)
    
    def train(self, train_df: pd.DataFrame, val_df: pd.DataFrame, epochs: int = 50):
        X_train, y_train = self.prepare_sequences(train_df)
        X_val, y_val = self.prepare_sequences(val_df)
        
        X_train_flat = X_train.reshape(-1, self.feature_dim)
        self.scaler.fit(X_train_flat)
        
        X_train_scaled = self.scaler.transform(X_train_flat).reshape(X_train.shape)
        X_val_scaled = self.scaler.transform(X_val.reshape(-1, self.feature_dim)).reshape(X_val.shape)
        
        if self.model is None:
            self.build_model()
        
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        reduce_lr = keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=0.00001
        )
        
        history = self.model.fit(
            X_train_scaled, y_train,
            validation_data=(X_val_scaled, y_val),
            epochs=epochs,
            batch_size=32,
            callbacks=[early_stopping, reduce_lr],
            verbose=1
        )
        
        return history
    
    def predict(self, player_history: pd.DataFrame) -> float:
        if len(player_history) < self.sequence_length:
            logger.warning(f"Insufficient history for prediction (need {self.sequence_length} gameweeks)")
            return 0.0
        
        recent_data = player_history.tail(self.sequence_length)
        features = recent_data[self.feature_columns].fillna(0).values
        
        X = features.reshape(1, self.sequence_length, self.feature_dim)
        X_scaled = self.scaler.transform(X.reshape(-1, self.feature_dim)).reshape(X.shape)
        
        prediction = self.model.predict(X_scaled, verbose=0)[0, 0]
        
        return max(0, prediction)
    
    def predict_multiple_gameweeks(self, player_history: pd.DataFrame, n_gameweeks: int = 5) -> List[float]:
        predictions = []
        history = player_history.copy()
        
        for _ in range(n_gameweeks):
            pred = self.predict(history)
            predictions.append(pred)
            
            new_row = history.iloc[-1:].copy()
            new_row['total_points'] = pred
            history = pd.concat([history, new_row], ignore_index=True)
        
        return predictions
    
    def save_model(self, path: str):
        self.model.save(f"{path}/cnn_model.h5")
        joblib.dump(self.scaler, f"{path}/scaler.pkl")
        
    def load_model(self, path: str):
        self.model = keras.models.load_model(f"{path}/cnn_model.h5")
        self.scaler = joblib.load(f"{path}/scaler.pkl")
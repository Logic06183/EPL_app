import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import Tuple, List
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PlayerSequenceDataset(Dataset):
    """Dataset class for player sequence data"""
    
    def __init__(self, sequences, targets):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]

class CNN1DPredictor(nn.Module):
    """1D CNN for player performance prediction"""
    
    def __init__(self, input_dim=15, sequence_length=6):
        super(CNN1DPredictor, self).__init__()
        
        self.conv_layers = nn.Sequential(
            # First conv block
            nn.Conv1d(input_dim, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Dropout(0.2),
            
            # Second conv block
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.GlobalMaxPool1d(),
        )
        
        # Calculate the size after conv layers
        self.fc_layers = nn.Sequential(
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
    def forward(self, x):
        # Input shape: (batch_size, sequence_length, features)
        # Conv1d expects: (batch_size, features, sequence_length)
        x = x.transpose(1, 2)
        
        x = self.conv_layers(x)
        x = x.view(x.size(0), -1)  # Flatten
        x = self.fc_layers(x)
        
        return x.squeeze()

class PyTorchPlayerPredictor:
    def __init__(self, sequence_length: int = 6, feature_dim: int = 15):
        self.sequence_length = sequence_length
        self.feature_dim = feature_dim
        self.model = None
        self.scaler = StandardScaler()
        self.device = 'mps' if torch.backends.mps.is_available() else 'cpu'
        
        self.feature_columns = [
            'total_points', 'goals_scored', 'assists', 'clean_sheets',
            'goals_conceded', 'minutes', 'influence', 'creativity', 
            'threat', 'ict_index', 'expected_goals', 'expected_assists',
            'expected_goal_involvements', 'expected_goals_conceded', 'value'
        ]
        
        logger.info(f"PyTorch predictor initialized on device: {self.device}")
        
    def build_model(self) -> nn.Module:
        """Build the CNN model"""
        self.model = CNN1DPredictor(
            input_dim=self.feature_dim,
            sequence_length=self.sequence_length
        )
        self.model.to(self.device)
        
        logger.info(f"Model built with {sum(p.numel() for p in self.model.parameters())} parameters")
        return self.model
    
    def prepare_sequences(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequential data for training"""
        df = df.sort_values(['name', 'kickoff_time'])
        
        X, y = [], []
        
        for player in df['name'].unique():
            player_data = df[df['name'] == player]
            
            if len(player_data) < self.sequence_length + 1:
                continue
            
            features = player_data[self.feature_columns].fillna(0).values
            
            for i in range(len(features) - self.sequence_length):
                X.append(features[i:i + self.sequence_length])
                y.append(features[i + self.sequence_length, 0])  # target is total_points
        
        return np.array(X), np.array(y)
    
    def train(self, train_df: pd.DataFrame, val_df: pd.DataFrame, epochs: int = 50, batch_size: int = 32):
        """Train the CNN model"""
        logger.info("Preparing training data...")
        X_train, y_train = self.prepare_sequences(train_df)
        X_val, y_val = self.prepare_sequences(val_df)
        
        if len(X_train) == 0:
            raise ValueError("No training sequences could be created. Check your data.")
        
        logger.info(f"Training sequences: {len(X_train)}, Validation sequences: {len(X_val)}")
        
        # Scale features
        X_train_flat = X_train.reshape(-1, self.feature_dim)
        self.scaler.fit(X_train_flat)
        
        X_train_scaled = self.scaler.transform(X_train_flat).reshape(X_train.shape)
        X_val_scaled = self.scaler.transform(X_val.reshape(-1, self.feature_dim)).reshape(X_val.shape)
        
        # Create datasets
        train_dataset = PlayerSequenceDataset(X_train_scaled, y_train)
        val_dataset = PlayerSequenceDataset(X_val_scaled, y_val)
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        # Initialize model if not already built
        if self.model is None:
            self.build_model()
        
        # Loss and optimizer
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
        
        # Training history
        history = {'train_loss': [], 'val_loss': [], 'train_mae': [], 'val_mae': []}
        best_val_loss = float('inf')
        patience_counter = 0
        
        logger.info(f"Starting training on {self.device} for {epochs} epochs...")
        
        for epoch in range(epochs):
            # Training phase
            self.model.train()
            train_loss = 0.0
            train_mae = 0.0
            
            for batch_X, batch_y in train_loader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)
                
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
                train_mae += torch.mean(torch.abs(outputs - batch_y)).item()
            
            # Validation phase
            self.model.eval()
            val_loss = 0.0
            val_mae = 0.0
            
            with torch.no_grad():
                for batch_X, batch_y in val_loader:
                    batch_X = batch_X.to(self.device)
                    batch_y = batch_y.to(self.device)
                    
                    outputs = self.model(batch_X)
                    loss = criterion(outputs, batch_y)
                    
                    val_loss += loss.item()
                    val_mae += torch.mean(torch.abs(outputs - batch_y)).item()
            
            # Average losses
            train_loss /= len(train_loader)
            val_loss /= len(val_loader)
            train_mae /= len(train_loader)
            val_mae /= len(val_loader)
            
            # Update history
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            history['train_mae'].append(train_mae)
            history['val_mae'].append(val_mae)
            
            # Learning rate scheduler
            scheduler.step(val_loss)
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Log progress
            if epoch % 5 == 0 or epoch == epochs - 1:
                logger.info(f"Epoch {epoch+1}/{epochs} - "
                          f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, "
                          f"Train MAE: {train_mae:.4f}, Val MAE: {val_mae:.4f}")
            
            # Early stopping
            if patience_counter >= 10:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break
        
        logger.info(f"Training completed. Best validation loss: {best_val_loss:.4f}")
        return history
    
    def predict(self, player_history: pd.DataFrame) -> float:
        """Predict next gameweek points for a player"""
        if self.model is None:
            logger.warning("Model not trained yet")
            return 0.0
            
        if len(player_history) < self.sequence_length:
            logger.warning(f"Insufficient history for prediction (need {self.sequence_length} gameweeks)")
            return 0.0
        
        recent_data = player_history.tail(self.sequence_length)
        features = recent_data[self.feature_columns].fillna(0).values
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(-1, self.feature_dim)).reshape(features.shape)
        
        # Convert to tensor and add batch dimension
        X = torch.FloatTensor(features_scaled).unsqueeze(0).to(self.device)
        
        self.model.eval()
        with torch.no_grad():
            prediction = self.model(X).cpu().item()
        
        return max(0, prediction)  # Ensure non-negative points
    
    def predict_multiple_gameweeks(self, player_history: pd.DataFrame, n_gameweeks: int = 5) -> List[float]:
        """Predict multiple future gameweeks"""
        predictions = []
        history = player_history.copy()
        
        for _ in range(n_gameweeks):
            pred = self.predict(history)
            predictions.append(pred)
            
            # Add predicted gameweek to history for next prediction
            new_row = history.iloc[-1:].copy()
            new_row['total_points'] = pred
            history = pd.concat([history, new_row], ignore_index=True)
        
        return predictions
    
    def save_model(self, path: str):
        """Save model and scaler"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        if self.model is not None:
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'model_params': {
                    'sequence_length': self.sequence_length,
                    'feature_dim': self.feature_dim
                }
            }, path / 'pytorch_model.pth')
            
        joblib.dump(self.scaler, path / 'scaler.pkl')
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load model and scaler"""
        path = Path(path)
        
        # Load model
        model_path = path / 'pytorch_model.pth'
        if model_path.exists():
            checkpoint = torch.load(model_path, map_location=self.device)
            
            # Build model with saved parameters
            self.sequence_length = checkpoint['model_params']['sequence_length']
            self.feature_dim = checkpoint['model_params']['feature_dim']
            
            self.model = CNN1DPredictor(
                input_dim=self.feature_dim,
                sequence_length=self.sequence_length
            ).to(self.device)
            
            self.model.load_state_dict(checkpoint['model_state_dict'])
            logger.info("Model loaded successfully")
        
        # Load scaler
        scaler_path = path / 'scaler.pkl'
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)
            logger.info("Scaler loaded successfully")

class GlobalMaxPool1d(nn.Module):
    """Global max pooling layer"""
    def forward(self, x):
        return torch.max(x, dim=2)[0]

# Monkey patch to add GlobalMaxPool1d to nn
nn.GlobalMaxPool1d = GlobalMaxPool1d
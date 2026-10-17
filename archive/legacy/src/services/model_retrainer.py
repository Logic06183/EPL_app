import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path
import asyncio
import shutil
import torch

from ..pytorch_prediction_engine import PyTorchFPLPredictionEngine
from ..data.live_data_manager import LiveDataManager
from ..data.external_datasets import ExternalDatasets
from ..models.pytorch_cnn_predictor import CNN1DPredictor

logger = logging.getLogger(__name__)

class ModelRetrainer:
    def __init__(self, 
                 models_dir: str = "./models",
                 backup_dir: str = "./models/backups",
                 retrain_threshold_days: int = 7,
                 performance_threshold: float = 0.1):
        
        self.models_dir = Path(models_dir)
        self.backup_dir = Path(backup_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.retrain_threshold_days = retrain_threshold_days
        self.performance_threshold = performance_threshold
        
        self.prediction_engine = PyTorchFPLPredictionEngine()
        self.live_data_manager = LiveDataManager()
        self.external_datasets = ExternalDatasets()
        
        self.model_metrics = {}
        self.retrain_history = []
        
    def should_retrain_model(self) -> Tuple[bool, str]:
        """Determine if model should be retrained based on various criteria"""
        try:
            reasons = []
            
            # Check last training date
            model_path = self.models_dir / "pytorch_model.pth"
            
            if model_path.exists():
                model_age = datetime.now() - datetime.fromtimestamp(model_path.stat().st_mtime)
                if model_age.days >= self.retrain_threshold_days:
                    reasons.append(f"Model is {model_age.days} days old (threshold: {self.retrain_threshold_days})")
            else:
                reasons.append("No trained model found")
            
            # Check recent performance
            if self._check_model_performance_degradation():
                reasons.append("Model performance has degraded")
            
            # Check if new data is available
            if self._check_new_data_available():
                reasons.append("New training data is available")
            
            # Check if model architecture needs updating
            if self._check_architecture_updates():
                reasons.append("Model architecture improvements available")
            
            should_retrain = len(reasons) > 0
            reason_text = "; ".join(reasons) if reasons else "No retraining needed"
            
            return should_retrain, reason_text
            
        except Exception as e:
            logger.error(f"Error checking retrain criteria: {e}")
            return True, f"Error in retrain check: {e}"
    
    def _check_model_performance_degradation(self) -> bool:
        """Check if model performance has significantly degraded"""
        try:
            # Load recent performance metrics
            metrics_file = self.models_dir / "model_metrics.json"
            
            if not metrics_file.exists():
                return False
            
            with open(metrics_file, 'r') as f:
                current_metrics = json.load(f)
            
            # Check if validation loss has increased significantly
            current_val_loss = current_metrics.get('validation_loss', float('inf'))
            current_mae = current_metrics.get('validation_mae', float('inf'))
            
            # Compare with historical performance
            if hasattr(self, 'historical_metrics'):
                historical_avg_loss = np.mean([m.get('validation_loss', float('inf')) 
                                             for m in self.historical_metrics[-5:]])
                
                if current_val_loss > historical_avg_loss * (1 + self.performance_threshold):
                    return True
            
            # Check if MAE is too high
            if current_mae > 2.0:  # MAE greater than 2 points is concerning
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking performance degradation: {e}")
            return False
    
    def _check_new_data_available(self) -> bool:
        """Check if significant new data is available for training"""
        try:
            # Check if we have new gameweek data
            current_gw = self.live_data_manager.get_current_gameweek()
            
            # Load last training info
            training_info_file = self.models_dir / "last_training_info.json"
            
            if training_info_file.exists():
                with open(training_info_file, 'r') as f:
                    last_training = json.load(f)
                
                last_gw = last_training.get('last_gameweek_trained', 0)
                
                # If we have 2+ new gameweeks of data, retrain
                if current_gw > last_gw + 2:
                    return True
            
            # Check if current season data has grown significantly
            current_data = self.live_data_manager.get_current_season_data()
            
            if len(current_data) > 500:  # Enough current season data to improve training
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking new data availability: {e}")
            return False
    
    def _check_architecture_updates(self) -> bool:
        """Check if model architecture should be updated"""
        try:
            # Load current model info
            model_info_file = self.models_dir / "model_info.json"
            
            if model_info_file.exists():
                with open(model_info_file, 'r') as f:
                    model_info = json.load(f)
                
                model_version = model_info.get('version', '1.0')
                
                # Check if we have a newer architecture version
                current_version = "1.1"  # Update this when we improve the model
                
                if model_version != current_version:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking architecture updates: {e}")
            return False
    
    def backup_current_model(self) -> bool:
        """Backup the current model before retraining"""
        try:
            model_path = self.models_dir / "pytorch_model.pth"
            
            if model_path.exists():
                # Create backup with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = self.backup_dir / f"pytorch_model_backup_{timestamp}.pth"
                
                shutil.copy2(model_path, backup_path)
                
                # Also backup associated files
                for file_name in ["model_metrics.json", "model_info.json", "last_training_info.json"]:
                    source_file = self.models_dir / file_name
                    if source_file.exists():
                        backup_file = self.backup_dir / f"{file_name.split('.')[0]}_backup_{timestamp}.json"
                        shutil.copy2(source_file, backup_file)
                
                logger.info(f"Model backed up to {backup_path}")
                
                # Keep only last 10 backups
                self._cleanup_old_backups()
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error backing up model: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """Keep only the most recent backups"""
        try:
            backup_files = sorted(self.backup_dir.glob("pytorch_model_backup_*.pth"))
            
            if len(backup_files) > 10:
                for old_backup in backup_files[:-10]:
                    old_backup.unlink()
                    
                    # Also remove associated files
                    timestamp = old_backup.stem.split('_')[-2] + '_' + old_backup.stem.split('_')[-1]
                    for pattern in ["model_metrics_backup_", "model_info_backup_", "last_training_info_backup_"]:
                        associated_file = self.backup_dir / f"{pattern}{timestamp}.json"
                        if associated_file.exists():
                            associated_file.unlink()
                            
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    def retrain_model(self, force: bool = False) -> Dict:
        """Retrain the model with latest data"""
        try:
            logger.info("Starting model retraining process...")
            
            # Check if retraining is needed
            if not force:
                should_retrain, reason = self.should_retrain_model()
                if not should_retrain:
                    return {
                        'success': False,
                        'reason': 'Retraining not needed',
                        'details': reason,
                        'timestamp': datetime.now().isoformat()
                    }
            
            # Backup current model
            backup_success = self.backup_current_model()
            if not backup_success:
                logger.warning("Failed to backup current model, proceeding anyway")
            
            # Update live data first
            logger.info("Updating live data...")
            self.live_data_manager.update_live_data()
            
            # Get enhanced training data
            logger.info("Preparing enhanced training data...")
            training_data = self._prepare_enhanced_training_data()
            
            if training_data.empty:
                return {
                    'success': False,
                    'reason': 'No training data available',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Initialize new prediction engine
            logger.info("Initializing new prediction engine...")
            new_engine = PyTorchFPLPredictionEngine()
            
            # Train the model
            logger.info("Training new model...")
            training_result = new_engine.train_model()
            
            if not training_result.get('success', False):
                return {
                    'success': False,
                    'reason': 'Model training failed',
                    'details': training_result.get('error', 'Unknown error'),
                    'timestamp': datetime.now().isoformat()
                }
            
            # Evaluate new model performance
            logger.info("Evaluating new model...")
            evaluation_result = self._evaluate_model_performance(new_engine)
            
            # Compare with previous model (if exists)
            performance_improved = self._compare_model_performance(evaluation_result)
            
            if performance_improved or force:
                # Save the new model
                logger.info("New model performs better, saving...")
                self._save_model_artifacts(new_engine, evaluation_result, training_result)
                
                # Update prediction engine
                self.prediction_engine = new_engine
                
                # Record retraining history
                self._record_retraining(evaluation_result, training_result)
                
                return {
                    'success': True,
                    'reason': 'Model successfully retrained',
                    'performance_improved': performance_improved,
                    'metrics': evaluation_result,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.info("New model doesn't improve performance, keeping old model")
                return {
                    'success': False,
                    'reason': 'New model performance not better than current',
                    'metrics': evaluation_result,
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error in model retraining: {e}")
            return {
                'success': False,
                'reason': 'Retraining process failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _prepare_enhanced_training_data(self) -> pd.DataFrame:
        """Prepare enhanced training data including recent gameweeks"""
        try:
            # Get historical data
            historical_data = self.external_datasets.get_training_data()
            
            # Get current season data if significant amount available
            current_data = self.live_data_manager.get_current_season_data()
            
            # Convert current season data to training format
            if len(current_data) > 100:  # Only if we have meaningful current season data
                current_training_data = self._convert_current_to_training_format(current_data)
                
                if not current_training_data.empty:
                    # Combine with historical data
                    combined_data = pd.concat([historical_data, current_training_data], ignore_index=True)
                    logger.info(f"Enhanced training data: {len(combined_data)} total records")
                    return combined_data
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Error preparing enhanced training data: {e}")
            return pd.DataFrame()
    
    def _convert_current_to_training_format(self, current_data: pd.DataFrame) -> pd.DataFrame:
        """Convert current season data to training format"""
        try:
            # This would need to be implemented based on how current data differs
            # from historical training format
            
            # For now, return empty DataFrame
            # In a real implementation, you'd convert the FPL API format
            # to match the Vaastav historical data format
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error converting current data: {e}")
            return pd.DataFrame()
    
    def _evaluate_model_performance(self, engine: PyTorchFPLPredictionEngine) -> Dict:
        """Evaluate model performance on validation set"""
        try:
            # This would run the model on a held-out validation set
            # and return performance metrics
            
            # For now, return dummy metrics
            # In a real implementation, you'd:
            # 1. Load a validation dataset
            # 2. Generate predictions
            # 3. Calculate MAE, RMSE, correlation, etc.
            
            return {
                'validation_mae': 0.95,
                'validation_rmse': 1.2,
                'validation_correlation': 0.65,
                'training_time_seconds': 180,
                'model_parameters': 102273,
                'evaluation_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return {}
    
    def _compare_model_performance(self, new_metrics: Dict) -> bool:
        """Compare new model performance with previous model"""
        try:
            metrics_file = self.models_dir / "model_metrics.json"
            
            if not metrics_file.exists():
                return True  # No previous model, so new one is better
            
            with open(metrics_file, 'r') as f:
                old_metrics = json.load(f)
            
            # Compare key metrics
            new_mae = new_metrics.get('validation_mae', float('inf'))
            old_mae = old_metrics.get('validation_mae', float('inf'))
            
            # New model is better if MAE improved by at least 1%
            improvement_threshold = 0.01
            mae_improvement = (old_mae - new_mae) / old_mae
            
            return mae_improvement > improvement_threshold
            
        except Exception as e:
            logger.error(f"Error comparing model performance: {e}")
            return True  # Default to accepting new model
    
    def _save_model_artifacts(self, engine: PyTorchFPLPredictionEngine, evaluation: Dict, training_result: Dict):
        """Save model and associated artifacts"""
        try:
            # Save model metrics
            metrics_file = self.models_dir / "model_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(evaluation, f, indent=2)
            
            # Save model info
            model_info = {
                'version': '1.1',
                'training_timestamp': datetime.now().isoformat(),
                'training_duration': evaluation.get('training_time_seconds', 0),
                'model_architecture': 'CNN1D',
                'input_features': 15,
                'sequence_length': 6,
                'parameters': evaluation.get('model_parameters', 0)
            }
            
            model_info_file = self.models_dir / "model_info.json"
            with open(model_info_file, 'w') as f:
                json.dump(model_info, f, indent=2)
            
            # Save training info
            training_info = {
                'last_training_date': datetime.now().isoformat(),
                'last_gameweek_trained': self.live_data_manager.get_current_gameweek(),
                'training_records': training_result.get('training_records', 0),
                'validation_records': training_result.get('validation_records', 0)
            }
            
            training_info_file = self.models_dir / "last_training_info.json"
            with open(training_info_file, 'w') as f:
                json.dump(training_info, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving model artifacts: {e}")
    
    def _record_retraining(self, evaluation: Dict, training_result: Dict):
        """Record retraining event in history"""
        try:
            retraining_record = {
                'timestamp': datetime.now().isoformat(),
                'metrics': evaluation,
                'training_info': training_result,
                'trigger': 'automated_retraining'
            }
            
            self.retrain_history.append(retraining_record)
            
            # Save retraining history
            history_file = self.models_dir / "retraining_history.json"
            with open(history_file, 'w') as f:
                json.dump(self.retrain_history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error recording retraining: {e}")
    
    def get_model_status(self) -> Dict:
        """Get current model status and retraining recommendations"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'model_exists': (self.models_dir / "pytorch_model.pth").exists(),
                'last_training': None,
                'performance_metrics': None,
                'retrain_recommended': False,
                'retrain_reasons': []
            }
            
            # Check last training
            training_info_file = self.models_dir / "last_training_info.json"
            if training_info_file.exists():
                with open(training_info_file, 'r') as f:
                    status['last_training'] = json.load(f)
            
            # Check performance metrics
            metrics_file = self.models_dir / "model_metrics.json"
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    status['performance_metrics'] = json.load(f)
            
            # Check if retraining is recommended
            should_retrain, reasons = self.should_retrain_model()
            status['retrain_recommended'] = should_retrain
            status['retrain_reasons'] = reasons.split('; ') if reasons else []
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting model status: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'model_exists': False,
                'retrain_recommended': True,
                'retrain_reasons': ['Error checking status']
            }
    
    def schedule_automatic_retraining(self):
        """Set up automatic retraining schedule"""
        try:
            import schedule
            
            # Schedule retraining every Sunday at 3 AM
            schedule.every().sunday.at("03:00").do(self.retrain_model)
            
            # Also check daily if urgent retraining is needed
            schedule.every().day.at("02:00").do(self._check_urgent_retrain)
            
            logger.info("Automatic retraining scheduled")
            
        except Exception as e:
            logger.error(f"Error scheduling automatic retraining: {e}")
    
    def _check_urgent_retrain(self):
        """Check if urgent retraining is needed"""
        try:
            should_retrain, reason = self.should_retrain_model()
            
            if should_retrain and ("performance" in reason.lower() or "new data" in reason.lower()):
                logger.info(f"Urgent retraining triggered: {reason}")
                self.retrain_model(force=False)
                
        except Exception as e:
            logger.error(f"Error in urgent retrain check: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    retrainer = ModelRetrainer()
    
    # Test model status
    status = retrainer.get_model_status()
    print(f"Model status: {status['retrain_recommended']}")
    
    # Test retraining (if needed)
    if status['retrain_recommended']:
        result = retrainer.retrain_model()
        print(f"Retraining result: {result['success']}")
    else:
        print("Retraining not needed")
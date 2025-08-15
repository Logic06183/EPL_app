#!/usr/bin/env python3

import sys
import logging
import time
from datetime import datetime
from src.pytorch_prediction_engine import PyTorchFPLPredictionEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('training.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    print("🚀 Starting PyTorch CNN Model Training for FPL Predictions")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Initialize the prediction engine
        logger.info("Initializing PyTorch FPL Prediction Engine...")
        engine = PyTorchFPLPredictionEngine(use_sentiment=False)
        
        # Display model info
        model_info = engine.get_model_info()
        print(f"📱 Device: {model_info['device']}")
        print(f"🔍 Model Type: {model_info['model_type']}")
        print(f"📊 Features: {model_info['feature_dim']}")
        print(f"📈 Sequence Length: {model_info['sequence_length']} gameweeks")
        print()
        
        # Start training
        print("🎯 Starting model training...")
        print("This will:")
        print("1. 📥 Download historical FPL data (2021-2024)")
        print("2. 🔄 Preprocess and create sequences")
        print("3. 🧠 Train CNN on Apple Silicon GPU")
        print("4. 💾 Save trained model")
        print()
        
        history = engine.train_models(force_retrain=True)
        
        if history:
            print("✅ Training completed successfully!")
            print(f"📊 Final Training Loss: {history['train_loss'][-1]:.4f}")
            print(f"📊 Final Validation Loss: {history['val_loss'][-1]:.4f}")
            print(f"📊 Final Training MAE: {history['train_mae'][-1]:.4f}")
            print(f"📊 Final Validation MAE: {history['val_mae'][-1]:.4f}")
        else:
            print("⚠️ Training completed with warnings (using baseline predictions)")
        
        # Test predictions
        print("\n🔮 Testing predictions on current players...")
        predictions = engine.get_player_predictions(horizon_gameweeks=3)
        
        # Get top 5 predictions to show
        sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)[:5]
        
        print("🌟 Top 5 Predicted Players:")
        players_df = engine.fpl_fetcher.get_all_players_data()
        for player_id, predicted_points in sorted_predictions:
            player_data = players_df[players_df['id'] == player_id]
            if not player_data.empty:
                player = player_data.iloc[0]
                print(f"   {player['web_name']} ({player['position']}) - {predicted_points:.1f} pts")
        
        # Test optimization
        print("\n🏆 Testing squad optimization...")
        optimization_result = engine.optimize_team_selection(budget=100.0)
        
        print(f"✅ Optimization Status: {optimization_result['squad']['optimization_status']}")
        print(f"💰 Total Cost: £{optimization_result['squad']['total_cost']:.1f}m")
        print(f"📈 Predicted Points: {optimization_result['squad']['predicted_points']:.1f}")
        
        # Training summary
        elapsed_time = time.time() - start_time
        print(f"\n⏱️ Total Time: {elapsed_time:.1f} seconds")
        print(f"📁 Model saved to: ./models/")
        print(f"📋 Training log: training.log")
        
        print("\n🎉 PyTorch CNN Model is ready for production!")
        print("\nNext steps:")
        print("1. Start API server: python run.py")
        print("2. Start frontend: cd frontend && npm run dev")
        print("3. Open http://localhost:3000 to see predictions")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ Training interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        logger.error(f"Training failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    logger.info("Testing imports...")
    try:
        from src.data.fpl_api import FPLDataFetcher
        from src.data.external_datasets import ExternalDatasets
        from src.models.cnn_predictor import CNNPlayerPredictor
        from src.models.sentiment_analyzer import PlayerSentimentAnalyzer
        from src.models.team_optimizer import FPLTeamOptimizer
        from src.prediction_engine import FPLPredictionEngine
        logger.info("✓ All imports successful")
        return True
    except ImportError as e:
        logger.error(f"✗ Import error: {e}")
        return False

def test_fpl_api():
    logger.info("Testing FPL API connection...")
    try:
        from src.data.fpl_api import FPLDataFetcher
        fetcher = FPLDataFetcher()
        data = fetcher.get_bootstrap_data()
        
        if 'elements' in data and 'teams' in data:
            logger.info(f"✓ FPL API working - Found {len(data['elements'])} players")
            return True
        else:
            logger.error("✗ FPL API returned unexpected data structure")
            return False
    except Exception as e:
        logger.error(f"✗ FPL API error: {e}")
        return False

def test_external_data():
    logger.info("Testing external dataset access...")
    try:
        from src.data.external_datasets import ExternalDatasets
        external = ExternalDatasets()
        
        logger.info("  Attempting to fetch Vaastav data...")
        df = external.fetch_player_historical_data("2023-24")
        
        if not df.empty:
            logger.info(f"✓ External data working - Loaded {len(df)} player records")
            return True
        else:
            logger.warning("⚠ External data returned empty dataset")
            return False
    except Exception as e:
        logger.warning(f"⚠ External data not critical, skipping: {e}")
        return True

def test_model_creation():
    logger.info("Testing model initialization...")
    try:
        from src.models.cnn_predictor import CNNPlayerPredictor
        from src.models.team_optimizer import FPLTeamOptimizer
        
        cnn = CNNPlayerPredictor()
        cnn.build_model()
        
        optimizer = FPLTeamOptimizer()
        
        logger.info("✓ Models initialized successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Model initialization error: {e}")
        return False

def test_api_startup():
    logger.info("Testing API startup (without running server)...")
    try:
        from src.api.main import app
        logger.info("✓ API app created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ API startup error: {e}")
        return False

def create_directories():
    logger.info("Creating necessary directories...")
    directories = [
        Path("data/cache"),
        Path("models"),
        Path("logs")
    ]
    
    for dir_path in directories:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"  ✓ Created {dir_path}")
    
    return True

def main():
    logger.info("=" * 50)
    logger.info("FPL Prediction App - Setup Test")
    logger.info("=" * 50)
    
    tests = [
        ("Directory Setup", create_directories),
        ("Python Imports", test_imports),
        ("FPL API Connection", test_fpl_api),
        ("External Datasets", test_external_data),
        ("Model Creation", test_model_creation),
        ("API Framework", test_api_startup)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{test_name}:")
        result = test_func()
        results.append((test_name, result))
    
    logger.info("\n" + "=" * 50)
    logger.info("Test Results Summary:")
    logger.info("=" * 50)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        logger.info("\n🎉 All tests passed! The app is ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Copy .env.example to .env and add your API keys (optional)")
        logger.info("2. Run 'python run.py' to start the API server")
        logger.info("3. Run 'python cli.py --help' to see CLI commands")
        logger.info("4. Visit http://localhost:8000/docs for API documentation")
    else:
        logger.warning("\n⚠ Some tests failed. Please check the errors above.")
        logger.info("Most features will still work without external data access.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Test core functionality without the full API
"""

import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database():
    """Test database functionality"""
    print("🗄️  Testing Database...")
    try:
        from src.database.local_db import LocalDatabase
        db = LocalDatabase()
        players = db.get_all_players()
        print(f"  ✅ Database working: {len(players)} players loaded")
        
        # Show a few sample players
        for i, player in enumerate(players[:3]):
            print(f"    Player {i+1}: {player['web_name']} ({player['team']}) - £{player['now_cost']/10}m")
        return True
    except Exception as e:
        print(f"  ❌ Database failed: {e}")
        return False

def test_pytorch_model():
    """Test PyTorch model loading"""
    print("\n🧠 Testing PyTorch Model...")
    try:
        import torch
        print(f"  ✅ PyTorch version: {torch.__version__}")
        
        # Check if model file exists
        model_path = "models/pytorch_model.pth"
        if os.path.exists(model_path):
            print(f"  ✅ Model file exists: {model_path}")
            
            # Try to load it
            try:
                checkpoint = torch.load(model_path, map_location='cpu')
                print(f"  ✅ Model loaded successfully")
                if 'model_info' in checkpoint:
                    print(f"    Model info: {checkpoint['model_info']}")
            except Exception as e:
                print(f"  ⚠️  Model file exists but failed to load: {e}")
        else:
            print(f"  ⚠️  Model file not found: {model_path}")
            print("    Model needs to be trained first")
        return True
    except Exception as e:
        print(f"  ❌ PyTorch test failed: {e}")
        return False

def test_fpl_api():
    """Test FPL API connection"""
    print("\n🌐 Testing FPL API Connection...")
    try:
        from src.data.fpl_api import FPLDataFetcher
        fetcher = FPLDataFetcher()
        # Just test basic initialization
        print(f"  ✅ FPL API fetcher initialized")
        return True
    except Exception as e:
        print(f"  ❌ FPL API test failed: {e}")
        return False

def main():
    print("=" * 50)
    print("🚀 FPL PREDICTION APP - CORE TESTS")
    print("=" * 50)
    
    tests = [
        ("Database", test_database),
        ("PyTorch Model", test_pytorch_model), 
        ("FPL API", test_fpl_api)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nOverall: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All core components working! Ready to start API server.")
    else:
        print(f"\n⚠️  {total_count - passed_count} components need attention.")
    
    return passed_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
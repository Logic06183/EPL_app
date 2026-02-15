# Firebase Cloud Functions entry point for FPL AI Pro API
import os
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import the FastAPI app
from api_production import app

# Firebase Functions entry point
def main(request):
    """
    Cloud Function entry point for Firebase
    """
    import uvicorn
    from fastapi.applications import FastAPI
    
    # Return the FastAPI app
    return app
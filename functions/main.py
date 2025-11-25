# Firebase Cloud Functions entry point for FPL AI Pro API
import os
import sys
from pathlib import Path
from firebase_functions import https_fn
from firebase_admin import initialize_app
import functions_framework
from mangum import Mangum

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Initialize Firebase Admin
initialize_app()

# Import the FastAPI app
from api_production import app

# Create Mangum handler
handler = Mangum(app)

# Expose the FastAPI app as a Cloud Function
@functions_framework.http
def api(request):
    """
    Cloud Function entry point for Firebase
    """
    return handler(request)
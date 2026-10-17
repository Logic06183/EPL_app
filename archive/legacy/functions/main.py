# Firebase Cloud Functions entry point for FPL AI Pro API
import os
import sys
from pathlib import Path
from firebase_functions import https_fn, options
from firebase_admin import initialize_app
from a2wsgi import ASGIMiddleware
import logging

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Initialize Firebase Admin
initialize_app()

# Expose the app as a Cloud Function using the Firebase SDK
@https_fn.on_request(
    region=options.SupportedRegion.US_CENTRAL1,
    memory=options.MemoryOption.GB_1,
    timeout_sec=300,
)
def api(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function entry point for Firebase
    """
    # Simple health check that bypasses the heavy app
    if req.path == "/ping" or req.path == "/api/ping":
        return https_fn.Response("pong")

    # Lazy import to avoid cold start timeouts
    from api_production import app
    
    # Convert FastAPI (ASGI) to WSGI
    # Note: We instantiate this once per container instance ideally, 
    # but for now let's do it here. Python caches module imports so 'app' is singleton.
    wsgi_app = ASGIMiddleware(app)
    
    return https_fn.Response.from_app(wsgi_app, req.environ)
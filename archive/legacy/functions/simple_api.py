#!/usr/bin/env python3
"""
Simple API server for FPL predictions - minimal dependencies
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from src.database.local_db import LocalDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="FPL Predictor API", 
    description="Simple FPL prediction API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = LocalDatabase()

@app.get("/")
async def root():
    """API root - basic info"""
    return {
        "message": "FPL Prediction API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/players": "Get all players",
            "/predictions": "Get sample predictions"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        players = db.get_all_players()
        return {
            "status": "healthy",
            "database": "connected",
            "players_count": len(players),
            "timestamp": "2024-08-15T12:00:00Z"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e)
        }

@app.get("/players")
async def get_players():
    """Get all players from database"""
    try:
        players = db.get_all_players()
        return {
            "players": players,
            "count": len(players)
        }
    except Exception as e:
        logger.error(f"Failed to get players: {e}")
        return {"error": str(e)}

@app.get("/predictions")
async def get_predictions():
    """Get sample predictions"""
    try:
        # Get sample predictions from database
        user_predictions = db.get_user_predictions(1, gameweek=15)  # Demo user
        return {
            "predictions": user_predictions,
            "count": len(user_predictions),
            "gameweek": 15
        }
    except Exception as e:
        logger.error(f"Failed to get predictions: {e}")
        return {"error": str(e)}

@app.get("/gameweek/current")
async def get_current_gameweek():
    """Get current gameweek info"""
    return {
        "gameweek": 15,
        "is_current": True,
        "deadline": "2024-08-17T11:30:00Z",
        "finished": False
    }

def main():
    logger.info("Starting Simple FPL API")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()
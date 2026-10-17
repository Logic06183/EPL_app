"""
Lightweight API for Cloud Functions deployment
Optimized for cost and performance
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import json
from datetime import datetime
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="EPL Predictor API",
    description="Lightweight FPL prediction API",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Will restrict to Firebase domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache for FPL data
data_cache = {}
CACHE_DURATION = 3600  # 1 hour

def get_fpl_data():
    """Fetch FPL data with caching"""
    cache_key = "fpl_data"
    if cache_key in data_cache:
        cached_data, timestamp = data_cache[cache_key]
        if (datetime.now() - timestamp).seconds < CACHE_DURATION:
            return cached_data
    
    try:
        response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
        data = response.json()
        data_cache[cache_key] = (data, datetime.now())
        return data
    except Exception as e:
        logger.error(f"Error fetching FPL data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch FPL data")

@app.get("/")
async def root():
    """API information"""
    return {
        "name": "EPL Predictor API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": [
            "/players/predictions",
            "/optimize/squad",
            "/gameweek/current"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/players/predictions")
async def get_player_predictions(top_n: int = 50):
    """Get player predictions (simplified version)"""
    try:
        data = get_fpl_data()
        players = data['elements']
        
        # Simple prediction based on form and recent points
        predictions = []
        for player in players[:top_n]:
            predicted_points = float(player['form']) * 2 + player['total_points'] / 10
            predictions.append({
                "id": player['id'],
                "name": player['web_name'],
                "team": player['team'],
                "position": player['element_type'],
                "price": player['now_cost'] / 10,
                "predicted_points": round(predicted_points, 2),
                "form": player['form'],
                "ownership": player['selected_by_percent']
            })
        
        # Sort by predicted points
        predictions.sort(key=lambda x: x['predicted_points'], reverse=True)
        return {"predictions": predictions[:top_n]}
    
    except Exception as e:
        logger.error(f"Error in predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize/squad")
async def optimize_squad(budget: float = 100.0):
    """Squad optimization (simplified version)"""
    try:
        data = get_fpl_data()
        players = data['elements']
        
        # Simple optimization: Pick best value players per position
        squad = []
        positions = {1: [], 2: [], 3: [], 4: []}  # GK, DEF, MID, FWD
        
        for player in players:
            value = float(player['form']) / (player['now_cost'] / 10 + 1)
            positions[player['element_type']].append({
                "id": player['id'],
                "name": player['web_name'],
                "position": player['element_type'],
                "price": player['now_cost'] / 10,
                "value": value,
                "form": player['form']
            })
        
        # Sort each position by value
        for pos in positions:
            positions[pos].sort(key=lambda x: x['value'], reverse=True)
        
        # Select players: 2 GK, 5 DEF, 5 MID, 3 FWD
        squad.extend(positions[1][:2])  # GK
        squad.extend(positions[2][:5])  # DEF
        squad.extend(positions[3][:5])  # MID
        squad.extend(positions[4][:3])  # FWD
        
        total_cost = sum(p['price'] for p in squad)
        
        return {
            "squad": squad,
            "total_cost": round(total_cost, 1),
            "budget_remaining": round(budget - total_cost, 1),
            "formation": "2-5-5-3"
        }
    
    except Exception as e:
        logger.error(f"Error in squad optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gameweek/current")
async def get_current_gameweek():
    """Get current gameweek information"""
    try:
        data = get_fpl_data()
        events = data['events']
        
        current_gw = None
        for event in events:
            if event['is_current']:
                current_gw = event
                break
        
        if not current_gw:
            # Find next gameweek
            for event in events:
                if event['is_next']:
                    current_gw = event
                    break
        
        return {
            "gameweek": current_gw['id'] if current_gw else 1,
            "name": current_gw['name'] if current_gw else "Gameweek 1",
            "deadline": current_gw['deadline_time'] if current_gw else None,
            "is_current": current_gw['is_current'] if current_gw else False,
            "is_next": current_gw['is_next'] if current_gw else False
        }
    
    except Exception as e:
        logger.error(f"Error fetching gameweek: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
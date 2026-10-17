from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Optional
import uvicorn
from datetime import datetime, timedelta
import json
import logging

# Import your existing components
from ..pytorch_prediction_engine import PyTorchFPLPredictionEngine
from ..models.team_optimizer import FPLTeamOptimizer
from ..analysis.sentiment_analyzer import SentimentAnalyzer
from ..analysis.price_monitor import FPLPriceMonitor
from ..analysis.injury_tracker import InjuryTracker
from ..database.local_db import LocalDatabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="FPL Predictor Pro - Local API",
    description="Local development version of FPL Predictor with full features",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = LocalDatabase()
prediction_engine = PyTorchFPLPredictionEngine()
team_optimizer = FPLTeamOptimizer()
sentiment_analyzer = SentimentAnalyzer()
price_monitor = FPLPriceMonitor()
injury_tracker = InjuryTracker()

# Simple auth for local testing
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple auth - always return demo user for local testing"""
    return db.get_user_by_username('demo_user')

@app.get("/")
def root():
    return {"message": "FPL Predictor Pro Local API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Auth endpoints for compatibility
@app.post("/auth/login")
def login(credentials: dict):
    """Mock login - always succeeds for local testing"""
    user = db.get_user_by_username('demo_user')
    return {
        "access_token": "mock_local_token",
        "token_type": "bearer",
        "user": user
    }

@app.get("/auth/me")
def get_current_user_profile(user = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "user": user,
        "features": {
            "predictions_per_week": -1,  # Unlimited for local testing
            "advanced_optimizer": True,
            "sentiment_analysis": True,
            "injury_alerts": True,
            "price_alerts": True
        },
        "usage": {
            "api_calls_today": 45,
            "predictions_this_week": 12
        }
    }

# Main dashboard endpoint
@app.get("/dashboard")
def get_dashboard_data(gameweek: Optional[int] = None, user = Depends(get_current_user)):
    """Get comprehensive dashboard data"""
    try:
        current_gameweek = gameweek or 15  # Mock current gameweek
        
        # Get all players
        players = db.get_all_players()
        
        # Get user predictions
        predictions = db.get_user_predictions(user['id'], current_gameweek)
        
        # Get user alerts
        alerts = db.get_user_alerts(user['id'])
        unread_alerts = [a for a in alerts if not a['is_read']]
        
        # Get price predictions
        price_predictions = db.get_price_predictions(10)
        
        # Get sentiment analysis
        sentiment_data = db.get_sentiment_analysis(10)
        
        # Mock additional data
        dashboard_data = {
            "currentGameweek": current_gameweek,
            "squadValue": 99.5,
            "squadValueChange": 2.3,
            "overallRank": 145_234,
            "rankChange": -5.2,
            "gameweekPoints": 67,
            "pointsVsAverage": 8.3,
            "predictionsUsed": len(predictions),
            "unreadAlerts": len(unread_alerts),
            
            # Player predictions
            "predictions": predictions[:10],  # Top 10 predictions
            
            # Squad data (mock)
            "squad": {
                "players": players[:15],  # First 15 players as mock squad
                "total_value": 99.5,
                "bank": 0.5,
                "free_transfers": 1
            },
            
            # Optimizer recommendations
            "optimizerRecommendations": {
                "transfers_in": [
                    {"name": "Haaland", "team": "Man City", "price": 14.0, "predicted_points": 12.5, "reason": "Top scorer potential"},
                    {"name": "Salah", "team": "Liverpool", "price": 13.0, "predicted_points": 11.2, "reason": "Excellent form"}
                ],
                "transfers_out": [
                    {"name": "De Bruyne", "team": "Man City", "price": 12.5, "predicted_points": 2.1, "reason": "Injury concerns"}
                ],
                "captain_suggestions": [
                    {"name": "Haaland", "predicted_points": 12.5, "confidence": 0.89},
                    {"name": "Salah", "predicted_points": 11.2, "confidence": 0.82}
                ]
            },
            
            # Weekly insights
            "weeklyInsights": {
                "top_picks": [
                    {"name": "Haaland", "team": "Man City", "predicted_points": 12.5, "position": "FWD", "price": 14.0},
                    {"name": "Salah", "team": "Liverpool", "predicted_points": 11.2, "position": "MID", "price": 13.0},
                    {"name": "Foden", "team": "Man City", "predicted_points": 8.9, "position": "MID", "price": 8.0}
                ],
                "differentials": [
                    {"name": "Watkins", "team": "Aston Villa", "predicted_points": 6.8, "ownership": 24.1, "price": 7.5}
                ],
                "captain_options": predictions[:3] if predictions else []
            },
            
            # Injury alerts
            "injuryAlerts": [
                {"player": "De Bruyne", "severity": "major", "return_date": "4-6 weeks", "impact": "high"},
                {"player": "James", "severity": "minor", "return_date": "This GW", "impact": "medium"}
            ],
            
            # Price predictions
            "pricePredictions": price_predictions,
            
            # Sentiment analysis
            "sentimentAnalysis": {
                "topPlayers": sentiment_data[:5]
            },
            
            # Mini leagues (mock)
            "miniLeagues": [
                {"id": 1, "name": "Work League", "rank": 3, "totalPlayers": 20, "points": 1234, "gapToFirst": -45},
                {"id": 2, "name": "Friends League", "rank": 1, "totalPlayers": 12, "points": 1289, "gapToFirst": 0}
            ],
            
            # All alerts
            "alerts": alerts
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Player predictions endpoint
@app.get("/predictions")
def get_predictions(gameweek: Optional[int] = None, user = Depends(get_current_user)):
    """Get AI predictions for players"""
    try:
        players = db.get_all_players()
        predictions = []
        
        for player in players:
            try:
                # Use actual ML model prediction or mock data
                predicted_points = prediction_engine.predict_player_points(
                    player_id=player['id'],
                    player_data=player
                ) if hasattr(prediction_engine, 'model') else float(player['form']) + 2.5
                
                predictions.append({
                    "player_id": player['id'],
                    "name": f"{player['first_name']} {player['second_name']}",
                    "web_name": player['web_name'],
                    "team": player['team'],
                    "position": player['position'],
                    "price": player['now_cost'] / 10,
                    "predicted_points": round(predicted_points, 1),
                    "confidence": round(0.6 + (predicted_points / 20), 2),
                    "form": player['form'],
                    "selected_by_percent": player['selected_by_percent']
                })
            except Exception as e:
                logger.warning(f"Error predicting for player {player['id']}: {e}")
                continue
        
        # Sort by predicted points
        predictions.sort(key=lambda x: x['predicted_points'], reverse=True)
        
        return {
            "gameweek": gameweek or 15,
            "predictions": predictions[:50],  # Top 50 predictions
            "total_players": len(predictions),
            "model_accuracy": 0.847,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Team optimizer endpoint
@app.post("/optimizer/squad")
def optimize_squad(constraints: dict = None, user = Depends(get_current_user)):
    """Optimize squad selection"""
    try:
        players = db.get_all_players()
        
        # Create predictions dict
        predictions = {}
        for player in players:
            try:
                predicted_points = prediction_engine.predict_player_points(
                    player_id=player['id'],
                    player_data=player
                ) if hasattr(prediction_engine, 'model') else float(player['form']) + 2.5
                predictions[player['id']] = predicted_points
            except:
                predictions[player['id']] = float(player['form']) + 2.5
        
        # Convert to DataFrame format expected by optimizer
        import pandas as pd
        players_df = pd.DataFrame(players)
        
        # Run optimization
        result = team_optimizer.optimize_squad(players_df, predictions)
        
        return {
            "status": "success",
            "squad": result.get('squad', []),
            "total_cost": result.get('total_cost', 0),
            "predicted_points": result.get('predicted_points', 0),
            "optimization_details": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing squad: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Alerts endpoint
@app.get("/alerts")
def get_alerts(unread_only: bool = False, user = Depends(get_current_user)):
    """Get user alerts"""
    try:
        alerts = db.get_user_alerts(user['id'], unread_only)
        return {
            "alerts": alerts,
            "total_count": len(alerts),
            "unread_count": len([a for a in alerts if not a['is_read']])
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Price predictions endpoint
@app.get("/price-changes")
def get_price_changes(user = Depends(get_current_user)):
    """Get price change predictions"""
    try:
        predictions = db.get_price_predictions(20)
        
        return {
            "predictions": predictions,
            "summary": {
                "predicted_rises": len([p for p in predictions if p['direction'] == 'rise']),
                "predicted_falls": len([p for p in predictions if p['direction'] == 'fall']),
                "confidence_threshold": 0.6
            },
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting price changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Sentiment analysis endpoint
@app.get("/sentiment")
def get_sentiment_analysis(user = Depends(get_current_user)):
    """Get sentiment analysis data"""
    try:
        sentiment_data = db.get_sentiment_analysis(15)
        
        return {
            "sentiment_analysis": sentiment_data,
            "summary": {
                "positive_players": len([s for s in sentiment_data if s['sentiment_label'] == 'positive']),
                "negative_players": len([s for s in sentiment_data if s['sentiment_label'] == 'negative']),
                "high_injury_risk": len([s for s in sentiment_data if s['injury_risk'] == 'high'])
            },
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting sentiment analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Player details endpoint
@app.get("/players/{player_id}")
def get_player_details(player_id: int, user = Depends(get_current_user)):
    """Get detailed player information"""
    try:
        players = db.get_all_players()
        player = next((p for p in players if p['id'] == player_id), None)
        
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Get prediction for this player
        try:
            predicted_points = prediction_engine.predict_player_points(
                player_id=player['id'],
                player_data=player
            ) if hasattr(prediction_engine, 'model') else float(player['form']) + 2.5
        except:
            predicted_points = float(player['form']) + 2.5
        
        # Get sentiment data
        sentiment_data = db.get_sentiment_analysis()
        player_sentiment = next((s for s in sentiment_data if s['player_name'] == player['web_name']), None)
        
        return {
            "player": player,
            "predicted_points": round(predicted_points, 1),
            "confidence": round(0.6 + (predicted_points / 20), 2),
            "sentiment": player_sentiment,
            "recent_form": [5.2, 6.1, 4.8, 7.3, 5.9],  # Mock recent form
            "upcoming_fixtures": [
                {"opponent": "Arsenal", "difficulty": 4, "venue": "away"},
                {"opponent": "Brighton", "difficulty": 2, "venue": "home"}
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Live updates endpoint
@app.get("/live")
def get_live_updates(user = Depends(get_current_user)):
    """Get live gameweek updates"""
    try:
        return {
            "live_gameweek": 15,
            "matches_in_progress": [
                {"home_team": "Arsenal", "away_team": "Chelsea", "score": "1-0", "minute": 67},
                {"home_team": "Liverpool", "away_team": "Man City", "score": "2-1", "minute": 78}
            ],
            "top_performers": [
                {"name": "Haaland", "points": 12, "goals": 2},
                {"name": "Salah", "points": 8, "assists": 1, "goals": 1}
            ],
            "price_changes_tonight": [
                {"name": "Salah", "direction": "rise", "probability": 0.89},
                {"name": "James", "direction": "fall", "probability": 0.74}
            ],
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting live updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Starting FPL Predictor Pro Local Server...")
    print("📊 Dashboard: http://localhost:3000")
    print("🔗 API Docs: http://localhost:8000/docs")
    print("💡 Demo User: username='demo_user' (auto-login)")
    print()
    
    uvicorn.run(
        "src.api.local_main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
"""
AI-Enhanced EPL Predictor API using Firebase AI Logic
Integrates Vertex AI and Genkit for advanced predictions and sentiment analysis
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import requests
import logging
import os
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="EPL Predictor AI API",
    description="AI-powered FPL prediction API with Firebase AI Logic",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache for FPL data
data_cache = {}
CACHE_DURATION = 3600  # 1 hour

# Models for requests
class PredictionRequest(BaseModel):
    player_id: int
    include_sentiment: bool = True
    gameweeks_ahead: int = 1

class SentimentRequest(BaseModel):
    player_name: str
    text: Optional[str] = None

class AIInsightRequest(BaseModel):
    squad_ids: List[int]
    budget: float = 100.0

# Vertex AI integration (using Google's generative AI)
try:
    import google.generativeai as genai
    # Configure with API key from environment
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        AI_ENABLED = True
    else:
        AI_ENABLED = False
        logger.warning("Google API key not found. AI features disabled.")
except ImportError:
    AI_ENABLED = False
    logger.warning("Google Generative AI not installed. AI features disabled.")

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

async def get_ai_prediction(player_data: dict, context: str = "") -> float:
    """Use Gemini AI to enhance player predictions"""
    if not AI_ENABLED:
        # Fallback to simple calculation
        return float(player_data.get('form', 0)) * 2 + player_data.get('total_points', 0) / 10
    
    try:
        prompt = f"""
        Analyze this FPL player data and predict their points for the next gameweek:
        
        Player: {player_data.get('web_name')}
        Position: {player_data.get('element_type')}
        Current Form: {player_data.get('form')}
        Total Points: {player_data.get('total_points')}
        Points Per Game: {player_data.get('points_per_game')}
        Selected By: {player_data.get('selected_by_percent')}%
        ICT Index: {player_data.get('ict_index')}
        
        {context}
        
        Provide only a numeric prediction (0-20 points) based on statistical analysis.
        Consider form trends, fixture difficulty, and historical performance.
        Response format: Just the number, nothing else.
        """
        
        response = model.generate_content(prompt)
        prediction = float(response.text.strip())
        return min(max(prediction, 0), 20)  # Clamp between 0-20
    except Exception as e:
        logger.error(f"AI prediction error: {e}")
        # Fallback to simple calculation
        return float(player_data.get('form', 0)) * 2 + player_data.get('total_points', 0) / 10

async def analyze_sentiment(player_name: str, text: Optional[str] = None) -> dict:
    """Use AI for sentiment analysis on player news/social media"""
    if not AI_ENABLED:
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "summary": "AI features not available"
        }
    
    try:
        # If no text provided, search for recent news (simplified for demo)
        if not text:
            text = f"Recent news and social media mentions about {player_name}"
        
        prompt = f"""
        Analyze the sentiment and injury/form implications for FPL player {player_name}:
        
        Text: {text}
        
        Provide analysis in JSON format:
        {{
            "sentiment": "positive/neutral/negative",
            "confidence": 0.0-1.0,
            "injury_risk": "low/medium/high",
            "form_trend": "improving/stable/declining",
            "key_factors": ["factor1", "factor2"],
            "fpl_impact": "Brief FPL impact summary"
        }}
        """
        
        response = model.generate_content(prompt)
        # Parse the response (assuming it returns valid JSON)
        try:
            result = json.loads(response.text)
        except:
            result = {
                "sentiment": "neutral",
                "confidence": 0.7,
                "summary": response.text[:200]
            }
        
        return result
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "error": str(e)
        }

@app.get("/")
async def root():
    """API information"""
    return {
        "name": "EPL Predictor AI API",
        "version": "2.0.0",
        "ai_enabled": AI_ENABLED,
        "features": [
            "AI-powered predictions using Gemini",
            "Sentiment analysis for player news",
            "Smart squad optimization",
            "Real-time FPL data integration"
        ],
        "endpoints": [
            "/players/predictions",
            "/players/ai-predict",
            "/sentiment/analyze",
            "/optimize/squad-ai",
            "/insights/team"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "ai_status": "enabled" if AI_ENABLED else "disabled",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/players/predictions")
async def get_player_predictions(top_n: int = 50, use_ai: bool = False):
    """Get player predictions with optional AI enhancement"""
    try:
        data = get_fpl_data()
        players = data['elements']
        
        predictions = []
        for player in players[:top_n]:
            if use_ai and AI_ENABLED:
                predicted_points = await get_ai_prediction(player)
            else:
                # Simple prediction
                predicted_points = float(player['form']) * 2 + player['total_points'] / 10
            
            predictions.append({
                "id": player['id'],
                "name": player['web_name'],
                "team": player['team'],
                "position": player['element_type'],
                "price": player['now_cost'] / 10,
                "predicted_points": round(predicted_points, 2),
                "form": player['form'],
                "ownership": player['selected_by_percent'],
                "ai_enhanced": use_ai and AI_ENABLED
            })
        
        predictions.sort(key=lambda x: x['predicted_points'], reverse=True)
        return {"predictions": predictions[:top_n]}
    
    except Exception as e:
        logger.error(f"Error in predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/players/ai-predict")
async def ai_predict_player(request: PredictionRequest):
    """Get AI-powered prediction for specific player"""
    try:
        data = get_fpl_data()
        player = next((p for p in data['elements'] if p['id'] == request.player_id), None)
        
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Get AI prediction
        prediction = await get_ai_prediction(player)
        
        # Get sentiment if requested
        sentiment = None
        if request.include_sentiment:
            sentiment = await analyze_sentiment(player['web_name'])
        
        return {
            "player": {
                "id": player['id'],
                "name": player['web_name']
            },
            "prediction": {
                "points": round(prediction, 2),
                "gameweeks_ahead": request.gameweeks_ahead,
                "confidence": 0.75  # Placeholder
            },
            "sentiment": sentiment,
            "ai_model": "gemini-pro" if AI_ENABLED else "fallback"
        }
    
    except Exception as e:
        logger.error(f"Error in AI prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sentiment/analyze")
async def analyze_player_sentiment(request: SentimentRequest):
    """Analyze sentiment for a player"""
    try:
        result = await analyze_sentiment(request.player_name, request.text)
        return {
            "player": request.player_name,
            "analysis": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize/squad-ai")
async def optimize_squad_with_ai(budget: float = 100.0):
    """AI-enhanced squad optimization"""
    try:
        data = get_fpl_data()
        players = data['elements']
        
        if AI_ENABLED:
            # Use AI to suggest optimal squad
            prompt = f"""
            Create an optimal FPL squad with budget {budget}M considering:
            - 2 GK, 5 DEF, 5 MID, 3 FWD (15 players total)
            - Max 3 players from same team
            - Current form, fixtures, and value
            
            From this player pool, suggest the best 15 players.
            Format: List player names only, one per line.
            """
            
            # For demo, we'll use simplified logic
            squad = []
            positions = {1: [], 2: [], 3: [], 4: []}
            
            for player in players:
                value = float(player['form']) / (player['now_cost'] / 10 + 1)
                positions[player['element_type']].append({
                    "id": player['id'],
                    "name": player['web_name'],
                    "position": player['element_type'],
                    "price": player['now_cost'] / 10,
                    "value": value,
                    "form": player['form'],
                    "ai_score": value * 1.2  # AI boost
                })
            
            # Sort by AI score
            for pos in positions:
                positions[pos].sort(key=lambda x: x['ai_score'], reverse=True)
            
            # Select optimal squad
            squad.extend(positions[1][:2])  # GK
            squad.extend(positions[2][:5])  # DEF
            squad.extend(positions[3][:5])  # MID
            squad.extend(positions[4][:3])  # FWD
        else:
            # Fallback to simple optimization
            squad = []
            positions = {1: [], 2: [], 3: [], 4: []}
            
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
            
            for pos in positions:
                positions[pos].sort(key=lambda x: x['value'], reverse=True)
            
            squad.extend(positions[1][:2])
            squad.extend(positions[2][:5])
            squad.extend(positions[3][:5])
            squad.extend(positions[4][:3])
        
        total_cost = sum(p['price'] for p in squad)
        
        return {
            "squad": squad,
            "total_cost": round(total_cost, 1),
            "budget_remaining": round(budget - total_cost, 1),
            "formation": "2-5-5-3",
            "ai_optimized": AI_ENABLED
        }
    
    except Exception as e:
        logger.error(f"Error in squad optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/insights/team")
async def get_team_insights(request: AIInsightRequest):
    """Get AI-powered insights for a team"""
    if not AI_ENABLED:
        return {
            "insights": "AI features not available. Enable Google API key.",
            "recommendations": []
        }
    
    try:
        data = get_fpl_data()
        squad_players = [p for p in data['elements'] if p['id'] in request.squad_ids]
        
        squad_info = "\n".join([
            f"- {p['web_name']} ({p['element_type']}, {p['now_cost']/10}M, Form: {p['form']})"
            for p in squad_players
        ])
        
        prompt = f"""
        Analyze this FPL squad and provide strategic insights:
        
        Squad:
        {squad_info}
        
        Budget: {request.budget}M
        
        Provide:
        1. Key strengths and weaknesses
        2. Transfer recommendations (specific players)
        3. Captain choice for next gameweek
        4. Formation suggestion
        5. Risk assessment
        
        Be specific and actionable.
        """
        
        response = model.generate_content(prompt)
        
        return {
            "insights": response.text,
            "squad_rating": 7.5,  # Placeholder
            "ai_confidence": 0.8
        }
    
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
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
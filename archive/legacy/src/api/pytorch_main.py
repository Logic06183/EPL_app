from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

from src.pytorch_prediction_engine import PyTorchFPLPredictionEngine
from src.data.fpl_api import FPLDataFetcher

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FPL Prediction API (PyTorch)", 
    version="2.0.0",
    description="PyTorch-powered Fantasy Premier League predictions and optimization"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
prediction_engine = PyTorchFPLPredictionEngine(use_sentiment=False)
fpl_fetcher = FPLDataFetcher()

class TeamOptimizationRequest(BaseModel):
    budget: float = 100.0
    excluded_players: Optional[List[int]] = []
    preferred_players: Optional[List[int]] = []

class TransferRequest(BaseModel):
    team_id: int
    gameweek: int
    free_transfers: int = 1

class PlayerPredictionResponse(BaseModel):
    player_id: int
    player_name: str
    team: str
    position: str
    predicted_points: float
    confidence: float
    price: float

class SquadResponse(BaseModel):
    squad: List[Dict]
    total_cost: float
    predicted_points: float
    optimization_status: str

@app.on_event("startup")
async def startup_event():
    logger.info("Starting PyTorch FPL Prediction API")
    try:
        # Try to load existing model
        prediction_engine.cnn_predictor.load_model(str(prediction_engine.model_dir))
        logger.info("Existing PyTorch model loaded successfully")
    except Exception as e:
        logger.warning(f"No existing model found: {e}")
        logger.info("API will use baseline predictions until model is trained")

@app.get("/")
async def root():
    model_info = prediction_engine.get_model_info()
    return {
        "message": "FPL Prediction API (PyTorch Edition)",
        "version": "2.0.0",
        "model_info": model_info,
        "endpoints": [
            "/players/predictions",
            "/optimize/squad",
            "/optimize/starting11", 
            "/transfers/suggest",
            "/players/{player_id}/details",
            "/gameweek/current",
            "/models/info",
            "/models/retrain"
        ]
    }

@app.get("/players/predictions", response_model=List[PlayerPredictionResponse])
async def get_all_player_predictions(top_n: int = 50):
    try:
        predictions = prediction_engine.get_player_predictions()
        players_df = fpl_fetcher.get_all_players_data()
        
        response = []
        for player_id, predicted_points in predictions.items():
            player_data = players_df[players_df['id'] == player_id]
            if not player_data.empty:
                player = player_data.iloc[0]
                
                # Calculate confidence based on player minutes and model availability
                base_confidence = 0.6
                if player['minutes'] > 500:
                    base_confidence = 0.8
                if prediction_engine.cnn_predictor.model is not None:
                    base_confidence += 0.15
                
                response.append(PlayerPredictionResponse(
                    player_id=player_id,
                    player_name=player['web_name'],
                    team=player.get('name_team', f"Team {player['team']}"),
                    position=player['position'],
                    predicted_points=round(predicted_points, 2),
                    confidence=min(0.95, base_confidence),
                    price=player['now_cost'] / 10
                ))
        
        response.sort(key=lambda x: x.predicted_points, reverse=True)
        return response[:top_n]
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/players/{player_id}/details")
async def get_player_details(player_id: int):
    try:
        players_df = fpl_fetcher.get_all_players_data()
        player_data = players_df[players_df['id'] == player_id]
        
        if player_data.empty:
            raise HTTPException(status_code=404, detail="Player not found")
        
        player = player_data.iloc[0]
        
        # Get player history
        try:
            history = fpl_fetcher.get_player_detailed_stats(player_id)
        except:
            history = pd.DataFrame()
        
        # Get predictions
        predictions = []
        if not history.empty and len(history) >= prediction_engine.cnn_predictor.sequence_length:
            if prediction_engine.cnn_predictor.model is not None:
                predictions = prediction_engine.cnn_predictor.predict_multiple_gameweeks(
                    history, n_gameweeks=5
                )
            else:
                # Fallback predictions
                baseline = prediction_engine._get_baseline_prediction(player)
                predictions = [baseline * (0.9 + 0.2 * i/4) for i in range(5)]
        else:
            baseline = prediction_engine._get_baseline_prediction(player)
            predictions = [baseline] * 5
        
        return {
            "player_info": {
                "id": player_id,
                "name": player['web_name'],
                "team": player.get('name_team', f"Team {player['team']}"),
                "position": player['position'],
                "price": player['now_cost'] / 10,
                "total_points": player['total_points'],
                "points_per_game": player.get('points_per_game', 0),
                "selected_by": f"{player.get('selected_by_percent', 0)}%",
                "form": player.get('form', 0),
                "status": player.get('status', 'a')
            },
            "predictions": {
                "next_5_gameweeks": [round(p, 1) for p in predictions],
                "average": round(sum(predictions) / len(predictions) if predictions else 0, 1)
            },
            "recent_performance": history.tail(5).to_dict('records') if not history.empty else []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize/squad", response_model=SquadResponse)
async def optimize_squad(request: TeamOptimizationRequest):
    try:
        result = prediction_engine.optimize_team_selection(budget=request.budget)
        
        return SquadResponse(
            squad=result['squad']['squad'],
            total_cost=result['squad']['total_cost'],
            predicted_points=result['squad']['predicted_points'],
            optimization_status=result['squad']['optimization_status']
        )
    except Exception as e:
        logger.error(f"Error optimizing squad: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize/starting11")
async def optimize_starting_eleven(squad: List[Dict]):
    try:
        gameweek_predictions = prediction_engine.get_single_gameweek_predictions()
        
        result = prediction_engine.team_optimizer.optimize_starting_11(
            squad,
            gameweek_predictions
        )
        
        return result
    except Exception as e:
        logger.error(f"Error optimizing starting 11: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transfers/suggest")
async def suggest_transfers(request: TransferRequest):
    try:
        suggestions = prediction_engine.get_transfer_suggestions(
            request.team_id,
            request.gameweek,
            request.free_transfers
        )
        
        return suggestions
    except Exception as e:
        logger.error(f"Error suggesting transfers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gameweek/current")
async def get_current_gameweek():
    try:
        bootstrap_data = fpl_fetcher.get_bootstrap_data()
        
        current_event = None
        for event in bootstrap_data['events']:
            if event.get('is_current'):
                current_event = event
                break
        
        if not current_event:
            next_event = next((e for e in bootstrap_data['events'] if e.get('is_next')), None)
            current_event = next_event if next_event else bootstrap_data['events'][0]
        
        return {
            "gameweek": current_event['id'],
            "name": current_event['name'],
            "deadline": current_event['deadline_time'],
            "is_current": current_event.get('is_current', False),
            "is_finished": current_event.get('finished', False)
        }
    except Exception as e:
        logger.error(f"Error getting current gameweek: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/info")
async def get_model_info():
    try:
        return prediction_engine.get_model_info()
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/models/retrain")
async def retrain_models(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(prediction_engine.train_models, force_retrain=True)
        return {"message": "PyTorch model retraining initiated in background"}
    except Exception as e:
        logger.error(f"Error initiating retraining: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    model_info = prediction_engine.get_model_info()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": model_info['model_loaded'],
        "device": model_info['device'],
        "pytorch_version": "2.8.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
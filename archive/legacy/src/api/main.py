from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

from src.prediction_engine import FPLPredictionEngine
from src.data.fpl_api import FPLDataFetcher

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FPL Prediction API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prediction_engine = FPLPredictionEngine(use_sentiment=False)
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

class Starting11Response(BaseModel):
    starting_11: List[Dict]
    formation: Dict
    captain: Dict
    vice_captain: Dict
    bench: List[Dict]
    predicted_points: float

@app.on_event("startup")
async def startup_event():
    logger.info("Starting FPL Prediction API")
    try:
        prediction_engine.train_models()
        logger.info("Models loaded successfully")
    except Exception as e:
        logger.error(f"Error loading models: {e}")

@app.get("/")
async def root():
    return {
        "message": "FPL Prediction API",
        "version": "1.0.0",
        "endpoints": [
            "/players/predictions",
            "/optimize/squad",
            "/optimize/starting11",
            "/transfers/suggest",
            "/players/{player_id}/details"
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
                response.append(PlayerPredictionResponse(
                    player_id=player_id,
                    player_name=player['web_name'],
                    team=player['name_team'],
                    position=player['position'],
                    predicted_points=round(predicted_points, 2),
                    confidence=0.75,
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
        
        history = fpl_fetcher.get_player_detailed_stats(player_id)
        
        predictions = prediction_engine.cnn_predictor.predict_multiple_gameweeks(
            history, n_gameweeks=5
        ) if len(history) >= 6 else [0] * 5
        
        return {
            "player_info": {
                "id": player_id,
                "name": player['web_name'],
                "team": player['name_team'],
                "position": player['position'],
                "price": player['now_cost'] / 10,
                "total_points": player['total_points'],
                "points_per_game": player['points_per_game'],
                "selected_by": f"{player['selected_by_percent']}%",
                "form": player['form'],
                "status": player['status']
            },
            "predictions": {
                "next_5_gameweeks": predictions,
                "average": sum(predictions) / len(predictions) if predictions else 0
            },
            "recent_performance": history.tail(5).to_dict('records') if not history.empty else []
        }
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

@app.post("/optimize/starting11", response_model=Starting11Response)
async def optimize_starting_eleven(squad: List[Dict]):
    try:
        gameweek_predictions = prediction_engine.get_single_gameweek_predictions()
        
        result = prediction_engine.team_optimizer.optimize_starting_11(
            squad,
            gameweek_predictions
        )
        
        return Starting11Response(**result)
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
            if event['is_current']:
                current_event = event
                break
        
        if not current_event:
            next_event = next((e for e in bootstrap_data['events'] if e['is_next']), None)
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

@app.post("/models/retrain")
async def retrain_models(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(prediction_engine.train_models, force_retrain=True)
        return {"message": "Model retraining initiated in background"}
    except Exception as e:
        logger.error(f"Error initiating retraining: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": prediction_engine.cnn_predictor.model is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
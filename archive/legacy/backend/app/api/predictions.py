"""
Prediction API endpoints
Multi-model predictions with xG/xA analytics and Gemini AI insights
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging

from ..schemas.player import PlayerPrediction
from ..services.prediction_service import get_prediction_service, PredictionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[PlayerPrediction], summary="Get player predictions")
async def get_predictions(
    top_n: int = Query(50, ge=1, le=500, description="Number of top players to return"),
    model: str = Query("ensemble", description="Model to use: random_forest, cnn, ensemble"),
    position: Optional[int] = Query(None, description="Filter by position"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    """
    Get player predictions using AI models

    Features:
    - Multi-model predictions (RandomForest, CNN, Ensemble)
    - Advanced analytics (xG, xA, ICT index)
    - Confidence scores
    - AI-generated insights

    Models:
    - `random_forest`: Fast, reliable baseline (200 trees, 24 features)
    - `cnn`: Deep learning model for temporal patterns
    - `ensemble`: Combined predictions from multiple models (recommended)
    """
    try:
        predictions = await prediction_service.get_predictions(
            top_n=top_n,
            model=model,
            position=position,
            max_price=max_price,
        )

        return predictions

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating predictions: {e}")
        raise HTTPException(status_code=500, detail="Prediction generation failed")


@router.get("/enhanced", response_model=List[PlayerPrediction], summary="Get enhanced predictions with Gemini AI")
async def get_enhanced_predictions(
    top_n: int = Query(20, ge=1, le=100, description="Number of top players to return"),
    model: str = Query("ensemble", description="Model to use"),
    use_gemini: bool = Query(True, description="Include Gemini AI insights"),
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    """
    Get enhanced predictions with Gemini AI insights

    This endpoint provides:
    - Multi-model predictions
    - xG/xA analytics with context
    - Gemini AI reasoning for each prediction
    - Overperformance/underperformance analysis

    Note: Gemini AI insights may take longer to generate
    """
    try:
        predictions = await prediction_service.get_enhanced_predictions(
            top_n=top_n,
            model=model,
            use_gemini=use_gemini,
        )

        return predictions

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating enhanced predictions: {e}")
        raise HTTPException(status_code=500, detail="Enhanced prediction generation failed")


@router.get("/{player_id}", response_model=PlayerPrediction, summary="Get prediction for specific player")
async def get_player_prediction(
    player_id: int,
    model: str = Query("ensemble", description="Model to use"),
    use_gemini: bool = Query(False, description="Include Gemini AI insights"),
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    """
    Get prediction for a specific player

    Returns detailed prediction including:
    - Predicted points for next gameweek
    - Confidence score
    - Model breakdown (if ensemble)
    - Advanced analytics
    - Optional Gemini AI insights
    """
    try:
        prediction = await prediction_service.get_player_prediction(
            player_id=player_id,
            model=model,
            use_gemini=use_gemini,
        )

        if not prediction:
            raise HTTPException(
                status_code=404, detail=f"Prediction for player {player_id} not available"
            )

        return prediction

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating prediction for player {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Prediction generation failed")


@router.get("/models/info", summary="Get model information")
async def get_model_info(
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    """
    Get information about available prediction models

    Returns:
    - Model names and descriptions
    - Features used
    - Performance metrics
    - Training status
    """
    try:
        info = await prediction_service.get_model_info()
        return info

    except Exception as e:
        logger.error(f"Error fetching model info: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch model information")


@router.post("/models/retrain", summary="Trigger model retraining")
async def retrain_models(
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    """
    Trigger retraining of prediction models

    This endpoint starts a background task to retrain models with latest data.
    Note: This operation may take several minutes.
    """
    try:
        result = await prediction_service.retrain_models()
        return result

    except Exception as e:
        logger.error(f"Error retraining models: {e}")
        raise HTTPException(status_code=500, detail="Model retraining failed")

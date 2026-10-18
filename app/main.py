"""
FPL AI Pro - Production FastAPI Application
Consolidated API with multi-model predictions, xG/xA analytics, and Gemini AI
"""

from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .utils.logging import setup_logging, get_logger
from .utils.cache import get_cache_manager
from .api import calendar, events, players, predictions, teams, payments, fpl_team, users

# Setup logging
setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
logger = get_logger(__name__)

# Global state
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize cache manager
    cache_manager = get_cache_manager(
        ttl=settings.CACHE_TTL,
        max_size=settings.CACHE_MAX_SIZE
    )
    app_state["cache"] = cache_manager
    logger.info("Cache manager initialized")

    # Pre-warm the FPL bootstrap cache and compute expected points so the first
    # user request is fast.
    app_state["models_loaded"] = False
    try:
        from .services.data_service import get_data_service
        from .services.xp_service import get_xp_service

        data_service = get_data_service()
        bootstrap = await data_service.get_bootstrap_data()
        elements = bootstrap.get("elements", [])
        logger.info(f"Bootstrap cache pre-warmed: {len(elements)} players loaded")

        xp_service = get_xp_service()
        await xp_service.refresh(data_service)
        app_state["models_loaded"] = xp_service.ready
        logger.info(f"Expected points ready: {app_state['models_loaded']}")
    except Exception as e:
        logger.warning(f"Startup pre-warm failed (non-fatal, will train lazily): {e}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")
    # Cleanup resources if needed


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Production FPL API with RandomForest, CNN, and Gemini AI predictions featuring xG/xA analytics",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint with information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
            "api": settings.API_PREFIX,
        },
        "features": [
            "Multi-model AI predictions (RandomForest + CNN + Gemini)",
            "Advanced analytics (xG, xA, ICT)",
            "Team optimization",
            "Transfer suggestions",
            "Payment integration",
        ],
    }


# Health check endpoint - compatible with both old and new frontend
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "ai_enabled": True,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models_loaded": app_state.get("models_loaded", False),
        "cache_available": app_state.get("cache") is not None,
    }


# Ping endpoint (lightweight health check)
@app.get("/ping")
async def ping():
    """Lightweight ping endpoint"""
    return {"status": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}


# Include API routers
app.include_router(
    players.router,
    prefix=f"{settings.API_PREFIX}/players",
    tags=["Players"],
)

# Mount predictions under BOTH /api/predictions AND /api/players/predictions
# The frontend expects /api/players/predictions but the clean API uses /api/predictions
app.include_router(
    predictions.router,
    prefix=f"{settings.API_PREFIX}/predictions",
    tags=["Predictions"],
)

# Backward-compatible route: frontend calls /api/players/predictions
app.include_router(
    predictions.router,
    prefix=f"{settings.API_PREFIX}/players/predictions",
    tags=["Predictions (compat)"],
    include_in_schema=False,  # Hide from docs to avoid confusion
)

app.include_router(
    teams.router,
    prefix=f"{settings.API_PREFIX}/teams",
    tags=["Teams & Optimization"],
)

app.include_router(
    payments.router,
    prefix=f"{settings.API_PREFIX}/payments",
    tags=["Payments"],
)

app.include_router(
    fpl_team.router,
    prefix=f"{settings.API_PREFIX}/fpl-team",
    tags=["FPL Team Import"],
)

app.include_router(
    users.router,
    prefix=f"{settings.API_PREFIX}/users",
    tags=["Users"],
)

app.include_router(
    events.router,
    prefix=f"{settings.API_PREFIX}/events",
    tags=["Analytics"],
)

app.include_router(
    calendar.router,
    prefix=f"{settings.API_PREFIX}/calendar",
    tags=["Calendar"],
)

app.include_router(
    events.admin_router,
    prefix=f"{settings.API_PREFIX}/admin",
    tags=["Admin"],
)


# Gameweek and Fixtures endpoints (directly under /api/)
from .services.data_service import get_data_service


@app.get(f"{settings.API_PREFIX}/gameweek/current", tags=["Gameweek"])
async def get_current_gameweek(
    data_service=Depends(get_data_service),
):
    """Get current or next gameweek information"""
    try:
        gameweek_info = await data_service.get_gameweek_info()
        selected = gameweek_info.get("current") or gameweek_info.get("next") or {}
        return {
            **selected,
            "gameweek": selected.get("id"),
            "deadline": selected.get("deadline_time"),
            "is_finished": selected.get("finished", False),
            "current": gameweek_info.get("current"),
            "next": gameweek_info.get("next"),
            "all_events": gameweek_info.get("all_events", []),
        }
    except Exception as e:
        logger.error(f"Error fetching gameweek: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch gameweek info")


@app.get(f"{settings.API_PREFIX}/fixtures", tags=["Fixtures"])
async def get_fixtures(
    filter: str = Query("upcoming", description="Filter: live, today, recent, upcoming"),
    gameweek: Optional[int] = Query(None, description="Specific gameweek"),
    data_service=Depends(get_data_service),
):
    """Get Premier League fixtures with various filters"""
    try:
        fixtures = await data_service.get_fixtures(filter_type=filter, gameweek=gameweek)
        # Enrich with team names from bootstrap
        bootstrap = await data_service.get_bootstrap_data()
        teams = {t["id"]: t for t in bootstrap.get("teams", [])}
        for f in fixtures:
            f["team_h_name"] = teams.get(f.get("team_h"), {}).get("name", f"Team {f.get('team_h')}")
            f["team_a_name"] = teams.get(f.get("team_a"), {}).get("name", f"Team {f.get('team_a')}")
        return {
            "fixtures": fixtures,
            "filter": filter,
            "gameweek": gameweek,
            "count": len(fixtures),
        }
    except Exception as e:
        logger.error(f"Error fetching fixtures: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch fixtures")


# Model info and performance endpoints (backward compat with old API)
from .services.prediction_service import get_prediction_service


@app.get(f"{settings.API_PREFIX}/models/info", tags=["Models"])
async def get_models_info(
    prediction_service=Depends(get_prediction_service),
):
    """Get information about available models (backward compatible)"""
    return await prediction_service.get_model_info()


@app.get(f"{settings.API_PREFIX}/models/available", tags=["Models"])
async def get_models_available(
    prediction_service=Depends(get_prediction_service),
):
    """List available models (alias for /models/info)"""
    return await prediction_service.get_model_info()


@app.get(f"{settings.API_PREFIX}/models/performance", tags=["Models"])
async def get_models_performance(
    prediction_service=Depends(get_prediction_service),
):
    """Compare model performance"""
    info = await prediction_service.get_model_info()
    return {
        "models": info.get("models", {}),
        "recommendation": info.get("recommendation"),
        "track_record": info.get("track_record"),
        "note": info.get("track_record_note"),
    }


@app.get(f"{settings.API_PREFIX}/models/track-record", tags=["Models"])
async def get_track_record():
    """
    How good are the predictions? The walk-forward backtest on past seasons,
    plus this season's gameweeks scored against actual points.
    """
    from .auth.firebase_auth import get_db
    from .services import track_record
    from .services.data_service import get_data_service
    from .services.xp_service import get_xp_service

    cache = app_state.get("cache")
    cached = cache.get("track_record") if cache else None
    if cached is not None:
        return cached

    xp = get_xp_service()
    live = {"season": None, "gameweeks": [], "summary": None}
    try:
        db = get_db()
        if db is not None:
            live = await track_record.live_record(get_data_service(), db)
    except Exception as e:
        logger.warning(f"Track record load failed: {e}")

    payload = {
        "backtest": xp.backtest,
        "live": live,
        "method": (
            "Predictions are saved before each deadline and scored once the gameweek "
            "finishes, against the same players and metrics as the backtest: players "
            "averaging 30+ minutes over their last 6 gameweeks. 'Season average' is each "
            "player's points per game so far this season."
        ),
    }
    if cache:
        cache.set("track_record", payload)
    return payload


# Development endpoints
if settings.DEBUG:
    @app.get("/debug/cache")
    async def debug_cache():
        """Debug cache contents (development only)"""
        cache = app_state.get("cache")
        if cache:
            return {
                "cache_size": len(cache.memory_cache),
                "cache_info": str(cache.memory_cache),
            }
        return {"error": "Cache not available"}

    @app.post("/debug/clear-cache")
    async def clear_cache():
        """Clear cache (development only)"""
        cache = app_state.get("cache")
        if cache:
            cache.clear()
            return {"message": "Cache cleared successfully"}
        return {"error": "Cache not available"}


# Make app_state accessible to routes
app.state.app_state = app_state

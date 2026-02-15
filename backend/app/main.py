"""
FPL AI Pro - Production FastAPI Application
Consolidated API with multi-model predictions, xG/xA analytics, and Gemini AI
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .utils.logging import setup_logging, get_logger
from .utils.cache import get_cache_manager
from .schemas.common import HealthResponse, ErrorResponse
from .api import players, predictions, teams, payments

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

    # Initialize ML models (lazy loading)
    app_state["models_loaded"] = False
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


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        models_loaded=app_state.get("models_loaded", False),
        cache_available=app_state.get("cache") is not None,
    )


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

app.include_router(
    predictions.router,
    prefix=f"{settings.API_PREFIX}/predictions",
    tags=["Predictions"],
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

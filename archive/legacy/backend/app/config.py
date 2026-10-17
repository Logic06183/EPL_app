"""
Application Configuration
Environment-based settings with validation using Pydantic
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable validation"""

    # Application
    APP_NAME: str = "FPL AI Pro"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # External APIs
    FPL_API_BASE: str = "https://fantasy.premierleague.com/api"
    NEWS_API_KEY: Optional[str] = None
    SPORTMONKS_API_KEY: Optional[str] = None

    # Google AI
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Payment Integration
    PAYSTACK_SECRET_KEY: Optional[str] = None
    PAYSTACK_PUBLIC_KEY: Optional[str] = None

    # Caching
    CACHE_TTL: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 1000

    # Redis (optional)
    REDIS_URL: Optional[str] = None
    REDIS_ENABLED: bool = False

    # Database (optional for future)
    DATABASE_URL: Optional[str] = None

    # ML Models
    MODEL_UPDATE_INTERVAL_HOURS: int = 24
    MODEL_PATH: str = "./models"
    USE_GPU: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Security
    API_KEY_ENABLED: bool = False
    API_KEY: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance

    Returns:
        Settings: Application settings
    """
    return Settings()


# Global settings instance
settings = get_settings()

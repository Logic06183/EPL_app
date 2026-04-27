"""
Application configuration settings
Loaded from environment variables with sensible defaults
"""

import os
from typing import List


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "FPL AI Pro")
    APP_VERSION: str = os.getenv("APP_VERSION", "3.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    FPL_API_BASE: str = os.getenv("FPL_API_BASE", "https://fantasy.premierleague.com/api")

    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))

    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    API_PREFIX: str = os.getenv("API_PREFIX", "/api")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    PAYSTACK_SECRET_KEY: str = os.getenv("PAYSTACK_SECRET_KEY", "")
    PAYSTACK_PUBLIC_KEY: str = os.getenv("PAYSTACK_PUBLIC_KEY", "")


settings = Settings()

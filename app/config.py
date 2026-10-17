"""
Application configuration settings
Loaded from environment variables with sensible defaults
"""

import os


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "FPL AI Pro")
    APP_VERSION: str = os.getenv("APP_VERSION", "3.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    FPL_API_BASE: str = os.getenv("FPL_API_BASE", "https://fantasy.premierleague.com/api")

    # Skip the startup FPL fetch + model training (CI smoke tests, offline dev).
    SKIP_PREWARM: bool = os.getenv("SKIP_PREWARM", "false").lower() == "true"

    # auto: use the next-GW model only if it beats naive baselines in its own backtest
    # next_gw: always use it once trained · legacy: season-snapshot models only
    PREDICTION_MODEL: str = os.getenv("PREDICTION_MODEL", "auto").lower()

    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))

    # Public origin the SPA is served from. Firebase Hosting proxies /api/** to
    # Cloud Run, so in production the browser calls the API same-origin.
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "https://epl-prediction-app.web.app").rstrip("/")

    # Comma-separated. Only needed for cross-origin callers (local dev, native app).
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "https://epl-prediction-app.web.app,https://epl-prediction-app.firebaseapp.com,"
            "http://localhost:3000,http://localhost:5000,http://localhost:8080,capacitor://localhost,https://localhost",
        ).split(",")
        if o.strip()
    ]
    API_PREFIX: str = os.getenv("API_PREFIX", "/api")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()

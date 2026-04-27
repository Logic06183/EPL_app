"""
Common Pydantic response schemas
"""

from typing import Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    ai_enabled: bool = True
    version: str
    timestamp: str
    models_loaded: bool = False
    cache_available: bool = False


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str

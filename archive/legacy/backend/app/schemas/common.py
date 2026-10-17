"""Common schemas used across the application"""

from pydantic import BaseModel
from typing import Optional, Any, Dict


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = "healthy"
    version: str
    timestamp: str
    models_loaded: bool
    cache_available: bool


class ErrorResponse(BaseModel):
    """Error response"""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: str


class SuccessResponse(BaseModel):
    """Generic success response"""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

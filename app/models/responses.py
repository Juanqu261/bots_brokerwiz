"""
Modelos de respuesta estándar de la API.
"""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Respuesta genérica de la API."""
    success: bool
    message: str
    data: Optional[T] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Operación exitosa",
                "data": {"job_id": "abc123"},
                "timestamp": "2026-01-23T10:30:00"
            }
        }
    }


class ErrorResponse(BaseModel):
    """Respuesta de error."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "error": "Aseguradora no soportada",
                "detail": "Las aseguradoras válidas son: hdi, sura, axa...",
                "timestamp": "2026-01-23T10:30:00"
            }
        }
    }


class HealthResponse(BaseModel):
    """Respuesta del health check."""
    status: str = "healthy"
    service: str = "brokerwiz-api"
    version: str = "1.0.0"
    mqtt_connected: bool
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "brokerwiz-api",
                "version": "1.0.0",
                "mqtt_connected": True,
                "timestamp": "2026-01-23T10:30:00"
            }
        }
    }

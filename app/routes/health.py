"""
Rutas de health check.

GET /health - Estado del servicio y conexión MQTT
"""

from fastapi import APIRouter

from app.models.responses import HealthResponse
from mosquitto.mqtt_service import get_mqtt_service

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Verifica el estado del servicio y la conexión con MQTT."
)
async def health_check() -> HealthResponse:
    """
    Health check del servicio.
    """
    mqtt = get_mqtt_service()
    
    return HealthResponse(
        status="healthy" if mqtt.connected else "degraded",
        mqtt_connected=mqtt.connected
    )


@router.get(
    "/",
    include_in_schema=False
)
async def root():
    """Redirect a docs."""
    return {
        "service": "BrokerWiz API",
        "docs": "/docs",
        "health": "/health"
    }

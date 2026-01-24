"""
Rutas de health check.

GET /health - Estado del servicio y conexión MQTT
"""

from fastapi import APIRouter, Depends

from app.models.responses import HealthResponse
from mosquitto.mqtt_service import MQTTService, get_mqtt_service

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Verifica el estado del servicio y la conexión con MQTT."
)
async def health_check(
    mqtt: MQTTService = Depends(get_mqtt_service)
) -> HealthResponse:
    """
    Health check del servicio.
    """
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

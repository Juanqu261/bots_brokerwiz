"""
Rutas de health check.

GET /health - Estado del servicio y conexión MQTT

El health check usa caché para evitar que cada request haga un ping
real al broker MQTT.
"""

import time
from fastapi import APIRouter, Depends

from app.models.responses import HealthResponse
from mosquitto.mqtt_service import MQTTService, get_mqtt_service

router = APIRouter(tags=["Health"])

# Cache del estado de MQTT para evitar pings excesivos
_mqtt_status_cache = {
    "is_alive": False,
    "last_check": 0.0,
    "ttl": 30.0  # Segundos entre verificaciones reales
}


def reset_mqtt_cache():
    """Resetear caché de MQTT (útil para tests)."""
    _mqtt_status_cache["is_alive"] = False
    _mqtt_status_cache["last_check"] = 0.0
    _mqtt_status_cache["ttl"] = 30.0


async def _get_mqtt_status(mqtt: MQTTService) -> bool:
    """
    Obtener estado de MQTT con caché.
    
    - Si el caché es válido (< TTL segundos), retorna el valor cacheado
    - Si expiró, hace ping real y actualiza el caché
    
    Esto evita que múltiples requests hagan ping simultáneamente
    y que cada health check tome 3s cuando MQTT está caído.
    """
    now = time.time()
    cache = _mqtt_status_cache
    
    # Si el caché es válido, retornar valor cacheado
    if (now - cache["last_check"]) < cache["ttl"]:
        return cache["is_alive"]
    
    # Caché expirado: hacer ping real
    is_alive = await mqtt.ping(timeout=3.0)
    
    # Actualizar caché
    cache["is_alive"] = is_alive
    cache["last_check"] = now
    
    # Si está caído, reducir TTL para detectar recuperación más rápido
    cache["ttl"] = 5.0 if not is_alive else 30.0
    
    return is_alive


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Verifica el estado del servicio y la conexión con MQTT (con caché de 10s)."
)
async def health_check(
    mqtt: MQTTService = Depends(get_mqtt_service)
) -> HealthResponse:
    """
    Health check del servicio.
    
    Usa caché para evitar pings excesivos al broker MQTT:
    - Máximo 1 ping real cada 30 segundos (si healthy)
    - Máximo 1 ping real cada 5 segundos (si degraded, para detectar recuperación)
    """
    mqtt_alive = await _get_mqtt_status(mqtt)
    
    return HealthResponse(
        status="healthy" if mqtt_alive else "degraded",
        mqtt_connected=mqtt_alive
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

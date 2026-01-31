"""
Endpoint de metricas:

system health, queue depth, activity, and resources.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.services.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Metrics"])

# Singleton
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Accede o crea la instancia singleton."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(
            log_path="logs/worker.log",
            cache_ttl=30
        )
    return _metrics_collector


@router.get(
    "/metrics",
    summary="Metricas del sistema",
    description="""
    Toma metricas en tiempo real:
    - Service status (API, MQTT, workers)
    - Queue depth (total and per aseguradora)
    - Activity metrics (last 24h): jobs received, completed, failed, success rate
    - System resources: CPU, RAM, disk, Chrome processes
    - Error breakdown by error code
    
    Las metricas estan cacheadas cada 30 segundos.
    """
)
async def get_metrics():
    """
    Returns:
        JSON con metricas del sistema
    """
    try:
        collector = get_metrics_collector()
        metrics = await collector.get_metrics()
        return metrics.to_dict()
    
    except Exception as e:
        logger.error(f"Error tomando metricas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error tomando metricas: {str(e)}"
        )

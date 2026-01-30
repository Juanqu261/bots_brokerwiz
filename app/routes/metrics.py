"""
Metrics endpoint for system observability.

Provides real-time metrics about system health, queue depth, activity, and resources.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.services.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Metrics"])

# Global metrics collector instance (singleton)
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create metrics collector singleton."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(
            log_path="logs/worker.log",
            cache_ttl=30
        )
    return _metrics_collector


@router.get(
    "/metrics",
    summary="Get system metrics",
    description="""
    Get real-time system metrics including:
    - Service status (API, MQTT, workers)
    - Queue depth (total and per aseguradora)
    - Activity metrics (last 24h): jobs received, completed, failed, success rate
    - System resources: CPU, RAM, disk, Chrome processes
    - Error breakdown by error code
    
    Metrics are cached for 30 seconds to avoid excessive log parsing.
    """
)
async def get_metrics():
    """
    Get comprehensive system metrics.
    
    Returns:
        JSON with system metrics
    """
    try:
        collector = get_metrics_collector()
        metrics = await collector.get_metrics()
        return metrics.to_dict()
    
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting metrics: {str(e)}"
        )

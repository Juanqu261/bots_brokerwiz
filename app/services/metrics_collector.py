"""
Recolector de metricas para obervabilidad.

Incluye logs, MQTT broker y recursos del sistema.
"""

import time
import psutil
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from workers.log_parser import LogParser
from mosquitto.mqtt_stats_client import MQTTStatsClient

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Status de los sitemas."""
    api: str  # "healthy" | "unhealthy" | "unknown"
    mqtt: str
    workers_detected: int


@dataclass
class QueueMetrics:
    """MQTT queue metrics."""
    total_messages: int
    by_aseguradora: dict[str, int]


@dataclass
class ActivityMetrics:
    """Job metrics."""
    jobs_received: int
    jobs_completed: int
    jobs_failed: int
    success_rate: float
    by_aseguradora: dict[str, dict]


@dataclass
class ResourceMetrics:
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    chrome_processes: int


@dataclass
class SystemMetrics:
    """Complete system metrics."""
    timestamp: str
    services: ServiceStatus
    queue: QueueMetrics
    activity_24h: ActivityMetrics
    resources: ResourceMetrics
    errors: dict[str, int]
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "services": asdict(self.services),
            "queue": asdict(self.queue),
            "activity_24h": asdict(self.activity_24h),
            "resources": asdict(self.resources),
            "errors": self.errors
        }


class MetricsCollector:
    """
    Recolecta y devuelve las distintas metricas.
    
    Devuelve informacion cacheada cada 30 segundos.
    """
    
    def __init__(
        self,
        log_path: str | Path = "logs/worker.log",
        cache_ttl: int = 30
    ):
        """
        Args:
            log_path: Ruta a logs de los workers
            cache_ttl: Cache time to live
        """
        self.log_path = Path(log_path)
        self.cache_ttl = cache_ttl
        self.cached_metrics: Optional[SystemMetrics] = None
        self.cache_timestamp: float = 0.0
        
        self.log_parser = LogParser(self.log_path)
        self.mqtt_stats = MQTTStatsClient()
    
    async def get_metrics(self) -> SystemMetrics:
        """
        Obtiene las metricas actuales del sistema.
        
        Returns:
            SystemMetrics instance con todas las metricas
        """
        # Validar tiempo del cache
        if self._is_cache_valid():
            logger.debug("Retornando metricas cacheadas")
            return self.cached_metrics
        
        logger.debug("Recolectando metricas nuevas")
        
        # todas las metricas
        metrics = SystemMetrics(
            timestamp=datetime.utcnow().isoformat() + "Z",
            services=await self._get_service_status(),
            queue=await self._get_queue_metrics(),
            activity_24h=self._get_activity_metrics(),
            resources=self._get_resource_metrics(),
            errors=self._get_error_metrics()
        )
        
        self._update_cache(metrics)
        
        return metrics
    
    def _is_cache_valid(self) -> bool:
        """Validar que las metricas cacheadas aun sean validas."""
        if self.cached_metrics is None:
            return False
        
        age = time.time() - self.cache_timestamp
        return age < self.cache_ttl
    
    def _update_cache(self, metrics: SystemMetrics) -> None:
        self.cached_metrics = metrics
        self.cache_timestamp = time.time()
    
    async def _get_service_status(self) -> ServiceStatus:
        """
        Check status de los servicios.
        
        Returns:
            ServiceStatus con API, MQTT, y worker status
        """
        # API es siempre healthy si logra responderse la peticion
        api_status = "healthy"
        
        # Check MQTT broker
        mqtt_healthy = await self.mqtt_stats.is_broker_healthy(timeout=2.0)
        mqtt_status = "healthy" if mqtt_healthy else "unhealthy"
        
        # contar workers por procesos activos o logs
        workers_detected = self._count_active_workers()
        
        return ServiceStatus(
            api=api_status,
            mqtt=mqtt_status,
            workers_detected=workers_detected
        )
    
    async def _get_queue_metrics(self) -> QueueMetrics:
        """
        Get MQTT queue metrics.
        
        Returns:
            QueueMetrics with total and per-aseguradora counts
        """
        queue_data = await self.mqtt_stats.get_queue_depth(timeout=2.0)
        
        return QueueMetrics(
            total_messages=queue_data["total_messages"],
            by_aseguradora=queue_data["by_aseguradora"]
        )
    
    def _get_activity_metrics(self) -> ActivityMetrics:
        """
        Activadades de los jobs las ultimas 24h, segun logs
        
        Returns:
            ActivityMetrics con conteo de jobs y tasa de exito
        """
        activity_data = self.log_parser.parse_activity(hours=24)
        
        return ActivityMetrics(
            jobs_received=activity_data["jobs_received"],
            jobs_completed=activity_data["jobs_completed"],
            jobs_failed=activity_data["jobs_failed"],
            success_rate=activity_data["success_rate"],
            by_aseguradora=activity_data["by_aseguradora"]
        )
    
    def _get_resource_metrics(self) -> ResourceMetrics:
        """
        Obtener recursos del sistema.
        
        Returns:
            ResourceMetrics con CPU, RAM, disk, and procesos de chrome activos
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            chrome_processes = self._count_chrome_processes()
            
            return ResourceMetrics(
                cpu_percent=round(cpu_percent, 2),
                memory_percent=round(memory_percent, 2),
                disk_percent=round(disk_percent, 2),
                chrome_processes=chrome_processes
            )
        
        except Exception as e:
            logger.error(f"Error recolectando metricas: {e}")
            return ResourceMetrics(
                cpu_percent=-1.0,
                memory_percent=-1.0,
                disk_percent=-1.0,
                chrome_processes=-1
            )
    
    def _get_error_metrics(self) -> dict[str, int]:
        """
        Tomar conteo de códigos de error desde los logs (últimas 24h).
        
        Returns:
            Dictionary conteo de errores por código
        """
        return self.log_parser.parse_errors(hours=24)
    
    def _count_active_workers(self) -> int:
        """
        Returns:
            Numero de procesos worker activos
        """
        try:
            count = 0
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and 'mqtt_worker' in ' '.join(cmdline):
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return count
        except Exception as e:
            logger.warning(f"Error counting workers: {e}")
            return -1
    
    def _count_chrome_processes(self) -> int:
        """
        Returns:
            Numero de procesos de Chrome/Chromium activos
        """
        try:
            count = 0
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info.get('name', '').lower()
                    if 'chrome' in name or 'chromium' in name:
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return count
        except Exception as e:
            logger.warning(f"Error counting Chrome processes: {e}")
            return -1

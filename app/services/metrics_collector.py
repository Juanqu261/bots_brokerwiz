"""
Metrics collector for system observability.

Aggregates metrics from logs, MQTT broker, and system resources.
"""

import time
import logging
import psutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from workers.log_parser import LogParser
from mosquitto.mqtt_stats_client import MQTTStatsClient

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Status of system services."""
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
    """Job activity metrics."""
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
        """Convert to dictionary for API response."""
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
    Collects and aggregates system metrics.
    
    Caches metrics for 30 seconds to avoid excessive log parsing and MQTT queries.
    """
    
    def __init__(
        self,
        log_path: str | Path = "logs/worker.log",
        cache_ttl: int = 30
    ):
        """
        Initialize metrics collector.
        
        Args:
            log_path: Path to worker log file
            cache_ttl: Cache time-to-live in seconds (default: 30)
        """
        self.log_path = Path(log_path)
        self.cache_ttl = cache_ttl
        self.cached_metrics: Optional[SystemMetrics] = None
        self.cache_timestamp: float = 0.0
        
        self.log_parser = LogParser(self.log_path)
        self.mqtt_stats = MQTTStatsClient()
    
    async def get_metrics(self) -> SystemMetrics:
        """
        Get current system metrics (cached for 30s).
        
        Returns:
            SystemMetrics instance with all metrics
        """
        # Check cache validity
        if self._is_cache_valid():
            logger.debug("Returning cached metrics")
            return self.cached_metrics
        
        logger.debug("Collecting fresh metrics")
        
        # Collect all metrics
        metrics = SystemMetrics(
            timestamp=datetime.utcnow().isoformat() + "Z",
            services=await self._get_service_status(),
            queue=await self._get_queue_metrics(),
            activity_24h=self._get_activity_metrics(),
            resources=self._get_resource_metrics(),
            errors=self._get_error_metrics()
        )
        
        # Update cache
        self._update_cache(metrics)
        
        return metrics
    
    def _is_cache_valid(self) -> bool:
        """Check if cached metrics are still valid."""
        if self.cached_metrics is None:
            return False
        
        age = time.time() - self.cache_timestamp
        return age < self.cache_ttl
    
    def _update_cache(self, metrics: SystemMetrics) -> None:
        """Update metrics cache."""
        self.cached_metrics = metrics
        self.cache_timestamp = time.time()
    
    async def _get_service_status(self) -> ServiceStatus:
        """
        Check status of system services.
        
        Returns:
            ServiceStatus with API, MQTT, and worker status
        """
        # API is always healthy if this code is running
        api_status = "healthy"
        
        # Check MQTT broker
        mqtt_healthy = await self.mqtt_stats.is_broker_healthy(timeout=2.0)
        mqtt_status = "healthy" if mqtt_healthy else "unhealthy"
        
        # Detect workers by counting unique worker processes or log entries
        workers_detected = self._count_active_workers()
        
        return ServiceStatus(
            api=api_status,
            mqtt=mqtt_status,
            workers_detected=workers_detected
        )
    
    async def _get_queue_metrics(self) -> QueueMetrics:
        """
        Get MQTT queue depth metrics.
        
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
        Get job activity metrics from logs (last 24h).
        
        Returns:
            ActivityMetrics with job counts and success rate
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
        Get system resource metrics.
        
        Returns:
            ResourceMetrics with CPU, RAM, disk, and Chrome process count
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
            logger.error(f"Error collecting resource metrics: {e}")
            return ResourceMetrics(
                cpu_percent=-1.0,
                memory_percent=-1.0,
                disk_percent=-1.0,
                chrome_processes=-1
            )
    
    def _get_error_metrics(self) -> dict[str, int]:
        """
        Get error code counts from logs (last 24h).
        
        Returns:
            Dictionary mapping error codes to counts
        """
        return self.log_parser.parse_errors(hours=24)
    
    def _count_active_workers(self) -> int:
        """
        Count active worker processes.
        
        Returns:
            Number of detected worker processes
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
        Count running Chrome/Chromium processes.
        
        Returns:
            Number of Chrome processes
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

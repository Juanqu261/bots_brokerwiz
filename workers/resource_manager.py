"""
Resource Manager - Control de capacidad para ejecución de bots.

Gestiona los recursos del sistema (CPU, RAM, slots) para evitar
sobrecarga al ejecutar múltiples bots de Selenium simultáneamente.

Uso:
    from workers.resource_manager import ResourceManager, ResourceUnavailableError
    
    resource_manager = ResourceManager()
    
    async with resource_manager.acquire_slot("hdi", "job-123"):
        await bot.run()
"""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

import psutil

from config.settings import settings

logger = logging.getLogger(__name__)


class ResourceUnavailableError(Exception):
    """Excepción cuando no hay recursos suficientes para ejecutar un bot."""
    pass


class ResourceManager:
    """Gestiona recursos del sistema para limitar ejecución de bots."""
    
    # Valores por defecto
    DEFAULT_MAX_CPU = 85.0  # Porcentaje máximo de CPU
    DEFAULT_MAX_MEMORY = 85.0  # Porcentaje máximo de RAM
    
    def __init__(
        self,
        max_concurrent: Optional[int] = None,
        max_cpu_percent: Optional[float] = None,
        max_memory_percent: Optional[float] = None
    ):
        """
        Inicializar gestor de recursos.
        
        Args:
            max_concurrent: Máximo de bots simultáneos (default: settings.workers.MAX_CONCURRENT_BOTS)
            max_cpu_percent: Umbral de CPU para rechazar tareas (default: 80%)
            max_memory_percent: Umbral de RAM para rechazar tareas (default: 85%)
        """
        self._max_concurrent = max_concurrent or settings.workers.MAX_CONCURRENT_BOTS
        self._max_cpu = max_cpu_percent or self.DEFAULT_MAX_CPU
        self._max_memory = max_memory_percent or self.DEFAULT_MAX_MEMORY
        
        # Semáforo para limitar concurrencia
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        
        # Contador de bots activos
        self._active_count = 0
        self._lock = asyncio.Lock()
        
        # Registro de bots activos para debugging
        self._active_bots: dict[str, str] = {}  # job_id -> bot_id
        
        logger.info(
            f"ResourceManager inicializado: max_concurrent={self._max_concurrent}, "
            f"max_cpu={self._max_cpu}%, max_memory={self._max_memory}%"
        )
    
    async def check_resources(self) -> tuple[bool, str]:
        """
        Verificar si hay recursos disponibles para ejecutar un bot.
        
        Returns:
            Tupla (disponible, razón):
            - (True, "") si hay recursos disponibles
            - (False, "razón") si no hay recursos
        """
        # Verificar slots disponibles
        if self._active_count >= self._max_concurrent:
            return False, f"Sin slots disponibles ({self._active_count}/{self._max_concurrent})"
        
        # Verificar CPU (muestreo rápido)
        cpu = psutil.cpu_percent(interval=0.1)
        if cpu > self._max_cpu:
            return False, f"CPU al {cpu:.1f}% (máx: {self._max_cpu}%)"
        
        # Verificar memoria
        memory = psutil.virtual_memory().percent
        if memory > self._max_memory:
            return False, f"RAM al {memory:.1f}% (máx: {self._max_memory}%)"
        
        return True, ""
    
    @asynccontextmanager
    async def acquire_slot(self, bot_id: str, job_id: str):
        """
        Context manager para ejecutar un bot con control de recursos.
        
        Verifica recursos antes de adquirir el slot y lo libera al terminar.
        
        Args:
            bot_id: Identificador del bot (ej: "hdi", "sura")
            job_id: ID único del job/tarea
        
        Yields:
            None (el bot puede ejecutarse)
        
        Raises:
            ResourceUnavailableError: Si no hay recursos suficientes
        
        Uso:
            async with resource_manager.acquire_slot("hdi", "job-123"):
                bot = HDIBot(job_id, payload)
                await bot.run()
        """
        # Verificar recursos antes de intentar adquirir semáforo
        ok, reason = await self.check_resources()
        if not ok:
            logger.warning(f"[{bot_id}] Recursos no disponibles para job {job_id}: {reason}")
            raise ResourceUnavailableError(reason)
        
        # Adquirir slot del semáforo
        async with self._semaphore:
            # Registrar bot activo
            async with self._lock:
                self._active_count += 1
                self._active_bots[job_id] = bot_id
            
            logger.info(
                f"[{bot_id}] Slot adquirido para job {job_id} "
                f"({self._active_count}/{self._max_concurrent} activos)"
            )
            
            try:
                yield
            finally:
                # Liberar registro
                async with self._lock:
                    self._active_count -= 1
                    self._active_bots.pop(job_id, None)
                
                logger.info(
                    f"[{bot_id}] Slot liberado para job {job_id} "
                    f"({self._active_count}/{self._max_concurrent} activos)"
                )
    
    @property
    def active_bots(self) -> int:
        """Número de bots ejecutándose actualmente."""
        return self._active_count
    
    @property
    def available_slots(self) -> int:
        """Número de slots disponibles para nuevos bots."""
        return max(0, self._max_concurrent - self._active_count)
    
    @property
    def max_concurrent(self) -> int:
        """Máximo de bots concurrentes configurado."""
        return self._max_concurrent
    
    def get_active_jobs(self) -> dict[str, str]:
        """
        Obtener diccionario de jobs activos.
        
        Returns:
            Dict {job_id: bot_id} de bots actualmente ejecutándose
        """
        return self._active_bots.copy()
    
    def get_system_stats(self) -> dict:
        """
        Obtener estadísticas actuales del sistema.
        
        Returns:
            Dict con métricas de CPU, RAM y slots
        """
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available // (1024 * 1024),
            "active_bots": self._active_count,
            "available_slots": self.available_slots,
            "max_concurrent": self._max_concurrent,
            "active_jobs": self._active_bots.copy(),
        }


# Singleton para uso global en el worker
_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Obtener instancia singleton del ResourceManager."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager

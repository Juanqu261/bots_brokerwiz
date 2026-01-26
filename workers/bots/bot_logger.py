"""
Bot Logger - Configuración de logging específico por ejecución de bot.

Complementa logging_config.py (que maneja api.log y worker.log).
Este módulo crea logs AISLADOS específicos por ejecución de bot.

Estructura de directorios:
    logs/
    ├── api.log              ← Logs del API (gestionado por logging_config)
    ├── worker.log           ← Logs del worker (gestionado por logging_config)
    └── bots/
        └── {aseguradora}/
            └── {job_id}/
                ├── bot.log      ← Logs específicos de esta ejecución
                └── screenshots/ ← Screenshots de esta ejecución

Separación de logs:
    - worker.log: Solo eventos del worker (conexión MQTT, dispatch de tareas)
    - bot.log: Solo logs de esa ejecución específica (NO se propagan a worker.log)
"""

import logging
from pathlib import Path
from datetime import datetime

from config.logging_config import LOG_FORMAT, LOG_DATE_FORMAT, LOGS_DIR

# Directorio específico para logs de bots
BOTS_LOGS_DIR = LOGS_DIR / "bots"


class BotExecutionLogger:
    """
    Gestiona logging y directorios para una ejecución específica de bot.
    
    Crea estructura:
        logs/bots/{aseguradora}/{job_id}/
        ├── bot.log
        └── screenshots/
    """
    
    def __init__(self, bot_id: str, job_id: str):
        """
        Inicializar logger para una ejecución específica.
        
        Args:
            bot_id: Identificador del bot (ej: "hdi", "sura")
            job_id: ID único del job/tarea
        """
        self.bot_id = bot_id
        self.job_id = job_id
        
        # Crear estructura de directorios
        self.execution_dir = BOTS_LOGS_DIR / bot_id / job_id
        self.screenshots_dir = self.execution_dir / "screenshots"
        self.log_file = self.execution_dir / "bot.log"
        
        self._ensure_dirs()
        self._logger: logging.Logger | None = None
        self._file_handler: logging.FileHandler | None = None
    
    def _ensure_dirs(self) -> None:
        """Crear directorios necesarios."""
        self.execution_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    def get_logger(self) -> logging.Logger:
        """
        Obtener logger configurado para esta ejecución.
        
        El logger escribe SOLO a logs/bots/{bot}/{job}/bot.log
        """
        if self._logger:
            return self._logger
        
        # Crear logger específico para esta ejecución
        logger_name = f"bot.{self.bot_id}.{self.job_id}"
        self._logger = logging.getLogger(logger_name)
        
        # No propagar al root logger (evita duplicar en worker.log)
        self._logger.propagate = False
        
        # Evitar duplicación si ya tiene handlers
        if not self._logger.handlers:
            # Handler para archivo específico de esta ejecución
            self._file_handler = logging.FileHandler(
                self.log_file,
                encoding="utf-8"
            )
            self._file_handler.setLevel(logging.DEBUG)
            self._file_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
            )
            self._logger.addHandler(self._file_handler)
        
        return self._logger
    
    def get_screenshot_path(self, name: str = "capture") -> Path:
        """
        Generar path para un screenshot.
        
        Args:
            name: Nombre descriptivo del screenshot
        
        Returns:
            Path completo donde guardar el screenshot
        """
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{timestamp}_{name}.png"
        return self.screenshots_dir / filename
    
    def cleanup(self) -> None:
        """Limpiar handlers al terminar."""
        if self._file_handler and self._logger:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None
    
    @property
    def execution_path(self) -> Path:
        """Path al directorio de esta ejecución."""
        return self.execution_dir


def cleanup_old_bot_logs(max_age_hours: int = 24) -> int:
    """
    Eliminar logs de bots más viejos que max_age_hours.
    
    Args:
        max_age_hours: Edad máxima en horas
    
    Returns:
        Número de directorios eliminados
    """
    import shutil
    from time import time
    
    if not BOTS_LOGS_DIR.exists():
        return 0
    
    deleted = 0
    max_age_seconds = max_age_hours * 3600
    current_time = time()
    
    # Iterar sobre aseguradoras
    for aseguradora_dir in BOTS_LOGS_DIR.iterdir():
        if not aseguradora_dir.is_dir():
            continue
        
        # Iterar sobre ejecuciones
        for job_dir in aseguradora_dir.iterdir():
            if not job_dir.is_dir():
                continue
            
            # Verificar edad por fecha de modificación
            try:
                age = current_time - job_dir.stat().st_mtime
                if age > max_age_seconds:
                    shutil.rmtree(job_dir)
                    deleted += 1
            except Exception:
                pass
        
        # Si la carpeta de aseguradora quedó vacía, eliminarla
        try:
            if aseguradora_dir.exists() and not any(aseguradora_dir.iterdir()):
                aseguradora_dir.rmdir()
        except Exception:
            pass
    
    return deleted

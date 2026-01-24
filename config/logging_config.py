"""
Configuración centralizada de logging con rotación diaria.

Cada servicio escribe a su propio archivo en logs/:
- logs/api.log       → FastAPI
- logs/mosquitto.log → Broker MQTT (configurado en mosquitto.sh)
- logs/worker.log    → Workers de Selenium

Los archivos rotan a medianoche y se eliminan después de N días.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

from config.settings import settings

# Directorio de logs (relativo a la raíz del proyecto)
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configuración
LOG_RETENTION_DAYS = 1  # Mantener logs de solo 1 día
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(service_name: str = "api") -> logging.Logger:
    """
    Configura logging con rotación diaria para un servicio específico.
    
    Args:
        service_name: Nombre del servicio. Define el archivo de log:
                     - "api"    → logs/api.log
                     - "worker" → logs/worker.log
                     - etc.
    
    Returns:
        Logger raíz configurado
    """
    log_level = getattr(logging, settings.general.LOG_LEVEL, logging.INFO)
    log_filename = f"{service_name}.log"
    
    # Obtener logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Limpiar handlers existentes (evita duplicados en reloads)
    root_logger.handlers.clear()
    
    # Formatter común
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # Handler 1: Consola (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Handler 2: Archivo con rotación diaria
    log_file = LOGS_DIR / log_filename
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",      # Rotar a medianoche
        interval=1,           # Cada 1 día
        backupCount=LOG_RETENTION_DAYS,  # Mantener solo N días
        encoding="utf-8",
        utc=False             # Usar hora local
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Sufijo para archivos rotados: api.log.2026-01-23
    file_handler.suffix = "%Y-%m-%d"
    
    root_logger.addHandler(file_handler)
    
    # Log inicial
    logger = logging.getLogger(__name__)
    logger.info(f"Logging iniciado [{service_name}] → {log_file}")
    
    return root_logger


def get_log_file_path(service_name: str = "api") -> Path:
    """Retorna la ruta al archivo de log de un servicio."""
    return LOGS_DIR / f"{service_name}.log"


def get_logs_directory() -> Path:
    """Retorna el directorio de logs."""
    return LOGS_DIR


def list_log_files() -> list[dict]:
    """Lista todos los archivos de log disponibles."""
    files = []
    for f in sorted(LOGS_DIR.glob("*.log*"), reverse=True):
        files.append({
            "name": f.name,
            "size_kb": round(f.stat().st_size / 1024, 2),
            "modified": f.stat().st_mtime
        })
    return files

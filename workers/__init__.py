"""
Workers - Sistema de ejecución de tareas basado en MQTT.

Componentes:
- resource_manager: Control de capacidad (CPU, RAM, slots)
- mqtt_worker: Worker que procesa mensajes de MQTT
- bots/: Implementaciones de bots específicos
- selenium/: Utilidades de Selenium (driver, cookies, helpers)
- http/: Cliente HTTP para comunicación con API
"""

from workers.resource_manager import (
    ResourceManager,
    ResourceUnavailableError,
    get_resource_manager,
)

__all__ = [
    # Resource management
    "ResourceManager",
    "ResourceUnavailableError",
    "get_resource_manager",
]

"""
Script para iniciar la API de Bots BrokerWiz.

Uso:
    python -m scripts.start_api
    
    # O con uvicorn directamente:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
import os

# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mosquitto.mqtt_service import configure_event_loop

# Configurar event loop ANTES de importar uvicorn
configure_event_loop()

import uvicorn
from config.settings import settings


def main():
    """Iniciar servidor API."""
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                    Bots BrokerWiz API                         ║
╠═══════════════════════════════════════════════════════════════╣
║  Host:     {settings.api.API_HOST:<15}                              ║
║  Port:     {settings.api.API_PORT:<15}                              ║
║  Debug:    {str(settings.general.DEBUG):<15}                              ║
║  MQTT:     {settings.mqtt.MQTT_HOST}:{settings.mqtt.MQTT_PORT:<10}                         ║
╠═══════════════════════════════════════════════════════════════╣
║  Docs:     http://localhost:{settings.api.API_PORT}/docs                      ║
║  Health:   http://localhost:{settings.api.API_PORT}/health                    ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app.main:app",
        host=settings.api.API_HOST,
        port=settings.api.API_PORT,
        reload=settings.general.DEBUG,
        log_level=settings.general.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()

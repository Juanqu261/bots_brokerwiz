import sys
import asyncio
import pytest

from mosquitto.mqtt_service import configure_event_loop

# Configurar event loop ANTES de que pytest-asyncio cree loops
configure_event_loop()


@pytest.fixture(scope="session")
def event_loop_policy():
    """Retorna la política de event loop correcta según la plataforma."""
    import sys
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()

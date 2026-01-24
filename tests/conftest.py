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


@pytest.fixture
def api_key():
    """API key para autenticación."""
    from config.settings import settings
    return settings.api.API_KEY


@pytest.fixture
def auth_headers(api_key):
    """Headers de autenticación válidos."""
    return {"Authorization": f"Bearer {api_key}"}


@pytest.fixture
def sample_cotizacion_hdi():
    """Payload de ejemplo para cotización HDI."""
    return {
        "solicitud_aseguradora_id": "test-hdi-123",
        "payload": {
            "in_strTipoDoc": "CC",
            "in_strNumDoc": "1234567890",
            "in_strNombre": "Juan",
            "in_strApellido": "Test",
            "in_strPlaca": "TEST123",
            "in_strModelo": "2024"
        }
    }


@pytest.fixture
def sample_cotizacion_sura():
    """Payload de ejemplo para cotización SURA."""
    return {
        "solicitud_aseguradora_id": "test-sura-456",
        "payload": {
            "in_strNumDoc": "1234567890",
            "in_strNombreCompleto": "Juan Test",
            "in_strApellidoCompleto": "Pérez García",
            "in_strPlaca": "TEST456",
            "in_strModelo": "2024"
        }
    }


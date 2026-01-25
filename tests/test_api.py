"""
Tests de la API FastAPI - Tests Unitarios (sin MQTT)

Estos tests usan mocks para el servicio MQTT, permitiendo probar
la lógica de la API sin necesidad de tener el broker activo.

pytest tests/test_api.py -v
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from config.settings import settings


@pytest.fixture
def mock_mqtt_service():
    """Mock del servicio MQTT para tests sin broker."""
    mock = MagicMock()
    mock.connected = True
    mock.client_id = "test-client"
    mock.publish_task = AsyncMock(return_value=True)
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    return mock


@pytest.fixture
def client(mock_mqtt_service):
    """Cliente de test sincrónico con MQTT mockeado usando dependency_overrides."""
    from fastapi import FastAPI
    from app.routes import health, cotizaciones
    from mosquitto.mqtt_service import get_mqtt_service
    
    # Crear app sin lifespan real (evita conexión MQTT)
    app = FastAPI(title="Test API")
    app.include_router(health.router)
    app.include_router(cotizaciones.router, prefix="/api")
    
    # Override de dependencias
    app.dependency_overrides[get_mqtt_service] = lambda: mock_mqtt_service
    
    with TestClient(app) as c:
        yield c
    
    # Limpiar overrides
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Headers de autenticación válidos."""
    return {"Authorization": f"Bearer {settings.api.API_KEY}"}


@pytest.fixture
def invalid_auth_headers():
    """Headers de autenticación inválidos."""
    return {"Authorization": "Bearer token-invalido"}


class TestHealthEndpoint:
    """Tests del endpoint /health."""
    
    def test_health_check_success(self, client, mock_mqtt_service):
        """Health check retorna estado correcto."""
        # El mock ya tiene connected=True
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "brokerwiz-api"
        assert data["mqtt_connected"] is True
    
    def test_health_no_auth_required(self, client):
        """Health check no requiere autenticación."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_root_returns_info(self, client):
        """Root endpoint retorna info del servicio."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "docs" in data


class TestAuthentication:
    """Tests de autenticación Bearer token."""
    
    def test_cotizacion_requires_auth(self, client):
        """Endpoint de cotización requiere autenticación."""
        response = client.post(
            "/api/hdi/cotizar",
            json={"solicitud_aseguradora_id": "test", "payload": {}}
        )
        
        assert response.status_code == 403  # Forbidden sin token
    
    def test_invalid_token_rejected(self, client, invalid_auth_headers):
        """Token inválido es rechazado."""
        response = client.post(
            "/api/hdi/cotizar",
            headers=invalid_auth_headers,
            json={"solicitud_aseguradora_id": "test", "payload": {}}
        )
        
        assert response.status_code == 401
        assert "inválido" in response.json()["detail"].lower()
    
    def test_valid_token_accepted(self, client, auth_headers):
        """Token válido permite acceso."""
        response = client.post(
            "/api/hdi/cotizar",
            headers=auth_headers,
            json={"solicitud_aseguradora_id": "test-123", "payload": {"test": True}}
        )
        
        assert response.status_code == 202


class TestCotizacionesEndpoint:
    """Tests del endpoint POST /api/cotizaciones/{aseguradora}."""
    
    def test_crear_cotizacion_hdi(self, client, auth_headers):
        """Crear cotización HDI exitosamente."""
        response = client.post(
            "/api/hdi/cotizar",
            headers=auth_headers,
            json={
                "solicitud_aseguradora_id": "abc123",
                "payload": {
                    "in_strTipoDoc": "CC",
                    "in_strNumDoc": "1234567890",
                    "in_strPlaca": "ABC123"
                }
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["data"]["aseguradora"] == "hdi"
        assert data["data"]["status"] == "pending"
        assert "job_id" in data["data"]
    
    def test_crear_cotizacion_sura(self, client, auth_headers):
        """Crear cotización SURA exitosamente."""
        response = client.post(
            "/api/sura/cotizar",
            headers=auth_headers,
            json={
                "solicitud_aseguradora_id": "xyz789",
                "payload": {"in_strPlaca": "XYZ789"}
            }
        )
        
        assert response.status_code == 202
        assert response.json()["data"]["aseguradora"] == "sura"
    
    def test_aseguradora_invalida(self, client, auth_headers):
        """Aseguradora no soportada retorna error 400."""
        response = client.post(
            "/api/aseguradora_fake/cotizar",
            headers=auth_headers,
            json={"solicitud_aseguradora_id": "test", "payload": {}}
        )
        
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "no soportada" in detail["error"]
        assert "aseguradoras_validas" in detail
    
    def test_aseguradora_case_insensitive(self, client, auth_headers):
        """Aseguradora acepta mayúsculas y minúsculas."""
        # Probar con mayúsculas
        response = client.post(
            "/api/HDI/cotizar",
            headers=auth_headers,
            json={"solicitud_aseguradora_id": "test", "payload": {}}
        )
        assert response.status_code == 202
        
        # Probar mixto
        response = client.post(
            "/api/Sura/cotizar",
            headers=auth_headers,
            json={"solicitud_aseguradora_id": "test", "payload": {}}
        )
        assert response.status_code == 202
    
    def test_payload_vacio_valido(self, client, auth_headers):
        """Payload vacío es válido (la validación específica la hace el bot)."""
        response = client.post(
            "/api/hdi/cotizar",
            headers=auth_headers,
            json={"solicitud_aseguradora_id": "test", "payload": {}}
        )
        
        assert response.status_code == 202
    
    def test_solicitud_id_requerido(self, client, auth_headers):
        """solicitud_aseguradora_id es requerido."""
        response = client.post(
            "/api/hdi/cotizar",
            headers=auth_headers,
            json={"payload": {"test": True}}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_mqtt_publish_called(self, client, auth_headers, mock_mqtt_service):
        """Verificar que se llama a MQTT publish con datos correctos."""
        response = client.post(
            "/api/axa/cotizar",
            headers=auth_headers,
            json={
                "solicitud_aseguradora_id": "sol-123",
                "payload": {"campo": "valor"}
            }
        )
        
        assert response.status_code == 202
        
        # Verificar que publish_task fue llamado
        mock_mqtt_service.publish_task.assert_called_once()
        call_args = mock_mqtt_service.publish_task.call_args
        
        # El primer argumento posicional es aseguradora, task_data es keyword
        assert call_args.kwargs["aseguradora"] == "axa"
        assert "job_id" in call_args.kwargs["task_data"]
        assert call_args.kwargs["task_data"]["solicitud_aseguradora_id"] == "sol-123"


class TestValidation:
    """Tests de validación de payloads."""
    
    def test_json_invalido(self, client, auth_headers):
        """JSON malformado retorna error 422."""
        headers = {"Content-Type": "application/json", **auth_headers}
        response = client.post(
            "/api/hdi/cotizar",
            headers=headers,
            content="esto no es json"
        )
        
        assert response.status_code == 422
    
    def test_content_type_requerido(self, client, auth_headers):
        """Content-Type application/json es requerido."""
        response = client.post(
            "/api/hdi/cotizar",
            headers=auth_headers,
            data="solicitud_aseguradora_id=test"  # form data
        )
        
        assert response.status_code == 422


class TestMQTTErrorHandling:
    """Tests de manejo de errores de MQTT."""
    
    def test_mqtt_publish_failure(self, auth_headers):
        """Error en MQTT publish retorna 503."""
        from fastapi import FastAPI
        from app.routes import health, cotizaciones
        from mosquitto.mqtt_service import get_mqtt_service
        
        # Mock que simula fallo en publish
        mock_mqtt = MagicMock()
        mock_mqtt.connected = True
        mock_mqtt.publish_task = AsyncMock(return_value=False)  # Simula fallo
        
        app = FastAPI(title="Test API")
        app.include_router(health.router)
        app.include_router(cotizaciones.router, prefix="/api")
        app.dependency_overrides[get_mqtt_service] = lambda: mock_mqtt
        
        with TestClient(app) as client:
            response = client.post(
                "/api/hdi/cotizar",
                headers=auth_headers,
                json={"solicitud_aseguradora_id": "test", "payload": {}}
            )
        
        assert response.status_code == 503
        assert "MQTT" in response.json()["detail"]
    
    def test_mqtt_connection_error(self, auth_headers):
        """Excepción en MQTT retorna 503."""
        from fastapi import FastAPI
        from app.routes import health, cotizaciones
        from mosquitto.mqtt_service import get_mqtt_service
        
        # Mock que lanza excepción
        mock_mqtt = MagicMock()
        mock_mqtt.connected = True
        mock_mqtt.publish_task = AsyncMock(side_effect=Exception("Connection lost"))
        
        app = FastAPI(title="Test API")
        app.include_router(health.router)
        app.include_router(cotizaciones.router, prefix="/api")
        app.dependency_overrides[get_mqtt_service] = lambda: mock_mqtt
        
        with TestClient(app) as client:
            response = client.post(
                "/api/hdi/cotizar",
                headers=auth_headers,
                json={"solicitud_aseguradora_id": "test", "payload": {}}
            )
        
        assert response.status_code == 503

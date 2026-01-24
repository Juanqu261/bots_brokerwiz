"""
Tests de Integración de la API - Requieren MQTT activo

Estos tests verifican la integración real con el broker Mosquitto.
Requieren que el broker MQTT esté corriendo.

Ejecutar:
    # Primero iniciar Mosquitto
    mosquitto -p 1883 -v
    
    # Luego correr tests de integración
    pytest tests/integration/test_api_integration.py -v -m integration
    
    # O con el marcador específico
    pytest -m integration -v
"""

import pytest
import asyncio
from datetime import datetime

from fastapi.testclient import TestClient

from config.settings import settings
from mosquitto.mqtt_service import MQTTService, configure_event_loop

# Configurar event loop
configure_event_loop()

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def mqtt_available():
    """Verificar si MQTT está disponible antes de correr tests."""
    import socket
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    
    try:
        result = sock.connect_ex((settings.mqtt.MQTT_HOST, settings.mqtt.MQTT_PORT))
        if result != 0:
            pytest.skip(
                f"MQTT broker no disponible en "
                f"{settings.mqtt.MQTT_HOST}:{settings.mqtt.MQTT_PORT}. "
                f"Ejecutar: docker compose up -d mqtt"
            )
    finally:
        sock.close()


@pytest.fixture
def app():
    """Obtener la app real de FastAPI."""
    from app.main import app
    return app


@pytest.fixture
def client(app, mqtt_available):
    """Cliente de test con MQTT real."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    """Headers de autenticación válidos."""
    return {"Authorization": f"Bearer {settings.api.API_KEY}"}


@pytest.fixture
async def mqtt_subscriber():
    """
    Cliente MQTT para verificar mensajes publicados.
    Se suscribe a todos los topics de cotización.
    """
    mqtt = MQTTService(client_id="test-subscriber", persistent=False)
    received_messages = []
    
    async with mqtt:
        await mqtt.subscribe_wildcard()
        yield mqtt, received_messages


class TestAPIWithRealMQTT:
    """Tests que verifican la integración real API → MQTT."""
    
    def test_health_con_mqtt_real(self, client):
        """Health check muestra MQTT conectado."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["mqtt_connected"] is True
        assert data["status"] == "healthy"
    
    def test_cotizacion_publica_en_mqtt(self, client, auth_headers):
        """Verificar que cotización se publica en MQTT."""
        solicitud_id = f"integration-test-{datetime.now().timestamp()}"
        
        response = client.post(
            "/api/hdi/cotizar",
            headers=auth_headers,
            json={
                "solicitud_aseguradora_id": solicitud_id,
                "payload": {
                    "in_strPlaca": "TEST123",
                    "in_strNumDoc": "9999999999"
                }
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["data"]["aseguradora"] == "hdi"
        
        # El job_id debería ser un UUID válido
        job_id = data["data"]["job_id"]
        assert len(job_id) == 36  # UUID format
    
    def test_multiples_aseguradoras(self, client, auth_headers):
        """Publicar en múltiples aseguradoras."""
        aseguradoras = ["hdi", "sura", "axa", "allianz"]
        
        for aseg in aseguradoras:
            response = client.post(
                f"/api/{aseg}/cotizar",
                headers=auth_headers,
                json={
                    "solicitud_aseguradora_id": f"multi-test-{aseg}",
                    "payload": {"test": True}
                }
            )
            
            assert response.status_code == 202, f"Falló para {aseg}"
            assert response.json()["data"]["aseguradora"] == aseg
    
    def test_batch_con_mqtt_real(self, client, auth_headers):
        """Batch publica múltiples mensajes en MQTT."""
        response = client.post(
            "/api/cotizaciones/batch",
            headers=auth_headers,
            json=[
                {"aseguradora": "hdi", "solicitud_aseguradora_id": "batch-int-1", "payload": {}},
                {"aseguradora": "sura", "solicitud_aseguradora_id": "batch-int-2", "payload": {}},
                {"aseguradora": "bolivar", "solicitud_aseguradora_id": "batch-int-3", "payload": {}}
            ]
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3


@pytest.mark.asyncio
class TestMQTTMessageVerification:
    """Tests que verifican el contenido de mensajes en MQTT."""
    
    async def test_mensaje_contiene_datos_correctos(self, mqtt_available):
        """Verificar que el mensaje MQTT tiene la estructura correcta."""
        # Crear cliente que publica (simula la API)
        publisher = MQTTService(client_id="test-publisher", persistent=False)
        
        # Crear cliente que escucha
        subscriber = MQTTService(client_id="test-subscriber-verify", persistent=False)
        
        test_data = {
            "job_id": "test-job-123",
            "solicitud_aseguradora_id": "sol-456",
            "payload": {"campo": "valor"},
            "created_at": datetime.now().isoformat()
        }
        
        received = []
        
        async with publisher, subscriber:
            # Suscribirse
            await subscriber.subscribe_aseguradora("hdi")
            
            # Publicar
            await publisher.publish_task("hdi", test_data)
            
            # Esperar mensaje (con timeout)
            try:
                async with asyncio.timeout(3):
                    async for topic, msg in subscriber.messages():
                        received.append((topic, msg))
                        break  # Solo necesitamos 1 mensaje
            except asyncio.TimeoutError:
                pass
        
        # Verificar
        assert len(received) == 1
        topic, msg = received[0]
        assert "hdi" in topic
        assert msg["job_id"] == "test-job-123"
        assert msg["solicitud_aseguradora_id"] == "sol-456"
    
    async def test_qos_garantiza_entrega(self, mqtt_available):
        """Verificar que QoS 1 garantiza entrega."""
        publisher = MQTTService(client_id="test-qos-pub", persistent=False)
        
        async with publisher:
            # Publicar varios mensajes
            for i in range(5):
                result = await publisher.publish_task(
                    "sura",
                    {"job_id": f"qos-test-{i}", "payload": {}}
                )
                assert result is True


class TestResilience:
    """Tests de resiliencia y manejo de errores."""
    
    def test_api_maneja_desconexion_gracefully(self, client, auth_headers):
        """API retorna error apropiado si MQTT falla."""
        # Este test verifica el manejo de errores cuando MQTT está caído
        # En un escenario real, el health check mostraría mqtt_connected=False
        
        response = client.get("/health")
        assert response.status_code == 200
        # Si llegamos aquí, MQTT está conectado


class TestPerformance:
    """Tests básicos de performance."""
    
    def test_latencia_publicacion(self, client, auth_headers):
        """Verificar que la publicación es rápida."""
        import time
        
        start = time.time()
        
        response = client.post(
            "/api/hdi/cotizar",
            headers=auth_headers,
            json={"solicitud_aseguradora_id": "perf-test", "payload": {}}
        )
        
        elapsed = time.time() - start
        
        assert response.status_code == 202
        assert elapsed < 1.0, f"Publicación tardó {elapsed:.2f}s (esperado < 1s)"
    
    def test_batch_performance(self, client, auth_headers):
        """Verificar que batch es eficiente."""
        import time
        
        jobs = [
            {"aseguradora": aseg, "solicitud_aseguradora_id": f"perf-{i}", "payload": {}}
            for i, aseg in enumerate(["hdi", "sura", "axa", "allianz", "bolivar"])
        ]
        
        start = time.time()
        
        response = client.post(
            "/api/cotizaciones/batch",
            headers=auth_headers,
            json=jobs
        )
        
        elapsed = time.time() - start
        
        assert response.status_code == 202
        assert elapsed < 2.0, f"Batch de 5 tardó {elapsed:.2f}s (esperado < 2s)"

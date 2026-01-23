"""
Tests para validar que la cola MQTT funciona como:
Producer -> Broker -> Consumer

Uso:
mosquitto -p 1883 -v
pytest -m mqtt -v
"""

import asyncio
import pytest

from mosquitto.mqtt_service import MQTTService


@pytest.mark.mqtt
class TestMQTTQueueBasic:
    """
    Tests básicos para validar que la cola MQTT funciona (async)
    """

    @pytest.mark.asyncio
    async def test_publish_and_subscribe_single_aseguradora(self):
        """
        Un cliente publica en bots/queue/hdi
        Otro cliente se suscribe a bots/queue/hdi
        El mensaje debe llegar correctamente.
        """
        received_messages = []

        async with MQTTService() as subscriber:
            await subscriber.subscribe_aseguradora("hdi")
            
            async with MQTTService() as producer:
                # Publicar tarea
                task = {
                    "job_id": "job-test-001",
                    "payload": {"foo": "bar"}
                }
                published = await producer.publish_task("hdi", task)
                assert published is True

            # Recibir mensaje con timeout
            try:
                async with asyncio.timeout(3):
                    async for topic, message in subscriber.messages():
                        received_messages.append((topic, message))
                        break  # Solo esperamos 1 mensaje
            except asyncio.TimeoutError:
                pass

        assert len(received_messages) == 1
        topic, message = received_messages[0]
        assert topic.endswith("/hdi")
        assert message["job_id"] == "job-test-001"
        assert message["payload"]["foo"] == "bar"

    @pytest.mark.asyncio
    async def test_publish_and_subscribe_wildcard(self):
        """
        Un cliente se suscribe a bots/queue/+
        Debe recibir mensajes de cualquier aseguradora.
        """
        received = []

        async with MQTTService() as subscriber:
            await subscriber.subscribe_wildcard()
            
            async with MQTTService() as producer:
                # Publicar tareas a distintas aseguradoras
                await producer.publish_task("hdi", {"job_id": "job-hdi", "payload": {}})
                await producer.publish_task("sura", {"job_id": "job-sura", "payload": {}})
                await producer.publish_task("mapfre", {"job_id": "job-mapfre", "payload": {}})

            # Recibir mensajes con timeout
            try:
                async with asyncio.timeout(5):
                    async for topic, message in subscriber.messages():
                        received.append((topic, message))
                        if len(received) >= 3:
                            break
            except asyncio.TimeoutError:
                pass

        # Deben llegar las 3 tareas
        assert len(received) == 3
        job_ids = {msg["job_id"] for _, msg in received}
        assert job_ids == {"job-hdi", "job-sura", "job-mapfre"}

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test de conexión y desconexión básica"""
        mqtt = MQTTService()
        
        assert mqtt.connected is False
        await mqtt.connect()
        assert mqtt.connected is True
        await mqtt.disconnect()
        assert mqtt.connected is False

    @pytest.mark.asyncio
    async def test_publish_without_connection_fails(self):
        """Publicar sin conexión debe retornar False"""
        mqtt = MQTTService()
        result = await mqtt.publish_task("hdi", {"job_id": "test"})
        assert result is False
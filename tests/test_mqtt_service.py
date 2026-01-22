"""
mosquitto -p 1883 -v
pytest -m mqtt
"""

import time
import pytest

from app.services.mqtt_service import MQTTService


@pytest.mark.integration
@pytest.mark.mqtt
class TestMQTTQueueBasic:
    """
    Tests básicos para validar que la cola MQTT funciona como:
    Producer -> Broker -> Consumer
    """

    def test_publish_and_subscribe_single_aseguradora(self):
        """
        Un cliente publica en bots/queue/hdi
        Otro cliente se suscribe a bots/queue/hdi
        El mensaje debe llegar correctamente.
        """
        received_messages = []

        def on_message(topic, message):
            received_messages.append((topic, message))

        # Subscriber (simula un bot)
        subscriber = MQTTService()
        assert subscriber.connect() is True
        subscriber.subscribe_aseguradora("hdi", callback=on_message)
        subscriber.loop_start()
        self._wait_until_connected(subscriber)

        # Producer (simula la API)
        producer = MQTTService()
        assert producer.connect() is True
        producer.loop_start()
        self._wait_until_connected(producer)

        # Publicar tarea
        task = {
            "job_id": "job-test-001",
            "payload": {"foo": "bar"}
        }

        published = producer.publish_task("hdi", task)
        assert published is True

        self._wait_for_messages(received_messages, expected=1)

        subscriber.loop_stop()
        producer.loop_stop()

        assert len(received_messages) == 1
        topic, message = received_messages[0]

        assert topic.endswith("/hdi")
        assert message["job_id"] == "job-test-001"
        assert message["payload"]["foo"] == "bar"


    def test_publish_and_subscribe_wildcard(self):
        """
        Un cliente se suscribe a bots/queue/+
        Debe recibir mensajes de cualquier aseguradora.
        """
        received = []

        def on_any(topic, message):
            received.append((topic, message))

        # Subscriber genérico (worker global)
        wildcard_subscriber = MQTTService()
        assert wildcard_subscriber.connect() is True
        wildcard_subscriber.subscribe_wildcard(callback=on_any)
        wildcard_subscriber.loop_start()
        self._wait_until_connected(wildcard_subscriber)

        # Producer
        producer = MQTTService()
        assert producer.connect() is True
        producer.loop_start()
        self._wait_until_connected(producer)

        # Publicar tareas a distintas aseguradoras
        producer.publish_task("hdi", {"job_id": "job-hdi", "payload": {}})
        producer.publish_task("sura", {"job_id": "job-sura", "payload": {}})
        producer.publish_task("mapfre", {"job_id": "job-mapfre", "payload": {}})

        self._wait_for_messages(received, expected=3)

        wildcard_subscriber.loop_stop()
        producer.loop_stop()

        # Deben llegar las 3 tareas
        assert len(received) == 3

        job_ids = {msg["job_id"] for _, msg in received}
        assert job_ids == {"job-hdi", "job-sura", "job-mapfre"}


    @staticmethod
    def _wait_until_connected(mqtt_service, timeout=5):
        start = time.time()
        while not mqtt_service.connected:
            if time.time() - start > timeout:
                raise TimeoutError("MQTT no se conectó a tiempo")
            time.sleep(0.05)

    @staticmethod
    def _wait_for_messages(container, expected, timeout=5):
        start = time.time()
        while len(container) < expected:
            if time.time() - start > timeout:
                break
            time.sleep(0.05)
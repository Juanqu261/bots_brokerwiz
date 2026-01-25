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


@pytest.mark.mqtt
class TestSharedSubscriptions:
    """
    Tests para validar Shared Subscriptions (MQTT 5).
    
    Shared Subscriptions permiten que múltiples workers compartan
    la carga de una cola. Cada mensaje se entrega a UN SOLO worker
    del grupo (distribución round-robin).
    
    Requiere: Mosquitto 2.0+ con MQTT 5 habilitado.
    """

    @pytest.mark.asyncio
    async def test_shared_subscription_distributes_messages(self):
        """
        Dos suscriptores con shared subscription deben recibir
        mensajes distribuidos (round-robin), no duplicados.
        """
        worker_a_messages = []
        worker_b_messages = []
        
        # Crear dos workers con shared subscription
        worker_a = MQTTService(client_id="test-worker-a", persistent=False)
        worker_b = MQTTService(client_id="test-worker-b", persistent=False)
        producer = MQTTService(client_id="test-producer", persistent=False)
        
        async with worker_a, worker_b, producer:
            # Ambos workers se suscriben al mismo grupo compartido
            await worker_a.subscribe_shared(group="test-group", aseguradora="hdi")
            await worker_b.subscribe_shared(group="test-group", aseguradora="hdi")
            
            # Pequeña pausa para asegurar que las suscripciones estén activas
            await asyncio.sleep(0.2)
            
            # Publicar 4 mensajes
            for i in range(4):
                await producer.publish_task("hdi", {
                    "job_id": f"shared-test-{i}",
                    "seq": i
                })
                await asyncio.sleep(0.05)  # Pequeña pausa entre mensajes
            
            # Recolectar mensajes de ambos workers con timeout
            async def collect_messages(mqtt_client, message_list, max_messages=4):
                try:
                    async with asyncio.timeout(3):
                        async for topic, message in mqtt_client.messages():
                            message_list.append(message)
                            if len(message_list) >= max_messages:
                                break
                except asyncio.TimeoutError:
                    pass
            
            # Ejecutar recolección en paralelo
            await asyncio.gather(
                collect_messages(worker_a, worker_a_messages, 2),
                collect_messages(worker_b, worker_b_messages, 2),
            )
        
        # Verificaciones
        total_received = len(worker_a_messages) + len(worker_b_messages)
        
        # Deben haber llegado los 4 mensajes en total
        assert total_received == 4, f"Se esperaban 4 mensajes, llegaron {total_received}"
        
        # Verificar que no hay duplicados (ningún job_id en ambos workers)
        worker_a_jobs = {m["job_id"] for m in worker_a_messages}
        worker_b_jobs = {m["job_id"] for m in worker_b_messages}
        duplicates = worker_a_jobs & worker_b_jobs
        assert len(duplicates) == 0, f"Mensajes duplicados: {duplicates}"
        
        # Verificar distribución (ambos workers recibieron algo)
        assert len(worker_a_messages) > 0, "Worker A no recibió mensajes"
        assert len(worker_b_messages) > 0, "Worker B no recibió mensajes"
        
        # Todos los job_ids esperados deben estar presentes
        all_jobs = worker_a_jobs | worker_b_jobs
        expected_jobs = {f"shared-test-{i}" for i in range(4)}
        assert all_jobs == expected_jobs, f"Jobs faltantes: {expected_jobs - all_jobs}"

    @pytest.mark.asyncio
    async def test_shared_vs_normal_subscription(self):
        """
        Comparar comportamiento:
        - Suscripción normal: TODOS reciben el mensaje
        - Shared subscription: Solo UNO recibe el mensaje
        """
        normal_a_messages = []
        normal_b_messages = []
        
        # Dos suscriptores NORMALES (sin shared)
        sub_a = MQTTService(client_id="normal-sub-a", persistent=False)
        sub_b = MQTTService(client_id="normal-sub-b", persistent=False)
        producer = MQTTService(client_id="normal-producer", persistent=False)
        
        async with sub_a, sub_b, producer:
            # Suscripción NORMAL (ambos reciben todo)
            await sub_a.subscribe_aseguradora("sura")
            await sub_b.subscribe_aseguradora("sura")
            
            await asyncio.sleep(0.2)
            
            # Publicar 1 mensaje
            await producer.publish_task("sura", {"job_id": "normal-test", "type": "broadcast"})
            
            # Recolectar
            async def collect_one(mqtt_client, message_list):
                try:
                    async with asyncio.timeout(2):
                        async for topic, message in mqtt_client.messages():
                            message_list.append(message)
                            break
                except asyncio.TimeoutError:
                    pass
            
            await asyncio.gather(
                collect_one(sub_a, normal_a_messages),
                collect_one(sub_b, normal_b_messages),
            )
        
        # Con suscripción NORMAL, AMBOS deben recibir el mensaje
        assert len(normal_a_messages) == 1, "Sub A no recibió (normal)"
        assert len(normal_b_messages) == 1, "Sub B no recibió (normal)"
        assert normal_a_messages[0]["job_id"] == "normal-test"
        assert normal_b_messages[0]["job_id"] == "normal-test"

    @pytest.mark.asyncio
    async def test_subscribe_shared_method(self):
        """Test del método subscribe_shared()"""
        mqtt = MQTTService(client_id="test-shared-method", persistent=False)
        
        async with mqtt:
            # Suscripción shared a todas las aseguradoras
            result = await mqtt.subscribe_shared(group="workers")
            assert result is True
            assert "$share/workers/" in list(mqtt._subscriptions)[0]
            
        # Suscripción shared a aseguradora específica
        mqtt2 = MQTTService(client_id="test-shared-method-2", persistent=False)
        async with mqtt2:
            result = await mqtt2.subscribe_shared(group="workers-hdi", aseguradora="hdi")
            assert result is True
            subscription = list(mqtt2._subscriptions)[0]
            assert "$share/workers-hdi/" in subscription
            assert "/hdi" in subscription
            
"""
MQTT Service - Cliente asíncrono para Mosquitto con aiomqtt

Servicio completamente async para integración con FastAPI y workers de Selenium.
No bloquea el event loop, ideal para alta concurrencia.

Funcionalidades:
- Publicar tareas por aseguradora (bots/queue/{aseguradora})
- Suscribirse a topics específicos o wildcard
- Last Will Testament (LWT) para detección de desconexión
- Reconexión automática con backoff exponencial
"""

import sys
import json
import uuid
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, AsyncIterator, Callable, Awaitable

import aiomqtt
from config.settings import settings

logger = logging.getLogger(__name__)

# Type alias para handlers de mensajes
MessageHandler = Callable[[str, Dict[str, Any]], Awaitable[None]]


def configure_event_loop() -> None:
    """
    Configura el event loop correcto según la plataforma.
    
    En Windows, aiomqtt requiere SelectorEventLoop en lugar del
    ProactorEventLoop por defecto (que no soporta add_reader/add_writer).
    
    Llamar ANTES de cualquier operación async:
    - Al inicio de main.py de FastAPI
    - Al inicio de scripts de workers
    
    Uso:
        from mosquitto.mqtt_service import configure_event_loop
        configure_event_loop()
        
        # Ahora puedes usar asyncio.run(), uvicorn, etc.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.debug("Event loop configurado: WindowsSelectorEventLoopPolicy")
    # En Linux/macOS no se requiere configuración especial


class MQTTService:
    """
    Cliente MQTT asíncrono para comunicación con Mosquitto.
    
    Uso para API:
    -----------------------------------------------------------
    mqtt = MQTTService(client_id="brokerwiz-api", persistent=False)
    async with mqtt:
        await mqtt.publish_task("hdi", {"job_id": "123", "payload": {...}})
    
    Uso con persistencia (para workers):
    ------------------------------------
    mqtt = MQTTService(client_id="worker-hdi-1", persistent=True)
    async with mqtt:
        await mqtt.subscribe_wildcard()
        async for topic, message in mqtt.messages():
            await process_message(topic, message)
    """
    
    def __init__(
        self, 
        client_id: Optional[str] = None,
        persistent: bool = False
    ):
        """
        Inicializar cliente MQTT.
        
        Args:
            client_id: ID único del cliente. 
                      - Para API: dejar None (genera UUID automático)
                      - Para workers: usar ID fijo ej: "worker-1", "worker-hdi-1"
            persistent: Si True, habilita sesiones persistentes (clean_session=False).
                       REQUIERE client_id fijo para funcionar correctamente.
                       El broker guardará mensajes QoS 1/2 mientras el cliente
                       esté desconectado y los entregará al reconectar.
        
        Ejemplos:
            # API - múltiples instancias, sin persistencia
            MQTTService()  # → client_id: "brokerwiz-api-a1b2c3d4"
            
            # Worker con persistencia - ID fijo obligatorio
            MQTTService(client_id="worker-1", persistent=True)
            MQTTService(client_id="worker-hdi", persistent=True)
        """
        self._client: Optional[aiomqtt.Client] = None
        self._connected = False
        self._subscriptions: set[str] = set()
        self._persistent = persistent
        
        # Validar: persistencia requiere client_id fijo
        if persistent and not client_id:
            raise ValueError(
                "persistent=True requiere client_id fijo. "
                "Ejemplo: MQTTService(client_id='worker-1', persistent=True)"
            )
        
        # Generar client_id: fijo si se proporciona, aleatorio si no
        self._client_id = client_id or f"{settings.mqtt.MQTT_CLIENT_ID}-{uuid.uuid4().hex[:8]}"
    
    @property
    def client_id(self) -> str:
        return self._client_id
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    @property
    def persistent(self) -> bool:
        return self._persistent
    
    @property
    def topic_prefix(self) -> str:
        return settings.mqtt.MQTT_TOPIC_PREFIX
    
    def get_topic(self, aseguradora: str) -> str:
        """Genera topic para aseguradora: bots/queue/{aseguradora}"""
        return f"{self.topic_prefix}/queue/{aseguradora}"
    
    @property
    def wildcard_topic(self) -> str:
        """Topic wildcard para todas las aseguradoras: bots/queue/+"""
        return f"{self.topic_prefix}/queue/+"
    
    def get_shared_topic(self, topic: str, group: str = "workers") -> str:
        """
        Genera topic con shared subscription (MQTT 5).
        
        Shared subscriptions permiten que múltiples workers se suscriban
        al mismo topic, pero cada mensaje se entrega a UN SOLO worker
        del grupo (round-robin).
        
        Args:
            topic: Topic base (ej: "bots/queue/hdi" o "bots/queue/+")
            group: Nombre del grupo de workers (default: "workers")
        
        Returns:
            Topic con prefijo $share (ej: "$share/workers/bots/queue/hdi")
        
        Ejemplo:
            # Sin shared (todos reciben):
            bots/queue/hdi → Worker1, Worker2, Worker3 (todos)
            
            # Con shared (solo uno recibe):
            $share/workers/bots/queue/hdi → Worker2 (round-robin)
        """
        return f"$share/{group}/{topic}"
    
    @property
    def lwt_topic(self) -> str:
        """Topic para Last Will Testament"""
        return settings.mqtt.MQTT_LWT_TOPIC
    
    def _create_client(self, persistent_session: bool = False) -> aiomqtt.Client:
        """
        Crea instancia del cliente con configuración LWT.
        
        Args:
            persistent_session: Si True, usa clean_session=False para que el broker
                               guarde mensajes QoS 1/2 cuando el cliente está desconectado.
                               Los mensajes se entregarán cuando el cliente reconecte.
        
        Importante para recuperación ante caídas:
        - persistent_session=True + QoS 1/2 = mensajes guardados en broker
        - El client_id DEBE ser estable (no usar UUID) para sesiones persistentes
        """
        lwt_message = aiomqtt.Will(
            topic=self.lwt_topic,
            payload=json.dumps({
                "client_id": self._client_id,
                "status": "offline",
                "timestamp": datetime.now().isoformat()
            }),
            qos=settings.mqtt.MQTT_QOS,
            retain=True
        )
        
        return aiomqtt.Client(
            hostname=settings.mqtt.MQTT_HOST,
            port=settings.mqtt.MQTT_PORT,
            identifier=self._client_id,
            will=lwt_message,
            # clean_session=False permite recuperar mensajes perdidos durante desconexión
            clean_session=not persistent_session
        )
    
    async def connect(self) -> None:
        """
        Conectar al broker MQTT.
        
        Si self._persistent=True, usa clean_session=False para recuperar
        mensajes pendientes de sesiones anteriores.
        """
        if self._connected:
            return
        
        try:
            self._client = self._create_client(persistent_session=self._persistent)
            await self._client.__aenter__()
            self._connected = True
            
            # Publicar estado online
            await self._publish_status("online")
            logger.info(f"Conectado a MQTT: {settings.mqtt.MQTT_HOST}:{settings.mqtt.MQTT_PORT}")
            
        except aiomqtt.MqttError as e:
            logger.error(f"Error conectando a MQTT: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Desconectar del broker MQTT"""
        if not self._connected or not self._client:
            return
        
        try:
            await self._publish_status("offline")
            await self._client.__aexit__(None, None, None)
            self._connected = False
            self._subscriptions.clear()
            logger.info("Desconectado de MQTT")
            
        except aiomqtt.MqttError as e:
            logger.error(f"Error desconectando: {e}")
    
    async def __aenter__(self) -> "MQTTService":
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()
    
    async def publish_task(
        self,
        aseguradora: str,
        task_data: Dict[str, Any],
        retain: bool = False
    ) -> bool:
        """
        Publicar tarea en cola de aseguradora.
        
        Args:
            aseguradora: Nombre (ej: "hdi", "sura", "axa")
            task_data: Dict con job_id, payload, etc.
            retain: Retener mensaje en broker
        
        Returns:
            True si se publicó exitosamente
        """
        if not self._connected or not self._client:
            logger.error("No conectado a MQTT")
            return False
        
        try:
            # Agregar timestamp si no existe
            if "timestamp" not in task_data:
                task_data["timestamp"] = datetime.now().isoformat()
            
            topic = self.get_topic(aseguradora)
            payload = json.dumps(task_data, ensure_ascii=False)
            
            await self._client.publish(
                topic=topic,
                payload=payload,
                qos=settings.mqtt.MQTT_QOS,
                retain=retain
            )
            
            logger.info(f"Tarea publicada → {topic}: {task_data.get('job_id', '?')}")
            return True
            
        except aiomqtt.MqttError as e:
            logger.error(f"Error publicando tarea: {e}")
            return False
    
    async def subscribe(self, topic: str) -> bool:
        """Suscribirse a un topic específico"""
        if not self._connected or not self._client:
            logger.error("No conectado a MQTT")
            return False
        
        try:
            await self._client.subscribe(topic, qos=settings.mqtt.MQTT_QOS)
            self._subscriptions.add(topic)
            logger.info(f"Suscrito a: {topic}")
            return True
            
        except aiomqtt.MqttError as e:
            logger.error(f"Error suscribiendo a {topic}: {e}")
            return False
    
    async def subscribe_aseguradora(self, aseguradora: str) -> bool:
        """Suscribirse a cola de aseguradora específica"""
        return await self.subscribe(self.get_topic(aseguradora))
    
    async def subscribe_wildcard(self) -> bool:
        """Suscribirse a todas las aseguradoras (bots/queue/+)"""
        logger.info("Escuchando todas las aseguradoras")
        return await self.subscribe(self.wildcard_topic)
    
    async def subscribe_shared(
        self, 
        group: str = "workers",
        aseguradora: Optional[str] = None
    ) -> bool:
        """
        Permite que múltiples workers compartan la carga de una cola.
        Cada mensaje se entrega a UN SOLO worker del grupo (round-robin).
        
        Args:
            group: Nombre del grupo de workers (default: "workers").
                   Workers con el mismo grupo comparten mensajes.
            aseguradora: Si se especifica, escucha solo esa aseguradora.
                        Si es None, escucha todas (wildcard).
        
        Returns:
            True si se suscribió exitosamente
        
        Ejemplos:
            # Escuchar todas las aseguradoras (compartido)
            await mqtt.subscribe_shared()
            # → $share/workers/bots/queue/+
            
            # Escuchar solo HDI (compartido entre workers HDI)
            await mqtt.subscribe_shared(group="workers-hdi", aseguradora="hdi")
            # → $share/workers-hdi/bots/queue/hdi
            
            # Grupo separado para pruebas
            await mqtt.subscribe_shared(group="test-workers")
            # → $share/test-workers/bots/queue/+
        """
        if aseguradora:
            base_topic = self.get_topic(aseguradora)
        else:
            base_topic = self.wildcard_topic
        
        shared_topic = self.get_shared_topic(base_topic, group)
        logger.info(f"Suscripción compartida [{group}]: {shared_topic}")
        return await self.subscribe(shared_topic)
    
    async def messages(self) -> AsyncIterator[tuple[str, Dict[str, Any]]]:
        """
        Iterador asíncrono de mensajes recibidos.
        
        Yields:
            Tupla (topic, message_dict)
        
        Uso:
            async for topic, data in mqtt.messages():
                aseguradora = topic.split("/")[-1]
                await process_task(aseguradora, data)
        """
        if not self._client:
            raise RuntimeError("Cliente no conectado")
        
        async for message in self._client.messages:
            try:
                topic = str(message.topic)
                payload = message.payload.decode("utf-8")
                data = json.loads(payload)
                
                logger.debug(f"Mensaje recibido ← {topic}: {data.get('job_id', '?')}")
                yield topic, data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON inválido en mensaje: {e}")
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}")
    
    async def _publish_status(self, status: str) -> None:
        """Publicar estado del cliente (online/offline)"""
        if not self._client:
            return
        
        try:
            payload = json.dumps({
                "client_id": self._client_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            })
            
            await self._client.publish(
                topic=self.lwt_topic,
                payload=payload,
                qos=settings.mqtt.MQTT_QOS,
                retain=True
            )
        except Exception as e:
            logger.warning(f"Error publicando status {status}: {e}")

    async def ping(self, timeout: float = 3.0) -> bool:
        """
        Verificar conexión real con el broker MQTT.
        
        Intenta publicar un mensaje de heartbeat con timeout.
        Si el broker no responde o la conexión está rota, retorna False.
        
        Args:
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            True si el broker está accesible, False si no
        """
        if not self._client or not self._connected:
            return False
        
        try:
            # Intentar publicar un mensaje de heartbeat con timeout
            heartbeat_topic = f"{self.topic_prefix}/heartbeat"
            heartbeat_payload = json.dumps({
                "client_id": self._client_id,
                "timestamp": datetime.now().isoformat(),
                "type": "ping"
            })
            
            await asyncio.wait_for(
                self._client.publish(
                    topic=heartbeat_topic,
                    payload=heartbeat_payload,
                    qos=0  # QoS 0 para velocidad, no necesitamos confirmación
                ),
                timeout=timeout
            )
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout verificando conexión MQTT ({timeout}s)")
            self._connected = False
            return False
        except aiomqtt.MqttError as e:
            logger.warning(f"Error verificando conexión MQTT: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Error inesperado en ping MQTT: {e}")
            self._connected = False
            return False


# Singleton para FastAPI
_mqtt_instance: Optional[MQTTService] = None

# Client ID fijo para la API - evita sesiones huérfanas en el broker
API_CLIENT_ID = f"{settings.mqtt.MQTT_CLIENT_ID}-api"


def get_mqtt_service() -> MQTTService:
    """Obtener instancia singleton del servicio MQTT para la API."""
    global _mqtt_instance
    if _mqtt_instance is None:
        # Client ID fijo, sin sesión persistente (solo publica)
        _mqtt_instance = MQTTService(client_id=API_CLIENT_ID, persistent=False)
    return _mqtt_instance


@asynccontextmanager
async def mqtt_lifespan_manager():
    """
    Context manager para lifespan de FastAPI.
    
    Uso en main.py:
        from contextlib import asynccontextmanager
        from mosquitto.mqtt_service import mqtt_lifespan_manager, get_mqtt_service
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with mqtt_lifespan_manager():
                yield
        
        app = FastAPI(lifespan=lifespan)
    """
    mqtt = get_mqtt_service()
    await mqtt.connect()
    try:
        yield mqtt
    finally:
        await mqtt.disconnect()


async def get_mqtt_dependency() -> MQTTService:
    """
    Dependency injection para endpoints FastAPI.
    
    Uso:
        @app.post("/cotizaciones/{aseguradora}")
        async def crear_cotizacion(
            aseguradora: str,
            data: CotizacionRequest,
            mqtt: MQTTService = Depends(get_mqtt_dependency)
        ):
            await mqtt.publish_task(aseguradora, data.dict())
    """
    mqtt = get_mqtt_service()
    if not mqtt.connected:
        await mqtt.connect()
    return mqtt


@asynccontextmanager
async def mqtt_worker_context(
    handler: MessageHandler,
    topic: Optional[str] = None,
    group: str = "workers",
    use_shared: bool = True,
    reconnect_interval: float = 5.0
):
    """
    Context manager para workers que procesan mensajes.
    Incluye reconexión automática y shared subscriptions.
    
    Args:
        handler: Función async que procesa cada mensaje (topic, data)
        topic: Topic específico o None para wildcard
        group: Nombre del grupo para shared subscriptions (default: "workers")
        use_shared: Si True, usa shared subscriptions para evitar duplicados
        reconnect_interval: Segundos entre intentos de reconexión
    
    Uso:
        async def handle_task(topic: str, data: dict):
            aseguradora = topic.split("/")[-1]
            bot = get_bot(aseguradora)
            await bot.run(data["payload"])
        
        # Worker con shared subscription (recomendado)
        async with mqtt_worker_context(handle_task) as mqtt:
            pass
        
        # Worker para aseguradora específica
        async with mqtt_worker_context(
            handle_task, 
            topic="bots/queue/hdi",
            group="workers-hdi"
        ) as mqtt:
            pass
    
    Comportamiento con shared subscriptions:
    - Múltiples workers pueden correr simultáneamente
    - Cada tarea se entrega a UN SOLO worker (round-robin)
    - Worker ocupado procesando = broker pasa al siguiente worker
    - Procesamiento secuencial garantiza distribución justa
    """
    mqtt = MQTTService()
    
    while True:
        try:
            async with mqtt:
                # Suscribirse (shared o normal)
                if use_shared:
                    if topic:
                        # Topic específico con shared
                        shared_topic = mqtt.get_shared_topic(topic, group)
                        await mqtt.subscribe(shared_topic)
                    else:
                        # Wildcard con shared
                        await mqtt.subscribe_shared(group=group)
                else:
                    # Suscripción normal (todos reciben)
                    if topic:
                        await mqtt.subscribe(topic)
                    else:
                        await mqtt.subscribe_wildcard()
                
                # Procesar mensajes
                async for msg_topic, data in mqtt.messages():
                    try:
                        await handler(msg_topic, data)
                    except Exception as e:
                        logger.error(f"Error en handler: {e}")
                
        except aiomqtt.MqttError as e:
            logger.warning(f"Conexión MQTT perdida: {e}. Reconectando en {reconnect_interval}s...")
            await asyncio.sleep(reconnect_interval)
        except asyncio.CancelledError:
            logger.info("Worker MQTT cancelado")
            break
    
    yield mqtt

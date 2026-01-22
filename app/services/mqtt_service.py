"""
MQTT Service - Wrapper para cliente MQTT de Mosquitto
Maneja publicacion y suscripcion a topics de tareas
"""

import ssl
import time
import json
import logging
from datetime import datetime
from typing import Callable, Dict, Any, Optional

import paho.mqtt.client as mqtt

from config.settings import settings
from config.constants import MQTTTopics, Aseguradora

logger = logging.getLogger(__name__)


class MQTTService:
    """
    Servicio para comunicacion con MQTT Mosquitto
    
    Uso:
    ----
    # Inicializar
    mqtt_service = MQTTService()
    mqtt_service.connect()
    mqtt_service.loop_start()  # non-blocking
    
    # Publicar tarea para HDI
    mqtt_service.publish_task(
        aseguradora="hdi",
        task_data={"job_id": "uuid-123", "payload": {...}}
    )
    
    # Suscribirse a cola de una aseguradora específica
    def on_hdi_message(topic, message):
        print(f"Mensaje para HDI: {message}")
    
    mqtt_service.subscribe_aseguradora("hdi", callback=on_hdi_message)
    
    # Suscribirse a cualquier aseguradora (worker genérico)
    mqtt_service.subscribe_wildcard(callback=on_any_aseguradora)
    """
    
    def __init__(self):
        """Inicializar cliente MQTT"""
        self.client = mqtt.Client(
            client_id=settings.mqtt.MQTT_CLIENT_ID,
            protocol=mqtt.MQTTv311,
            clean_session=settings.mqtt.MQTT_CLEAN_SESSION
        )
        
        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        
        # State
        self.connected = False
        self.message_callbacks: Dict[str, Callable] = {}
        self.reconnect_count = 0
        self.last_reconnect_delay = settings.mqtt.MQTT_RECONNECT_MIN_DELAY
        
    def connect(self) -> bool:
        """
        Conectar a broker MQTT
        
        Returns:
            True si conexion exitosa, False si error
        """
        try:
            # TLS/SSL
            if settings.mqtt.MQTT_USE_TLS:
                self._setup_tls()
            
            # Last Will and Testament (LWT)
            if settings.mqtt.MQTT_ENABLE_LWT:
                self._setup_lwt()
            
            # Auto-reconnect
            if settings.mqtt.MQTT_AUTO_RECONNECT:
                self.client.reconnect_delay_set(
                    min_delay=settings.mqtt.MQTT_RECONNECT_MIN_DELAY,
                    max_delay=settings.mqtt.MQTT_RECONNECT_MAX_DELAY
                )
            
            # Credenciales
            if settings.mqtt.MQTT_USERNAME:
                self.client.username_pw_set(
                    settings.mqtt.MQTT_USERNAME,
                    settings.mqtt.MQTT_PASSWORD
                )
            
            # Conectar
            logger.info(
                f"Conectando a MQTT: {settings.mqtt.MQTT_HOST}:{settings.mqtt.MQTT_PORT} "
            )
            
            self.client.connect(
                host=settings.mqtt.MQTT_HOST,
                port=settings.mqtt.MQTT_PORT,
                keepalive=settings.mqtt.MQTT_KEEPALIVE
            )
            
            logger.info("Conectado a broker MQTT")
            return True
            
        except Exception as e:
            logger.error(f"Error al conectar a MQTT: {e}")
            return False
    
    def disconnect(self) -> None:
        """Desconectar de broker MQTT"""
        try:
            self.client.disconnect()
            logger.info("Desconectado de broker MQTT")
        except Exception as e:
            logger.error(f"Error al desconectar de MQTT: {e}")
    
    def publish_task(
        self, 
        aseguradora: str, 
        task_data: Dict[str, Any],
        retain: bool = False
    ) -> bool:
        """
        Publicar tarea en cola MQTT
        
        Args:
            aseguradora: Nombre de aseguradora (ej: "hdi", "seguros_monterrey")
            task_data: Dict con {"job_id", "timestamp", "payload", ...}
            retain: Si True, guardar mensaje en broker (default: False, ephemeral)
        
        Ejemplo:
            mqtt_service.publish_task(
                aseguradora="hdi",
                task_data={"job_id": "abc123", "payload": {...}}
            )
        
        Returns:
            True si publish exitoso
        """
        try:
            # Agregar timestamp si no existe
            if "timestamp" not in task_data:
                task_data["timestamp"] = datetime.now().isoformat()
            
            # Topic per-aseguradora
            topic = self.get_aseguradora_topic(aseguradora)
            
            # Convertir a JSON
            message = json.dumps(task_data, ensure_ascii=False)
            
            # Publicar
            result = self.client.publish(
                topic=topic,
                payload=message,
                qos=settings.mqtt.MQTT_QOS,
                retain=retain
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Tarea publicada en {topic}: {task_data.get('job_id')}")
                return True
            else:
                logger.error(f"Error publicando: rc={result.rc}")
                return False
        
        except Exception as e:
            logger.error(f"Error en publish_task: {e}")
            return False
    
    def subscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """
        Suscribirse a un topic MQTT (puede incluir wildcards)
        
        Args:
            topic: Topic a suscribirse, ej:
                   - "bots/queue/hdi" (specific)
                   - "bots/queue/+" (cualquier aseguradora)
                   - "bots/queue/#" (cualquier cosa bajo queue)
            callback: Función callback(topic, message_dict)
        
        Returns:
            True si suscripcion exitosa
        """
        try:
            # Guardar callback
            if callback:
                self.message_callbacks[topic] = callback
            
            # Suscribirse
            result = self.client.subscribe(topic, qos=settings.mqtt.MQTT_QOS)
            
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Suscrito a topic: {topic}")
                return True
            else:
                logger.error(f"Error en subscripcion: rc={result[0]}")
                return False
        
        except Exception as e:
            logger.error(f"Error en subscribe: {e}")
            return False
    
    def subscribe_aseguradora(
        self, 
        aseguradora: str, 
        callback: Optional[Callable] = None
    ) -> bool:
        """
        Suscribirse a cola de aseguradora específica
        
        Args:
            aseguradora: Nombre de aseguradora (ej: "hdi")
            callback: Función callback(topic, message_dict)
        
        Ejemplo:
            mqtt_service.subscribe_aseguradora(
                "hdi",
                callback=handle_hdi_tasks
            )
        """
        topic = self.get_aseguradora_topic(aseguradora)
        return self.subscribe(topic, callback)
    
    def subscribe_wildcard(self, callback: Optional[Callable] = None) -> bool:
        """
        Suscribirse a CUALQUIER aseguradora (worker genérico)
        
        Usa wildcard de un nivel: bots/queue/+
        
        Args:
            callback: Función callback(topic, message_dict)
        
        Ejemplo:
            mqtt_service.subscribe_wildcard(
                callback=handle_any_aseguradora
            )
        """
        topic = settings.mqtt.MQTT_QUEUE_WILDCARD_SINGLE
        logger.info("Escuchando todas las aseguradoras")
        return self.subscribe(topic, callback)
    
    def get_aseguradora_topic(self, aseguradora: str) -> str:
        """
        Obtener topic para aseguradora específica
        
        Ejemplo: aseguradora="hdi" → "bots/queue/hdi"
        """
        return f"{settings.mqtt.MQTT_TOPIC_PREFIX}/queue/{aseguradora}"
    
    def loop_start(self) -> None:
        """Iniciar loop de eventos MQTT (non-blocking)"""
        try:
            self.client.loop_start()
            logger.info("Loop MQTT iniciado (background)")
        except Exception as e:
            logger.error(f"Error iniciando loop: {e}")
    
    def loop_stop(self) -> None:
        """Detener loop de eventos MQTT"""
        try:
            self.client.loop_stop()
            logger.info("Loop MQTT detenido")
        except Exception as e:
            logger.error(f"Error deteniendo loop: {e}")
    
    def loop_forever(self) -> None:
        """Bloquear en loop MQTT (para workers principal)"""
        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Loop MQTT interrumpido por usuario")
        except Exception as e:
            logger.error(f"Error en loop_forever: {e}")

    
    def _setup_tls(self) -> None:
        """Configurar TLS/SSL para conexion cifrada"""
        try:
            # Validar certificados del servidor
            tls_version = getattr(ssl, f"PROTOCOL_{settings.mqtt.MQTT_TLS_VERSION.upper()}", ssl.PROTOCOL_TLSv1_2)
            
            self.client.tls_set(
                ca_certs=settings.mqtt.MQTT_CA_CERTS,          # CA para validar servidor
                certfile=settings.mqtt.MQTT_CERTFILE,          # Cert cliente (mutual auth)
                keyfile=settings.mqtt.MQTT_KEYFILE,            # Key cliente (mutual auth)
                cert_reqs=ssl.CERT_REQUIRED if not settings.mqtt.MQTT_TLS_INSECURE else ssl.CERT_NONE,
                tls_version=tls_version,
                ciphers=None
            )
            
            # NO verificar hostname (solo para dev, NUNCA en produccion)
            if settings.mqtt.MQTT_TLS_INSECURE:
                self.client.tls_insecure_set(True)
                logger.warning("TLS INSECURE: No verificando certificado del servidor (SOLO PARA DEV)")
            else:
                logger.info("TLS configurado con validacion de certificado del servidor")
        
        except Exception as e:
            logger.error(f"Error configurando TLS: {e}")
            raise
    
    def _setup_lwt(self) -> None:
        """
        Configurar Last Will and Testament (LWT)
        
        Publica mensaje de estado offline cuando cliente se desconecta inesperadamente
        """
        try:
            lwt_topic = settings.mqtt.MQTT_STATUS_TOPIC
            lwt_payload = json.dumps({
                "client_id": settings.mqtt.MQTT_CLIENT_ID,
                "status": "offline",
                "timestamp": datetime.now().isoformat()
            })
            
            self.client.will_set(
                topic=lwt_topic,
                payload=lwt_payload,
                qos=settings.mqtt.MQTT_QOS,
                retain=True  # Guardar mensaje de LWT para nuevos subscribers
            )
            
            logger.info(f"LWT configurado: {lwt_topic} → offline")
        
        except Exception as e:
            logger.error(f"Error configurando LWT: {e}")
    
    def _on_connect(self, client, userdata, connect_flags, reason_code, properties=None):
        """
        Callback cuando se conecta al broker
        
        reason_code:
          0 = Connection successful
          1-5 = Various connection failures
        """
        if reason_code == 0:
            self.connected = True
            self.reconnect_count = 0
            logger.info("Conectado a broker MQTT")
            
            # Publicar estado online (si LWT estaba offline)
            if settings.mqtt.MQTT_ENABLE_LWT:
                self._publish_online_status()
        else:
            logger.error(f"Error de conexion: {reason_code}")
    
    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        """
        Callback cuando se desconecta del broker
        
        Si MQTT_AUTO_RECONNECT=true, el cliente reconectará automáticamente
        """
        self.connected = False
        self.reconnect_count += 1
        logger.warning(
            f"Desconectado de broker: reason_code={reason_code}, "
            f"reconnect_attempt={self.reconnect_count}"
        )
    
    def _on_message(self, client, userdata, msg):
        """Callback cuando se recibe un mensaje"""
        try:
            topic = msg.topic
            
            # Decodificar payload
            payload = msg.payload.decode('utf-8')
            message_dict = json.loads(payload)
            
            logger.debug(f"Mensaje recibido en {topic}: {message_dict.get('job_id', '???')}")
            
            # Ejecutar callback si existe
            callback = self.message_callbacks.get(topic)
            if callback:
                callback(topic, message_dict)
            else:
                # Si es un wildcard, buscar callback del wildcard
                wildcard_topics = [k for k in self.message_callbacks.keys() if '+' in k or '#' in k]
                for wildcard_topic in wildcard_topics:
                    if self._matches_wildcard(topic, wildcard_topic):
                        self.message_callbacks[wildcard_topic](topic, message_dict)
                        return
                
                logger.warning(f"No hay callback registrado para {topic}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando JSON: {e}")
        except Exception as e:
            logger.error(f"Error en _on_message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback cuando se completa publish"""
        logger.debug(f"Mensaje publicado (mid={mid})")
    
    def _publish_online_status(self) -> None:
        """Publicar estado online cuando se conecta"""
        try:
            status_topic = settings.mqtt.MQTT_STATUS_TOPIC
            online_payload = json.dumps({
                "client_id": settings.mqtt.MQTT_CLIENT_ID,
                "status": "online",
                "timestamp": datetime.now().isoformat()
            })
            
            self.client.publish(
                topic=status_topic,
                payload=online_payload,
                qos=settings.mqtt.MQTT_QOS,
                retain=True
            )
        except Exception as e:
            logger.error(f"Error publicando estado online: {e}")
    
    @staticmethod
    def _matches_wildcard(topic: str, wildcard: str) -> bool:
        """Verificar si topic coincide con wildcard pattern"""
        # bots/queue/hdi coincide con bots/queue/+ (un nivel)
        # bots/queue/hdi/extra coincide con bots/queue/# (multiples niveles)
        
        if '#' in wildcard:
            # Multilinivel: bots/queue/# coincide con bots/queue/* (anything under)
            base = wildcard.replace('/#', '').replace('#', '')
            return topic.startswith(base)
        elif '+' in wildcard:
            # Un nivel: bots/queue/+ coincide con bots/queue/hdi
            parts_wildcard = wildcard.split('/')
            parts_topic = topic.split('/')
            
            if len(parts_wildcard) != len(parts_topic):
                return False
            
            for w, t in zip(parts_wildcard, parts_topic):
                if w != '+' and w != t:
                    return False
            return True
        else:
            # Exact match
            return topic == wildcard


_mqtt_service_instance: Optional[MQTTService] = None


def get_mqtt_service() -> MQTTService:
    """
    Obtener instancia singleton de MQTTService
    
    Uso en FastAPI:
        from app.services.mqtt_service import get_mqtt_service
        
        mqtt = get_mqtt_service()
        mqtt.publish_task(aseguradora="hdi", task_data={...})
    """
    global _mqtt_service_instance
    if _mqtt_service_instance is None:
        _mqtt_service_instance = MQTTService()
    return _mqtt_service_instance


def mqtt_service_factory():
    """
    Factory para dependency injection en FastAPI
    
    Uso:
        from fastapi import Depends
        from app.services.mqtt_service import mqtt_service_factory
        
        @app.post("/cotizaciones/hdi")
        async def endpoint(mqtt = Depends(mqtt_service_factory)):
            mqtt.publish_task(aseguradora="hdi", task_data={...})
    """
    return get_mqtt_service()

"""
Worker MQTT para procesar tareas de cotización.

Escucha mensajes en bots/queue/+ y ejecuta el bot correspondiente.
Usa ResourceManager para limitar concurrencia y verificar recursos.

Uso:
    python -m workers.mqtt_worker --id worker-1
    
    # Solo una aseguradora específica:
    python -m workers.mqtt_worker --id worker-hdi --aseguradora hdi
"""

import asyncio
import argparse
import signal
from typing import Optional, Type

from config.settings import settings
from config.logging_config import setup_logging
from mosquitto.mqtt_service import configure_event_loop, MQTTService
from workers.resource_manager import ResourceManager, ResourceUnavailableError
from workers.bots import BaseBot
from workers.bots.hdi_bot import HDIBot

# Configurar logging al inicio
logger = setup_logging("worker")


# === Registro de Bots ===
# Mapea nombre de aseguradora → clase del bot
# Los bots se registran aquí conforme se implementan

BOT_REGISTRY: dict[str, Type[BaseBot]] = {
    "hdi": HDIBot,
    # "sura": SURABot,
    # "axa": AXABot,
    # etc.
}


def get_bot_class(aseguradora: str) -> Optional[Type[BaseBot]]:
    """
    Obtener clase del bot para una aseguradora.
    
    Args:
        aseguradora: Nombre de la aseguradora (lowercase)
    
    Returns:
        Clase del bot, o None si no está implementado
    """
    return BOT_REGISTRY.get(aseguradora.lower())


def list_available_bots() -> list[str]:
    """Listar aseguradoras con bots implementados."""
    return list(BOT_REGISTRY.keys())


# === Handler de tareas ===

async def handle_task(
    topic: str,
    data: dict,
    resource_manager: ResourceManager
) -> None:
    """
    Procesar tarea recibida de MQTT.
    
    Args:
        topic: Topic MQTT (ej: "bots/queue/hdi")
        data: Datos del mensaje {"job_id", "payload", "timestamp"}
        resource_manager: Gestor de recursos para control de concurrencia
    """
    # Extraer aseguradora del topic
    aseguradora = topic.split("/")[-1]
    job_id = data.get("job_id", "unknown")
    payload = data.get("payload", {})
    
    logger.info(f"[{aseguradora.upper()}] Recibido job: {job_id}")
    
    # Verificar que existe bot para esta aseguradora
    bot_class = get_bot_class(aseguradora)
    if not bot_class:
        logger.warning(
            f"[{aseguradora.upper()}] Bot no implementado. "
            f"Disponibles: {list_available_bots() or 'ninguno'}"
        )
        return
    
    # Adquirir slot de recursos y ejecutar bot
    try:
        async with resource_manager.acquire_slot(aseguradora, job_id):
            bot = bot_class(job_id=job_id, payload=payload)
            
            try:
                async with bot:
                    success = await bot.run()
                    
                if success:
                    logger.info(f"[{aseguradora.upper()}] Job {job_id} completado exitosamente")
                else:
                    logger.warning(f"[{aseguradora.upper()}] Job {job_id} completado con errores")
                    
            except Exception as e:
                logger.error(f"[{aseguradora.upper()}] Error en job {job_id}: {e}")

                # Reportar error a la API solo en produccion
                if settings.ENVIRONMENT == "production":
                    await bot.report_error(
                        error_code="BOT_EXCEPTION",
                        message=str(e),
                        severity="CRITICAL"
                    )
                
    except ResourceUnavailableError as e:
        logger.warning(
            f"[{aseguradora.upper()}] Job {job_id} rechazado: {e}. "
            "El mensaje será reprocesado al reconectar."
        )
        # Al no hacer ACK, el mensaje se reintentará
        raise


# === Worker principal ===

async def run_worker(
    client_id: str,
    aseguradora: Optional[str] = None,
    persistent: bool = True
) -> None:
    """
    Ejecutar worker MQTT.
    
    Args:
        client_id: ID único del worker (ej: "worker-1", "worker-hdi")
        aseguradora: Si se especifica, solo escucha esa aseguradora.
                    Si es None, escucha todas (wildcard).
        persistent: Si True, usa sesiones persistentes para recuperar
                   mensajes pendientes tras reinicio.
    """
    # Crear gestor de recursos
    resource_manager = ResourceManager()
    
    # Crear cliente MQTT
    mqtt = MQTTService(client_id=client_id, persistent=persistent)
    topic = mqtt.get_topic(aseguradora) if aseguradora else None
    
    scope = aseguradora.upper() if aseguradora else "TODAS"
    logger.info(
        f"Worker [{client_id}] iniciado\n"
        f"  Aseguradoras: {scope}\n"
        f"  Persistente: {persistent}\n"
        f"  Max concurrent: {resource_manager.max_concurrent}\n"
        f"  Bots disponibles: {list_available_bots() or 'ninguno (modo test)'}"
    )
    
    reconnect_interval = 5.0
    active_tasks: set[asyncio.Task] = set()
    
    while True:
        try:
            async with mqtt:
                # Suscribirse con shared subscription (load balancing entre workers)
                if topic:
                    shared_topic = mqtt.get_shared_topic(topic)
                    await mqtt.subscribe(shared_topic)
                else:
                    shared_topic = mqtt.get_shared_topic(mqtt.wildcard_topic)
                    await mqtt.subscribe(shared_topic)
                
                logger.info("Worker listo. Esperando tareas...")
                
                # Procesar mensajes en paralelo
                async for msg_topic, data in mqtt.messages():
                    # Limpiar tareas completadas
                    done_tasks = {t for t in active_tasks if t.done()}
                    active_tasks -= done_tasks
                    
                    # Crear tarea asíncrona
                    task = asyncio.create_task(
                        handle_task(msg_topic, data, resource_manager)
                    )
                    active_tasks.add(task)
                    
                    # Callback para manejar excepciones sin bloquear
                    def task_done_callback(t: asyncio.Task):
                        try:
                            exc = t.exception()
                            if exc and not isinstance(exc, ResourceUnavailableError):
                                logger.error(f"Error inesperado en tarea: {exc}")
                        except asyncio.CancelledError:
                            pass
                    
                    task.add_done_callback(task_done_callback)
                
        except asyncio.CancelledError:
            logger.info("Worker cancelado. Esperando tareas activas...")
            # Esperar que terminen las tareas en curso
            if active_tasks:
                await asyncio.gather(*active_tasks, return_exceptions=True)
            break
            
        except Exception as e:
            logger.warning(
                f"Conexión MQTT perdida: {e}. "
                f"Reconectando en {reconnect_interval}s..."
            )
            await asyncio.sleep(reconnect_interval)
    
    # Log final de estadísticas
    stats = resource_manager.get_system_stats()
    logger.info(
        f"Worker [{client_id}] terminado. "
        f"Bots activos al cerrar: {stats['active_bots']}"
    )


# === Entry point ===

def main():
    """Entry point del worker."""
    parser = argparse.ArgumentParser(
        description="Worker MQTT para bots de cotización",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python -m workers.mqtt_worker --id worker-1
  python -m workers.mqtt_worker --id worker-hdi -a hdi
  python -m workers.mqtt_worker --id worker-1 --no-persistent
        """
    )
    parser.add_argument(
        "--id",
        type=str,
        required=True,
        help="ID único del worker (ej: worker-1, worker-hdi)"
    )
    parser.add_argument(
        "--aseguradora", "-a",
        type=str,
        default=None,
        help="Aseguradora específica (hdi, sura, axa). Sin especificar = todas."
    )
    parser.add_argument(
        "--no-persistent",
        action="store_true",
        help="Deshabilitar sesiones persistentes (no recomendado en producción)"
    )
    args = parser.parse_args()
    
    # Configurar event loop para compatibilidad Windows/Linux
    configure_event_loop()
    
    # Crear event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Manejar señales de terminación
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(
                sig, 
                lambda: asyncio.create_task(shutdown(loop))
            )
        except NotImplementedError:
            # Windows no soporta add_signal_handler
            signal.signal(sig, lambda s, f: loop.call_soon_threadsafe(loop.stop))
    
    try:
        loop.run_until_complete(run_worker(
            client_id=args.id,
            aseguradora=args.aseguradora,
            persistent=not args.no_persistent
        ))
    except KeyboardInterrupt:
        logger.info("Interrumpido por usuario")
    finally:
        loop.close()
        logger.info("Worker terminado")


async def shutdown(loop: asyncio.AbstractEventLoop) -> None:
    """Shutdown graceful del worker."""
    logger.info("Recibida señal de terminación...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


if __name__ == "__main__":
    main()

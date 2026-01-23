"""
Worker MQTT para procesar tareas de cotización.

Escucha mensajes en bots/queue/+ y ejecuta el bot correspondiente.
Funciona en Windows (desarrollo) y Linux (producción).

Uso:
    python -m workers.mqtt_worker
    
    # Solo una aseguradora específica:
    python -m workers.mqtt_worker --aseguradora hdi
"""

import asyncio
import argparse
import logging
import signal
from typing import Optional

from mosquitto.mqtt_service import (
    configure_event_loop,
    MQTTService,
    mqtt_worker_context,
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def handle_task(topic: str, data: dict) -> None:
    """
    Procesar tarea recibida de MQTT.
    
    Args:
        topic: Topic MQTT (ej: "bots/queue/hdi")
        data: Datos del mensaje {"job_id", "payload", "timestamp"}
    """
    # Extraer aseguradora del topic
    aseguradora = topic.split("/")[-1]
    job_id = data.get("job_id", "unknown")
    payload = data.get("payload", {})
    
    logger.info(f"[{aseguradora.upper()}] Procesando job: {job_id}")
    
    try:
        # TODO: Importar y ejecutar el bot correspondiente
        # from workers.bots import get_bot
        # bot = get_bot(aseguradora)
        # result = await asyncio.to_thread(bot.run, payload)
        
        # Placeholder - simula procesamiento
        await asyncio.sleep(1)
        logger.info(f"[{aseguradora.upper()}] Job {job_id} completado")
        
    except Exception as e:
        logger.error(f"[{aseguradora.upper()}] Error en job {job_id}: {e}")
        raise


async def run_worker(aseguradora: Optional[str] = None) -> None:
    """
    Ejecutar worker MQTT.
    
    Args:
        aseguradora: Si se especifica, solo escucha esa aseguradora.
                    Si es None, escucha todas (wildcard).
    """
    mqtt = MQTTService()
    topic = mqtt.get_topic(aseguradora) if aseguradora else None
    
    scope = aseguradora.upper() if aseguradora else "TODAS"
    logger.info(f"Iniciando worker MQTT - Aseguradoras: {scope}")
    
    reconnect_interval = 5.0
    
    while True:
        try:
            async with mqtt:
                # Suscribirse
                if topic:
                    await mqtt.subscribe(topic)
                else:
                    await mqtt.subscribe_wildcard()
                
                logger.info("Worker listo. Esperando tareas...")
                
                # Procesar mensajes
                async for msg_topic, data in mqtt.messages():
                    try:
                        await handle_task(msg_topic, data)
                    except Exception as e:
                        logger.error(f"Error procesando tarea: {e}")
                        # Continúa con el siguiente mensaje
                
        except asyncio.CancelledError:
            logger.info("Worker cancelado. Cerrando...")
            break
            
        except Exception as e:
            logger.warning(
                f"Conexión MQTT perdida: {e}. "
                f"Reconectando en {reconnect_interval}s..."
            )
            await asyncio.sleep(reconnect_interval)


def main():
    """Entry point del worker."""
    parser = argparse.ArgumentParser(description="Worker MQTT para bots de cotización")
    parser.add_argument(
        "--aseguradora", "-a",
        type=str,
        default=None,
        help="Aseguradora específica (hdi, sura, axa, etc). Si no se especifica, escucha todas."
    )
    args = parser.parse_args()
    
    # Configurar event loop para compatibilidad Windows/Linux
    configure_event_loop()
    
    # Manejar señales de terminación
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Graceful shutdown en SIGTERM/SIGINT
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(loop)))
        except NotImplementedError:
            # Windows no soporta add_signal_handler, usar alternativa
            signal.signal(sig, lambda s, f: loop.call_soon_threadsafe(loop.stop))
    
    try:
        loop.run_until_complete(run_worker(args.aseguradora))
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

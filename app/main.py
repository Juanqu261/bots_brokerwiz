"""
BrokerWiz API - Orquestador de Bots de Cotización

API REST que recibe solicitudes de cotización y las encola en MQTT
para ser procesadas por workers (bots de Selenium).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from config.logging_config import setup_logging
from mosquitto.mqtt_service import (
    configure_event_loop,
    mqtt_lifespan_manager,
    get_mqtt_service
)

# Configurar event loop ANTES de cualquier operación async
configure_event_loop()

# Configurar logging
setup_logging(service_name="api")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager de FastAPI.
    
    - Startup: Conecta el cliente MQTT singleton y DLQ manager
    - Shutdown: Desconecta limpiamente
    """
    logger.info("Iniciando BrokerWiz API...")
    
    # Conectar MQTT
    async with mqtt_lifespan_manager():
        mqtt = get_mqtt_service()
        logger.info(f"MQTT conectado: {mqtt.client_id}")
        
        # Iniciar DLQ manager
        from app.services.dlq_manager import get_dlq_manager
        dlq_manager = get_dlq_manager()
        await dlq_manager.start()
        logger.info("DLQ manager iniciado")
        
        yield  # La aplicación corre aquí
        
        # Detener DLQ manager
        await dlq_manager.stop()
        logger.info("DLQ manager detenido")
        
    logger.info("BrokerWiz API detenida")


# Crear aplicación
app = FastAPI(
    title="BrokerWiz API",
    description="""
    ## Orquestador de Bots de Cotización
    
    API para encolar tareas de cotización que serán procesadas por bots 
    de Selenium conectados vía MQTT.
    
    ### Autenticación
    
    Todos los endpoints (excepto `/health`) requieren Bearer token:
    
    ```
    Authorization: Bearer <API_KEY>
    ```
    
    ### Flujo
    
    1. Cliente envía `POST /api/{aseguradora}/cotizar` con payload
    2. API encola mensaje en topic MQTT `bots/queue/{aseguradora}`
    3. Worker disponible recibe la tarea y ejecuta el bot
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.CORS_ORIGINS_LIST,
    allow_origin_regex=r"^http://localhost(:\d+)?$",  # Permite localhost con cualquier puerto
    allow_credentials=settings.security.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.security.CORS_ALLOW_METHODS_LIST,
    allow_headers=["*"] if settings.security.CORS_ALLOW_HEADERS == "*" else settings.security.CORS_ALLOW_HEADERS.split(","),
)


# Registrar routers
from app.routes import health, cotizaciones, logs, metrics, dlq

app.include_router(health.router)
app.include_router(cotizaciones.router, prefix="/api")
app.include_router(logs.router)
app.include_router(metrics.router)
app.include_router(dlq.router)

# Entry point para desarrollo
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api.API_HOST,
        port=settings.api.API_PORT,
        reload=settings.general.DEBUG,
        reload_excludes=["logs", "*.log", "logs/**"],  # Excluir carpeta logs del hot-reload
        log_level=settings.general.LOG_LEVEL.lower()
    )

# Plan de Implementacion: Servidor de Bots Selenium con API y Queue

## Vision General

Crear un servidor modular de automatizacion con bots Selenium orchestrados por una API REST + cola de tareas (RQ), todo containerizado para fácil escalabilidad. La arquitectura separa API y workers en procesos independientes, permitiendo crecer desde 2 bots concurrentes a 10+ sin cambios de codigo. **Los PDFs generados por los bots se envian directamente a un endpoint de la app web existente para almacenamiento.**

---

## 1. Stack Tecnico

### Lenguaje y Runtime
- **Python 3.12.x**

### Cola de Tareas
- **RQ (Redis Queue)** como gestor de tareas

### Orquestacion de Procesos
- **Multiprocessing + FastAPI**
- API en proceso principal (FastAPI)
- N workers en procesos separados (RQ workers)
- Resilencia: Si un worker falla, no afecta API

### Containerizacion
- **Single-container MVP**: API + Redis + 2 workers en scripts/start_all.py
- **Multi-container Produccion** (future): Docker Compose con replicas de workers (3+ containers independientes)
- Base: Python 3.12-slim + Chromium + ChromeDriver

---

## 2. Arquitectura de la Solucion

### Componentes Principales

```
┌─────────────────────────────────────────────────────────┐
│                  Docker Container                       │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   FastAPI    │  │    Redis     │  │  RQ Workers  │   │
│  │   (API)      │  │   (Queue)    │  │  (Selenium)  │   │
│  │              │  │              │  │              │   │
│  │ Port 8000    │  │ Port 6379    │  │ Processes 2+ │   │
│  │              │  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│         ↑                                      ↑        │
│         └──────────────────────────────────────┘        │
│                    Job Queue                            │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │    /app/storage/temp (Temporal PDF Memory)       │   │
│  │    (Limpiar despues de envio exitoso)            │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         ↑                                           │
         │ POST /api/{aseguradora}/cotizar           │
         │ GET /api/jobs/{id}/status                 │ PDFs enviados a
         │                                           │ app web via
      (App Web)                       <--------------│ /archivos-cotizacion

```

### Flujo de Ejecucion

1. **App Web** → POST `/api/hdi/cotizar` con payload de cotizacion
2. **FastAPI** → Valida, mapea payload, encola job en Redis
3. **RQ** → Devuelve `job_id` inmediatamente
4. **Worker** → Obtiene job de cola, ejecuta bot Selenium HDI
5. **Bot** → Login → Navega → Extrae datos → Genera PDF (en memoria)
6. **PDFs** → Se genera en `/tmp` o BytesIO
7. **Envio** → Bot llama `POST /archivos-cotizacion` de app web con PDF
8. **App Web** → Recibe y almacena PDF (responsabilidad de app web)
9. **Cleanup** → Bot elimina PDF temp despues de envio exitoso
10. **App Web** → GET `/api/jobs/{job_id}/status` (polling) o webhook para saber que está listo

---

## 3. Estructura de Proyecto

```
bots_brokerWiz/
├── app/                                 # API FastAPI
│   ├── __init__.py
│   ├── main.py                          # App principal, startup/shutdown
│   ├── config.py                        # Alias para settings
│   ├── dependencies.py                  # Inyeccion de dependencias
│   ├── models/
│   │   ├── __init__.py
│   │   ├── quote.py                     # Pydantic: QuoteRequest, QuoteResponse
│   │   ├── job.py                       # Pydantic: JobStatus, JobResult
│   │   └── responses.py                 # Response envelopes
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── cotizaciones.py              # POST /api/{aseguradora}/cotizar
│   │   ├── jobs.py                      # GET /api/jobs/{id}, status, cancel
│   │   ├── webhooks.py                  # Notificaciones (opcional)
│   │   └── health.py                    # GET /health (liveness)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── redis_service.py             # RedisClient wrapper
│   │   ├── email_service.py             # Notificaciones (opcional)
│   │   └── asegurador_mapper.py         # Mapeos de payload por aseguradora
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py                      # Validacion API Key
│       └── logging.py                   # Request/response logging
│
├── workers/                             # Procesos RQ + Bots Selenium
│   ├── __init__.py
│   ├── start_rq_worker.py               # Entry point: python -m rq worker
│   ├── bots/
│   │   ├── __init__.py
│   │   ├── base_bot.py                  # Clase base (Template Method)
│   │   ├── hdi_bot.py                   # Bot HDI (subclase)
│   │   ├── runt_bot.py                  # Bot RUNT
│   │   ├── axa_bot.py                   # Bot AXA
│   │   ├── sura_bot.py                  # Bot SURA
│   │   ├── solidaria_bot.py             # Bot SOLIDARIA
│   │   ├── equidad_bot.py               # Bot EQUIDAD
│   │   ├── mundial_bot.py               # Bot MUNDIAL
│   │   ├── allianz_bot.py               # Bot ALLIANZ
│   │   ├── bolivar_bot.py               # Bot BOLiVAR
│   │   ├── sbs_bot.py                   # Bot SBS
│   │   ├── payload_mappers.py           # Mapeos por aseguradora
│   │   └── pdf_uploader.py              # Servicio para enviar PDFs a app web
│   ├── tasks.py                         # Task functions (execute_bot_with_retry)
│   └── utils/
│       ├── __init__.py
│       ├── selenium_utils.py            # Helpers Selenium (waits, clicks)
│       ├── screenshot_utils.py          # Screenshots para debugging
│       └── retry_utils.py               # Backoff exponencial
│
├── config/
│   ├── __init__.py
│   ├── settings.py                      # Pydantic Settings (env vars)
│   ├── logging_config.py                # Setup logging (console + file)
│   └── redis_config.py                  # Configuracion de Redis
│
├── storage/                             # Volumen Docker (gitignored)
│   └── screenshots/                     # Debug screenshots solamente
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Fixtures pytest
│   ├── test_api.py                      # Test endpoints
│   ├── test_bots/
│   │   ├── __init__.py
│   │   ├── test_hdi_bot.py              # Test HDI bot
│   │   ├── test_base_bot.py             # Test clase base
│   │   └── test_payload_mappers.py      # Test mapeos
│   └── test_integration.py              # End-to-end
│
├── scripts/
│   ├── __init__.py
│   ├── start_all.py                     # Inicia API + Redis + Workers
│   ├── start_api.py                     # Solo API
│   ├── start_worker.py                  # Solo worker RQ
│   ├── cleanup.py                       # Limpiar archivos de debug viejos
│   └── init_project.py                  # Inicializar (crear dirs, etc)
│
├── docs/
│   ├── API.md                           # Documentacion de endpoints
│   ├── BOTS.md                          # Guia para crear bots
│   ├── ARCHITECTURE.md                  # Diagrama tecnico
│   └── DEPLOYMENT.md                    # Instrucciones Docker
│
├── .env.example                         # Template variables de entorno
├── .env.local                           # Dev local (gitignored)
├── .dockerignore
├── .gitignore
├── Dockerfile                           # Single-container MVP
├── docker-compose.yml                   # MVP: single container
├── docker-compose.prod.yml              # (Future) Multi-container
├── requirements.txt                     # Dependencies prod
├── requirements-dev.txt                 # Dev + test dependencies
├── pytest.ini                           # Config pytest
├── pyproject.toml                       # Metadata del proyecto
└── README.md                            # Setup instructions
```

---

## 4. Stack de Dependencias

### requirements.txt (Principal)

```
# API
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# Queue & Redis
redis==5.0.1
rq==1.15.0
rq-scheduler==0.13.1

# Selenium
selenium==4.15.2
webdriver-manager==4.0.1

# HTTP Client (para enviar PDFs a app web)
httpx==0.25.2
requests==2.31.0

# Utilities
python-dotenv==1.0.0
tenacity==8.2.3  # Retry logic

# Logging
python-json-logger==2.0.7
```

### requirements-dev.txt

```
-r requirements.txt

# Testing
pytest==7.4.4
pytest-asyncio==0.23.2
pytest-mock==3.12.0

# Code Quality
black==23.12.1
flake8==6.1.0
mypy==1.8.0
isort==5.13.2

# Documentation
mkdocs==1.5.3

# Debug
ipdb==0.13.13
```

---

## 5. Configuracion Centralizada

### config/settings.py (Resumen)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "BrokerWiz Automation"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False
    
    # API
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    API_KEY: str = "dev-key"  # Override con env var
    API_REQUEST_TIMEOUT: int = 120
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    
    # RQ Workers
    NUM_WORKERS: int = 2
    WORKER_TIMEOUT: int = 3600  # 1 hora max
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: int = 2  # Segundos, exponencial
    
    # Selenium
    HEADLESS: bool = True
    CHROME_ARGS: list = [
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--start-maximized"
    ]
    IMPLICIT_WAIT: int = 10
    PAGE_LOAD_TIMEOUT: int = 30
    
    # App Web Integration
    APP_WEB_BASE_URL: str = "http://localhost:3000"  # URL base de app web
    APP_WEB_PDF_UPLOAD_ENDPOINT: str = "/archivos-cotizacion"  # Endpoint para subir PDFs
    APP_WEB_API_KEY: str = ""  # API key para autenticarse con app web (REQUERIDO)
    APP_WEB_PDF_UPLOAD_TIMEOUT: int = 60  # Timeout para upload de PDFs
    APP_WEB_PDF_UPLOAD_RETRIES: int = 3  # Reintentos en caso de fallo
    
    # Storage Temporal
    TEMP_STORAGE_PATH: str = "/tmp/bots-selenium"  # Solo para archivos temporales
    SCREENSHOT_PATH: str = "/app/storage/screenshots"  # Debug screenshots
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Jobs
    JOB_RESULT_TTL: int = 86400  # 24 horas
    JOB_FAILURE_TTL: int = 604800  # 7 dias
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

## 6. Clase Base para Bots (Template Method Pattern)

### workers/bots/base_bot.py (Resumen)

```python
from abc import ABC, abstractmethod
from selenium import webdriver
from typing import Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

class BaseBot(ABC):
    """Base class para todos los bots de seguros"""
    
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.driver = None
        self.wait = None
        self.job_id = os.getenv('RQ_JOB_ID', 'unknown')
        self.aseguradora = self.__class__.__name__
        self.pdf_bytes = None  # PDF en memoria
    
    def setup_driver(self):
        """Inicializa ChromeDriver"""
        # Logica común de inicializacion
    
    def cleanup_driver(self):
        """Limpia recursos"""
        # Logica común de limpieza
    
    def execute(self) -> Dict[str, Any]:
        """Orquesta ejecucion (Template Method)"""
        try:
            self.setup_driver()
            self._login()
            self._navigate_to_quote()
            result = self._extract_quote()
            self._generate_pdf()  # Genera PDF en self.pdf_bytes
            
            # Enviar PDF a app web
            from workers.bots.pdf_uploader import upload_pdf_to_app_web
            response = upload_pdf_to_app_web(
                pdf_bytes=self.pdf_bytes,
                solicitud_aseguradora_id=self.payload.get('in_strIDSolicitudAseguradora'),
                aseguradora=self.aseguradora,
                job_id=self.job_id
            )
            
            return {
                "status": "success",
                "uploaded_file_id": response.get('id'),
                "quote_data": result
            }
        
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            self._take_screenshot("error")
            raise
        
        finally:
            self.cleanup_driver()
    
    # Metodos abstract que cada bot implementa
    @abstractmethod
    def _login(self):
        pass
    
    @abstractmethod
    def _navigate_to_quote(self):
        pass
    
    @abstractmethod
    def _extract_quote(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def _generate_pdf(self):
        """Genera PDF y lo almacena en self.pdf_bytes"""
        pass
    
    # Metodos helper compartidos
    def wait_and_click(self, locator):
        """Helper para esperar y clickear"""
        pass
    
    def wait_and_send_keys(self, locator, keys):
        """Helper para esperar y enviar texto"""
        pass
    
    def _take_screenshot(self, name: str):
        """Guarda screenshot para debugging (solo debug)"""
        pass
```

### workers/bots/pdf_uploader.py

```python
import httpx
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

def upload_pdf_to_app_web(pdf_bytes: bytes, solicitud_aseguradora_id: str,
                          aseguradora: str, job_id: str) -> dict:
    """
    Envia PDF generado por bot a endpoint de app web
    
    POST {APP_WEB_BASE_URL}/archivos-cotizacion
    Content-Type: multipart/form-data
    """
    
    url = f"{settings.APP_WEB_BASE_URL}{settings.APP_WEB_PDF_UPLOAD_ENDPOINT}"
    
    files = {
        'archivo': ('cotizacion.pdf', pdf_bytes, 'application/pdf')
    }
    
    data = {
        'idSolicitudAseguradora': solicitud_aseguradora_id,
        'tipoSubida': 'bot'
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"[{job_id}] PDF subido exitosamente a app web")
            logger.info(f"Response: {result}")
            
            return result.get('data', {})
    
    except httpx.HTTPError as e:
        logger.error(f"[{job_id}] Error al subir PDF a app web: {e}")
        raise
```

---

## 7. API REST Endpoints

### POST /api/{aseguradora}/cotizar
- **Request**: JSON payload con datos del vehiculo y solicitante
- **Response**: `{"job_id": "abc123", "status": "queued", "status_url": "/api/jobs/abc123"}`
- **Accion**: Encola task en RQ

### GET /api/jobs/{job_id}
- **Response**: `{"job_id": "abc123", "status": "queued|processing|completed|failed", "result": {...}, "error": "..."`
- **Accion**: Retorna estado y resultado si completo
- **Nota**: Si completo exitosamente, `result` incluye `uploaded_file_id` del PDF en app web

### GET /health
- **Response**: `{"status": "healthy", "redis": "connected", "workers": 2}`
- **Accion**: Liveness check para Kubernetes/orchestration

### DELETE /api/jobs/{job_id}
- **Response**: `{"status": "cancelled"}`
- **Accion**: Cancela job si está queued

---

## 8. Containerizacion

### Dockerfile (Single-Container MVP)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    chromium-browser \
    chromium-chromedriver \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Crea directorio de screenshots (debug solamente)
RUN mkdir -p /app/storage/screenshots

# Entrypoint: inicia API + Redis + Workers
CMD ["python", "scripts/start_all.py"]
```

### docker-compose.yml (MVP - Simplificado)

```yaml
version: '3.8'

services:
  bots-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NUM_WORKERS=2
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
      - API_KEY=dev-key
      - APP_WEB_BASE_URL=http://app-web:3000  # O URL de app web
      - REDIS_HOST=localhost  # Dentro del contenedor
    volumes:
      - ./storage/screenshots:/app/storage/screenshots  # Solo debug
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### scripts/start_all.py

```python
import subprocess
import time
import os
import signal

# 1. Redis
redis = subprocess.Popen(['redis-server', '--port', '6379'])
time.sleep(2)

# 2. N Workers RQ
num_workers = int(os.getenv('NUM_WORKERS', 2))
workers = []
for i in range(num_workers):
    worker = subprocess.Popen([
        'python', '-m', 'rq', 'worker', 'default', '--with-scheduler'
    ])
    workers.append(worker)

# 3. FastAPI (foreground)
api = subprocess.Popen([
    'uvicorn', 'app.main:app',
    '--host', '0.0.0.0', '--port', '8000'
])

# Cleanup en Ctrl+C
def signal_handler(sig, frame):
    print("Shutting down...")
    redis.terminate()
    for w in workers:
        w.terminate()
    api.terminate()
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
api.wait()
```

---

## 9. Mapeo de Payloads por Aseguradora

### workers/bots/payload_mappers.py (Resumen)

```python
PAYLOAD_MAPPERS = {
    "hdi": {
        "in_strIDSolicitudAseguradora": "meta.solicitudAseguradoraId",
        "in_strTipoIdentificacionAsesorUsuario": "asesor.tipoIdentificacionAsesor",
        # ... más campos
    },
    "axa": { ... },
    "runt": { ... },
    "sura": { ... },
    # ... rest of insurers
}

def map_payload(aseguradora: str, context: dict) -> dict:
    """
    Mapea desde QuoteContext a payload especifico de aseguradora
    Ejemplo: {"in_strIDSolicitudAseguradora": "abc123", ...}
    """
    mapper = PAYLOAD_MAPPERS.get(aseguradora.lower())
    # Logica de mapeo con validacion
    return mapped_payload
```

---

## 10. Logging y Monitoreo

### config/logging_config.py (Estrategia)

- **Console**: INFO+ (legible)
- **app.log**: DEBUG+ (detalle completo, 10MB rotating, 5 backups)
- **errors.log**: ERROR+ (solo errores, separado para alertas)
- **bots.log**: DEBUG (bot-specific, rotacion separada)

### Formato
```
2026-01-21 14:35:22 - [workers.bots.hdi_bot] - INFO - [hdi_bot.py:45] - _login() - [job-abc123] Login exitoso
```

### Health Check
```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "redis": "connected" if redis_connected else "disconnected",
        "workers": count_active_workers(),
        "uptime_seconds": app_uptime()
    }
```

---

## 11. Error Handling y Reintentos

### Estrategia

1. **Reintento automático** con backoff exponencial (2^attempt segundos)
   - Intento 1: Falla → Espera 2s
   - Intento 2: Falla → Espera 4s
   - Intento 3: Falla → Marca como failed

2. **Errores capturados**:
   - Network timeout → Reintentar
   - Element not found → Reintentar con wait más largo
   - PDF generation failed → Reintentar
   - PDF upload failed → Reintentar (timeout en app web)
   - Authentication failed → NO reintentar (marcar failed inmediatamente)

3. **Dead Letter Queue**
   - Jobs que fallan tras 3 reintentos → Logs en `errors.log`
   - Webhook notificacion (opcional) a app web

### workers/tasks.py

```python
def execute_bot_with_retry(aseguradora: str, payload: dict, 
                           attempt=1, max_retries=3):
    try:
        bot_module = __import__(f'workers.bots.{aseguradora}_bot', fromlist=['execute'])
        return bot_module.execute(payload)
    except Exception as e:
        if attempt < max_retries and should_retry(e):
            wait_time = 2 ** attempt
            time.sleep(wait_time)
            return execute_bot_with_retry(aseguradora, payload, attempt+1, max_retries)
        else:
            raise
```

---

## 12. Admin Dashboard & Monitoring

### Vision General

Dashboard web en vivo para visualizar:
- Estado de Redis y workers
- Jobs encolados, procesándose, completados, fallidos
- Estadisticas por aseguradora
- Logs en tiempo real
- Metricas Prometheus-compatible

### Librerias de Monitoreo

#### En requirements.txt
```
# Monitoring & Metrics
prometheus-client==0.19.0
```

#### Stack Admin
- **Backend**: FastAPI endpoints en `/admin/*`
- **Frontend**: HTML/JS simple (SPA embebida, sin Node.js)
- **Metricas**: Prometheus client para scraping
- **Real-time**: Server-sent events (SSE) para logs live

### Estructura de Archivos Nuevos

```
app/
├── routes/
│   ├── admin.py              # NEW: Endpoints /admin/*
│   └── ...
├── services/
│   ├── monitoring.py         # NEW: MonitoringService
│   ├── redis_service.py
│   └── ...
├── templates/
│   └── dashboard.html        # NEW: Dashboard UI
└── ...
```

### Arquitectura

#### A. Servicio de Monitoreo (`services/monitoring.py`)

```python
from typing import Dict, List, Any
from redis import Redis
import json
from datetime import datetime

class MonitoringService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    def get_redis_info(self) -> Dict[str, Any]:
        """Informacion de Redis"""
        info = self.redis.info()
        return {
            "memory_mb": info.get("used_memory") / 1024 / 1024,
            "connected_clients": info.get("connected_clients"),
            "total_commands": info.get("total_commands_processed")
        }
    
    def get_workers_status(self) -> Dict[str, Any]:
        """Estado de workers RQ"""
        from rq import Worker
        workers = Worker.all(connection=self.redis)
        return {
            "total": len(workers),
            "busy": sum(1 for w in workers if w.state == 'busy'),
            "idle": sum(1 for w in workers if w.state == 'idle'),
            "workers": [
                {
                    "id": w.name,
                    "state": w.state,
                    "current_job": w.get_current_job().id if w.get_current_job() else None
                }
                for w in workers
            ]
        }
    
    def get_jobs_summary(self) -> Dict[str, int]:
        """Resumen de jobs por estado"""
        from rq import Queue
        queue = Queue(connection=self.redis)
        return {
            "queued": len(queue),
            "failed": len(queue.failed_job_registry),
            "completed": len(queue.completed_job_registry)
        }
    
    def get_bots_running(self) -> List[Dict[str, Any]]:
        """Bots actualmente corriendo"""
        from rq import Worker
        workers = Worker.all(connection=self.redis)
        running = []
        for w in workers:
            job = w.get_current_job()
            if job:
                running.append({
                    "worker": w.name,
                    "aseguradora": job.args[0] if job.args else None,
                    "start_time": job.started_job_registry.get(job.id),
                    "timeout": job.timeout
                })
        return running
    
    def get_health(self) -> Dict[str, Any]:
        """Health check general"""
        try:
            redis_info = self.get_redis_info()
            workers = self.get_workers_status()
            jobs = self.get_jobs_summary()
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "redis": redis_info,
                "workers": workers,
                "jobs": jobs,
                "bots_running": len(self.get_bots_running())
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def add_log(self, level: str, message: str, **extra):
        """Agregar log a canal Redis (SSE streaming)"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **extra
        }
        self.redis.rpush("app:logs", json.dumps(log_entry))
        # Mantener últimos 1000 logs
        self.redis.ltrim("app:logs", -1000, -1)
        # Publicar en canal para SSE
        self.redis.publish("logs", json.dumps(log_entry))
```

#### B. Endpoints Admin

```python
# En app/routes/admin.py (nuevo)

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from services.monitoring import MonitoringService

router = APIRouter(prefix="/admin", tags=["admin"])

async def verify_api_key(authorization: str = Header(...)):
    """Verificar API Key en todos los endpoints admin"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth")
    token = authorization.split(" ")[1]
    if token != settings.API_KEY:  # API_KEY == auth para admin
        raise HTTPException(status_code=403, detail="Forbidden")
    return token

@router.get("/health", dependencies=[Depends(verify_api_key)])
async def health_check(monitoring: MonitoringService = Depends(get_monitoring)):
    """GET /admin/health - Estado general del sistema"""
    return monitoring.get_health()

@router.get("/dashboard", dependencies=[Depends(verify_api_key)])
async def dashboard_data(monitoring: MonitoringService = Depends(get_monitoring)):
    """GET /admin/dashboard - Datos para el dashboard"""
    return {
        "workers": monitoring.get_workers_status(),
        "jobs": monitoring.get_jobs_summary(),
        "bots_running": monitoring.get_bots_running(),
        "redis": monitoring.get_redis_info()
    }

@router.get("/metrics", dependencies=[Depends(verify_api_key)])
async def metrics(monitoring: MonitoringService = Depends(get_monitoring)):
    """GET /admin/metrics - Metricas en formato Prometheus"""
    from prometheus_client import generate_latest
    return StreamingResponse(
        iter([generate_latest()]),
        media_type="text/plain"
    )

@router.get("/logs/stream", dependencies=[Depends(verify_api_key)])
async def stream_logs(monitoring: MonitoringService = Depends(get_monitoring)):
    """GET /admin/logs/stream - SSE streaming de logs"""
    async def event_generator():
        pubsub = monitoring.redis.pubsub()
        pubsub.subscribe("logs")
        
        for message in pubsub.listen():
            if message["type"] == "message":
                yield f"data: {message['data']}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.get("/ui")
async def dashboard_ui():
    """GET /admin/ui - HTML del dashboard (sin auth para desarrollo)"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=open("app/templates/dashboard.html").read())
```

#### C. Dashboard HTML (`app/templates/dashboard.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <title>BrokerWiz Bot Admin</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        header { margin-bottom: 30px; }
        h1 { font-size: 2em; color: #00d4ff; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 20px; }
        .card h3 { color: #00d4ff; margin-bottom: 15px; }
        .stat { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; }
        .stat-label { color: #999; }
        .stat-value { font-weight: bold; color: #00d4ff; }
        .health-ok { color: #00c800; }
        .health-warn { color: #ffaa00; }
        .health-bad { color: #ff5555; }
        .logs { background: #0a0a0a; border: 1px solid #333; border-radius: 8px; padding: 15px; height: 400px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.85em; }
        .log-entry { padding: 3px 0; }
        .log-error { color: #ff5555; }
        .log-warn { color: #ffaa00; }
        .log-info { color: #00c800; }
        button { background: #00d4ff; color: #000; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        button:hover { background: #00a8cc; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 BrokerWiz Bot Admin Dashboard</h1>
            <p>Monitoreo en tiempo real | Última actualizacion: <span id="last-update">--:--:--</span></p>
        </header>

        <div class="grid">
            <div class="card">
                <h3>📊 Estado General</h3>
                <div class="stat">
                    <span class="stat-label">Sistema</span>
                    <span class="stat-value health-ok" id="status-health">Cargando...</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Bots Corriendo</span>
                    <span class="stat-value" id="status-running">--</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Jobs en Cola</span>
                    <span class="stat-value" id="status-queued">--</span>
                </div>
            </div>

            <div class="card">
                <h3>👷 Workers</h3>
                <div class="stat">
                    <span class="stat-label">Total</span>
                    <span class="stat-value" id="workers-total">--</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Ocupados</span>
                    <span class="stat-value health-warn" id="workers-busy">--</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Disponibles</span>
                    <span class="stat-value health-ok" id="workers-idle">--</span>
                </div>
            </div>

            <div class="card">
                <h3>💾 Redis</h3>
                <div class="stat">
                    <span class="stat-label">Memoria (MB)</span>
                    <span class="stat-value" id="redis-memory">--</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Clientes</span>
                    <span class="stat-value" id="redis-clients">--</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>🤖 Bots Ejecutándose</h3>
            <div id="bots-list">Ninguno</div>
        </div>

        <div class="card">
            <h3>📋 Logs en Vivo</h3>
            <button onclick="clearLogs()">Limpiar</button>
            <div class="logs" id="logs-container"></div>
        </div>
    </div>

    <script>
        const API_KEY = prompt("Ingrese API Key:") || "dev";
        const HEADERS = { "Authorization": `Bearer ${API_KEY}` };

        async function updateDashboard() {
            try {
                const response = await fetch("/admin/dashboard", { headers: HEADERS });
                const data = await response.json();
                
                document.getElementById("status-running").innerText = data.bots_running;
                document.getElementById("status-queued").innerText = data.jobs.queued;
                document.getElementById("workers-total").innerText = data.workers.total;
                document.getElementById("workers-busy").innerText = data.workers.busy;
                document.getElementById("workers-idle").innerText = data.workers.idle;
                document.getElementById("redis-memory").innerText = data.redis.memory_mb.toFixed(1);
                document.getElementById("redis-clients").innerText = data.redis.connected_clients;
                
                // Listar bots
                const botsList = document.getElementById("bots-list");
                if (data.bots_running > 0) {
                    const resp = await fetch("/admin/bots-running", { headers: HEADERS });
                    const bots = await resp.json();
                    botsList.innerHTML = bots.map(b => 
                        `<div style="padding: 10px; background: #0a0a0a; margin: 5px 0; border-radius: 4px;">
                            <strong>${b.aseguradora}</strong> @ ${b.worker} (iniciado: ${new Date(b.start_time).toLocaleTimeString()})
                        </div>`
                    ).join("");
                } else {
                    botsList.innerHTML = "<em>Ningún bot en ejecucion</em>";
                }
                
                document.getElementById("last-update").innerText = new Date().toLocaleTimeString();
            } catch (e) {
                console.error("Error actualizando dashboard:", e);
                document.getElementById("status-health").innerText = "⚠️ Error";
                document.getElementById("status-health").className = "stat-value health-bad";
            }
        }

        function streamLogs() {
            const eventSource = new EventSource("/admin/logs/stream?token=" + encodeURIComponent(HEADERS.Authorization));
            eventSource.onmessage = (event) => {
                const log = JSON.parse(event.data);
                const logsDiv = document.getElementById("logs-container");
                const entry = document.createElement("div");
                entry.className = `log-entry log-${log.level.toLowerCase()}`;
                entry.innerText = `[${log.timestamp}] ${log.level}: ${log.message}`;
                logsDiv.appendChild(entry);
                logsDiv.scrollTop = logsDiv.scrollHeight;
                // Limitar a últimos 100 logs visibles
                while (logsDiv.children.length > 100) logsDiv.removeChild(logsDiv.firstChild);
            };
        }

        function clearLogs() {
            document.getElementById("logs-container").innerHTML = "";
        }

        // Actualizar cada 2 segundos
        updateDashboard();
        setInterval(updateDashboard, 2000);
        streamLogs();
    </script>
</body>
</html>
```



### Integracion en Settings

```python
# config/settings.py
class Settings(BaseSettings):
    # ... existentes ...
    
    # Monitoreo
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    PROMETHEUS_PORT: int = Field(default=8001, env="PROMETHEUS_PORT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
```

### Flujo de Monitoreo

```
┌─────────────────────────────────────────────────┐
│  Eventos en Sistema (jobs, workers, etc)        │
└──────────────┬──────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
   ┌───▼────┐      ┌─── ▼────┐
   │ Redis  │      │Prometheus
   │  Logs  │      │ Metrics
   └───┬────┘      └─── ┬────┘
       │                │
   ┌───▼─────────────────▼───┐
   │  Dashboard HTML + JS    │
   │  (refresh cada 2s)      │
   └─────────────────────────┘
```

---

## 13. Plan de Ejecucion

### **Fase 1: Setup del Proyecto (Semana 1)**
1. Inicializar repo: `git init && git remote add origin <repo>`
2. Crear estructura de carpetas (config, app, workers, tests, etc)
3. Crear `requirements.txt` con dependencias
4. Crear `.env.example` con variables de configuracion
5. Crear `Dockerfile` y `docker-compose.yml` para MVP

### **Fase 2: API Base + Monitoreo (Semana 1-2)**
1. Implementar FastAPI con rutas básicas
2. Configurar Redis y RQ
3. Implementar `MonitoringService` y endpoints `/admin/*`
4. Probar dashboard en navegador

### **Fase 3: PDF Uploader (Semana 2)**
1. Implementar `pdf_uploader.py` con @retry decorator
2. Tests unitarios de reintentos
3. Validar POST a app-web con API Key

### **Fase 4: Bots Base (Semana 2-3)**
1. Implementar `base_bot.py` con Template Method
2. Crear bots por aseguradora (heredar de base_bot)
3. Tests de extraccion de datos

### **Fase 5: Integracion E2E (Semana 3)**
1. Llamada API → Queue → Bot → PDF Upload
2. Tests end-to-end
3. Documentar flujo

### **Fase 6: Produccion (Semana 4)**
1. Dockerfile optimizado (multi-stage)
2. CI/CD pipeline básico
3. Deploy a VM/Docker
4. Logs centralizados (ELK o similar)

---

## Resumen de Decisiones Arquitectonicas

| Aspecto | Decision | Razon |
|--------|----------|-------|
| **Lenguaje** | Python 3.12 | Selenium, productivo, buen ecosistema |
| **API** | FastAPI | Async, rápido, documentacion automática |
| **Cola** | RQ (Redis Queue) | Simple, debugging fácil, scales bien 2-10 bots |
| **Storage PDFs** | NO local, enviar a app-web | Simplifica arquitectura, responsabilidad en app-web |
| **Auth** | API Key (Bearer token) | Seguro, simple de implementar |
| **Reintentos** | Exponential backoff (tenacity) | Resilencia contra fallos temporales |
| **Persistencia Jobs** | Redis ephemeral | MVP aceptable, logs en archivo para auditoria |
| **Monitoreo** | Prometheus + Dashboard HTML | Observabilidad en tiempo real sin complejidad |
| **Container** | Single container MVP | Simplidad, fácil de deployar |

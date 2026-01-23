# Plan de Implementacion: Servidor de Bots Selenium con API y Queue

## Vision General

Crear un servidor modular de automatizacion con bots Selenium orchestrados por una API REST + cola de tareas (RQ), todo containerizado para fácil escalabilidad. La arquitectura separa API y workers en procesos independientes, permitiendo crecer desde 2 bots concurrentes a 10+ sin cambios de codigo. **Los PDFs generados por los bots se envian directamente a un endpoint de la app web existente para almacenamiento.**

---

## 1. Stack Tecnico

### Lenguaje y Runtime
- **Python 3.12.x**

### Cola de Tareas
- **MQTT** como gestor de tareas

### Orquestacion de Procesos
- **Multiprocessing + FastAPI**
- API en proceso principal (FastAPI)
- N workers en procesos separados
- Resilencia: Si un worker falla, no afecta API

### Containerizacion
- **Single-container MVP**: API + Redis + 2 workers en scripts/start_all.py
- **Multi-container Produccion** (future): Docker Compose con replicas de workers (3+ containers independientes)
- Base: Python 3.12-slim + Chromium + ChromeDriver

---

## 2. Arquitectura de la Solucion

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Server                          │
│  ┌─────────────────┐                                            │
│  │ lifespan_manager│──► MQTT.connect() al iniciar               │
│  └─────────────────┘                                            │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ POST /cotizar   │───►│get_mqtt_dependency│                   │
│  │ {aseguradora}   │    │   (inyectado)    │                    │
│  └─────────────────┘    └────────┬─────────┘                    │
│                                  │                              │
│                                  ▼                              │
│                    await mqtt.publish_task("hdi", {...})        │
└──────────────────────────────────┬──────────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │     Mosquitto Broker     │
                    │   topic: bots/queue/hdi  │
                    └──────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Worker Process                             │
│  ┌─────────────────────────────────────────────────────┐        │
│  │ mqtt_worker_context(handle_task)                    │        │
│  │   ├─ subscribe("bots/queue/+")                      │        │
│  │   └─ async for topic, data in mqtt.messages():      │        │
│  │         await handle_task(topic, data)  ──────────────► Bot  │
│  │         └─ Ejecutar Selenium                        │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                 │
│  Reconexión automática si se pierde conexión                    │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Ejecucion

1. **App Web** → POST `/api/hdi/cotizar` con payload de cotizacion
2. **FastAPI** → Valida, mapea payload, encola job en Redis
3. **MQTT** → Devuelve `job_id` inmediatamente
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
│   │   ├── mqtt_service.py              # Cliente MQTT wrapper (singleton)
│   │   ├── email_service.py             # Notificaciones (opcional)
│   │   └── asegurador_mapper.py         # Mapeos de payload por aseguradora
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py                      # Validacion API Key
│       └── logging.py                   # Request/response logging
│
├── workers/                             # Procesos MQTT + Bots Selenium
│   ├── __init__.py
│   ├── mqtt_worker.py                   # Entry point: python -m workers.mqtt_worker
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
│   ├── constants.py                     # Enums (Aseguradora, MQTTTopics, ErrorCode, etc)
│   └── logging_config.py                # Setup logging (console + file)
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

# Message Queue
paho-mqtt==1.6.1

# Selenium
selenium==4.15.2
webdriver-manager==4.0.1

# HTTP Client (para enviar PDFs a app web)
httpx==0.25.2
requests==2.31.0

# Utilities
python-dotenv==1.0.0
tenacity==8.2.3  # Retry logic

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

## 5. Clase Base para Bots (Template Method Pattern)

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

## 6. API REST Endpoints

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

## 7. Mapeo de Payloads por Aseguradora

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

## 8. Logging y Monitoreo

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

## 9. Error Handling y Reintentos

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

## 10. Plan de Ejecucion

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
| **Cola** | MQTT (mosquito) | Simple, debugging fácil, scales bien 2-10 bots |
| **Storage PDFs** | NO local, enviar a app-web | Simplifica arquitectura, responsabilidad en app-web |
| **Auth** | API Key (Bearer token) | Seguro, simple de implementar |
| **Reintentos** | Exponential backoff (tenacity) | Resilencia contra fallos temporales |
| **Container** | Single container MVP | Simplidad, fácil de deployar |

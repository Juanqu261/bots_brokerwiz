# BrokerWiz Bot Automation Server

Sistema de automatización de bots Selenium para cotización de seguros, con API REST y cola de tareas MQTT.

## Quick Start (Docker)

```bash
# 1. Clone & setup
git clone <repo>
cd bots_brokerWiz
cp .env.example .env

# 2. Configurar variables en .env
# - APP_WEB_BASE_URL (URL del endpoint de app-web)
# - APP_WEB_API_KEY (Bearer token para autorización)
# - REDIS_HOST, REDIS_PORT, etc

# 3. Build & Run
docker-compose up --build

# 4. Acceder a
- API: http://localhost:8000 (OpenAPI: /docs)
```

## Estructura del Proyecto

```
bots_brokerWiz/
├── app/                      # FastAPI application
│   ├── main.py              # Entry point
│   ├── routes/              # API endpoints
│   │   ├── bots.py          # POST /api/{aseguradora}/cotizar
│   │   ├── jobs.py          # GET /api/jobs/{id}
│   │   └── admin.py         # /admin/* endpoints
│   ├── services/
│   │   ├── monitoring.py    # MonitoringService
│   │   ├── redis_service.py # Redis wrapper
│   │   └── pdf_uploader.py  # Retry logic para uploads
│   └── templates/
│       └── dashboard.html   # Admin UI
│
├── workers/                  # RQ workers & Selenium bots
│   ├── tasks.py             # Task definitions
│   └── bots/
│       ├── base_bot.py      # Abstract base class
│       ├── seguros_monterrey.py
│       ├── seguros_azteca.py
│       └── ...              # 9 aseguradoras
│
├── config/
│   ├── settings.py          # Pydantic config
│   └── constants.py         # Constants & enums
│
├── storage/                 # Screenshots & debug logs
├── logs/                    # Application logs
├── tests/                   # Unit & integration tests
│
├── requirements.txt         # Python dependencies
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Local dev environment
├── docker-entrypoint.sh    # Container startup
├── pyproject.toml          # Build config & tool settings
├── .env.example            # Environment template
└── README.md               # This file
```

## Configuración

Copiar `.env.example` a `.env` y configurar:

```bash
# API
API_KEY=your-secure-key-here

# App Web Integration (IMPORTANTE)
APP_WEB_BASE_URL=http://tu-app-web.com
APP_WEB_API_KEY=tu-bearer-token

# Workers
NUM_WORKERS=3
WORKER_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
```

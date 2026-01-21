# BrokerWiz Bot Automation Server

Sistema de automatización de bots Selenium para cotización de seguros, con API REST, cola de tareas RQ, y monitoreo en tiempo real.

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
- Admin Dashboard: http://localhost:8000/admin/ui
- RQ Dashboard: http://localhost:9181
- Métricas Prometheus: http://localhost:8001/metrics
```

## 📁 Estructura del Proyecto

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

# Redis (ajustar si no es localhost)
REDIS_HOST=localhost
REDIS_PORT=6379

# App Web Integration (IMPORTANTE)
APP_WEB_BASE_URL=http://tu-app-web.com
APP_WEB_API_KEY=tu-bearer-token

# Workers
NUM_WORKERS=3
WORKER_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
```

## API Endpoints

### Solicitar Cotización
```bash
POST /api/{aseguradora}/cotizar
Authorization: Bearer {API_KEY}
Content-Type: application/json

{
  "datos": {
    "nombre": "Juan Pérez",
    "edad": 35,
    "cobertura": "responsabilidad_civil",
    ...
  }
}

Response (202):
{
  "job_id": "abc123def456",
  "status": "queued",
  "aseguradora": "seguros_monterrey"
}
```

### Consultar Estado
```bash
GET /api/jobs/{job_id}
Authorization: Bearer {API_KEY}

Response (200):
{
  "id": "abc123def456",
  "status": "completed",
  "result": {
    "prima": 2500.00,
    "coberturas": [...],
    "pdf_url": "http://app-web/archivos/xyz.pdf"
  }
}
```

### Admin - Health Check
```bash
GET /admin/health
Authorization: Bearer {API_KEY}

Response (200):
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "redis": {...},
  "workers": {...},
  "jobs": {...}
}
```

## Añadir un Bot

### 1. Crear clase bot
```python
# workers/bots/nueva_aseguradora.py

from .base_bot import BaseBot
from config.constants import Aseguradora

class NuevaAseguradoraBot(BaseBot):
    ASEGURADORA = Aseguradora.NUEVA
    BASE_URL = "https://app.nueva-aseguradora.com"
    
    def navegar_a_cotizacion(self):
        # Implementar navegación específica
        pass
    
    def rellenar_formulario(self, datos: dict):
        # Llenar campos del formulario
        pass
    
    def obtener_resultado(self) -> dict:
        # Extraer prima, coberturas, etc
        pass
```

### 2. Registrar en config
```python
# config/constants.py
class Aseguradora(str, Enum):
    # ...
    NUEVA = "nueva_aseguradora"

# config/settings.py
BOTS_MAPPING = {
    Aseguradora.NUEVA: "workers.bots.nueva_aseguradora.NuevaAseguradoraBot"
}
```

### 3. Desplegar
```bash
docker-compose restart app  # Recarga workers con nuevo bot
```

## Monitoreo

### Admin Dashboard (UI Web)
- Acceder: http://localhost:8000/admin/ui
- Ver: Workers, jobs en cola, bots corriendo, Redis status
- Logs en vivo (SSE streaming)

### RQ Dashboard
- Acceder: http://localhost:9181
- Monitoreo de tareas en detalle

### Prometheus Metrics
- Acceder: http://localhost:8001/metrics
- Integrables con Grafana

## Testing

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# Coverage report
pytest --cov=. --cov-report=html
```

## Deployment

### Docker Single Container
```bash
docker build -t broker-wiz:latest .
docker run -d -p 8000:8000 \
  -e APP_WEB_BASE_URL=http://prod-app-web \
  -e APP_WEB_API_KEY=prod-key \
  -e NUM_WORKERS=5 \
  broker-wiz:latest
```

### Kubernetes (Multi-container)
- Separar: API deployment + Worker deployment + Redis StatefulSet
- Ver: `k8s/` (por crear)

## Seguridad

- API Key en Bearer token
- Auth a app-web con Bearer token
- Validación de entrada (Pydantic)
- CORS configurado
- Retry + backoff exponencial (resilencia)

## Logs

```bash
# Ver logs en tiempo real (Docker)
docker-compose logs -f app

# En archivos
tail -f logs/broker_wiz.log

# Formato JSON para parsing
```

## Troubleshooting

### Redis no se conecta
```bash
docker-compose ps  # Verificar que redis está corriendo
docker-compose logs redis
```

### Workers no reciben tasks
```bash
docker-compose exec app rq info  # Ver estado de workers
docker-compose exec redis redis-cli monitor  # Monitor Redis
```

### Bot falla en extracción de datos
```bash
# Verificar screenshot en storage/
ls -la storage/screenshots/
# Revisar logs de bot específico
grep "aseguradora" logs/broker_wiz.log
```

## Documentación Adicional

- [API.md](docs/API.md) - Referencia completa de endpoints
- [BOTS.md](docs/BOTS.md) - Guía de desarrollo de bots
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Decisiones de diseño
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Guía de deployment

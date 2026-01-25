# BrokerWiz - Bot Automation Server

Sistema de automatización para cotización de seguros usando bots Selenium, con API REST y cola de tareas MQTT.

## Arquitectura

```
┌─────────────┐      ┌─────────────┐      ┌─────────────────────────┐
│   Cliente   │ ───► │  FastAPI    │ ───► │   Mosquitto (MQTT)      │
│  (BrokerWiz)│      │  /api/*/    │      │   bots/queue/{aseg}     │
└─────────────┘      └─────────────┘      └───────────┬─────────────┘
                                                      │
                                    $share/workers/bots/queue/+
                                                      │
                          ┌───────────────────────────┼───────────────────────────┐
                          ▼                           ▼                           ▼
                    ┌───────────┐                ┌───────────┐                ┌───────────┐
                    │ Worker 1  │                │ Worker 2  │                │ Worker N  │
                    │ (Selenium)│                │ (Selenium)│                │ (Selenium)│
                    └───────────┘                └───────────┘                └───────────┘
```

**Flujo:** Cliente → API → MQTT → Workers (Shared Subscriptions, round-robin)

## Quick Start

```bash
# 1. Clonar e instalar
git clone <repo> /opt/brokerwiz && cd /opt/brokerwiz
chmod +x scripts/*.sh && ./scripts/setup.sh

# 2. Configurar Mosquitto
sudo ./scripts/mosquitto.sh setup
./scripts/mosquitto.sh version  # Verificar MQTT 5 (v2.0+)

# 3. Configurar entorno
cp .env.example .env && nano .env

# 4. Iniciar servicios
./scripts/api.sh start -d       # API (background)
# Workers: próximamente

# 5. Verificar
curl http://localhost:8000/health
```

## API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Health check (API + MQTT) |
| `POST` | `/api/{aseguradora}/cotizar` | Encolar tarea de cotización |
| `GET` | `/logs` | Consultar logs del sistema |

**Aseguradoras soportadas:** `hdi`, `sura`, `axa`, `allianz`, `bolivar`, `mundial`, `equidad`, `solidaria`, `sbs`

## Ejemplo de Uso

```bash
curl -X POST http://localhost:8000/api/hdi/cotizar \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "SOL-001",
    "in_strPlaca": "ABC123",
    "in_strNumDoc": "1234567890"
  }'
```

## Estructura del Proyecto

```
├── app/                 # API FastAPI
├── workers/             # Workers MQTT + Bots Selenium
│   └── bots/            # Bots por aseguradora
├── mosquitto/           # Cliente MQTT (aiomqtt)
├── config/              # Configuración y settings
├── scripts/             # Scripts de despliegue
├── logs/                # Logs centralizados (rotación diaria)
└── tests/               # Tests unitarios e integración
```

## Documentación Adicional

- [Tests Manuales](docs/manual-testing.md) - Guía de pruebas locales

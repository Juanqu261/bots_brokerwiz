# BrokerWiz Bot Automation Server

Sistema de automatización de bots Selenium para cotización de seguros, con API REST y cola de tareas MQTT.

## Quick Start

```bash
# 1. Clonar repo
git clone <repo> /opt/brokerwiz
cd /opt/brokerwiz

# 2. Setup inicial (una vez)
chmod +x scripts/*.sh
./scripts/setup.sh

# 3. Configurar Mosquitto (una vez)
sudo ./scripts/mosquitto.sh setup

# 4. Editar .env para producción
nano .env
# Cambiar: API_HOST=127.0.0.1, ENVIRONMENT=production, API_KEY=<seguro>

# 5. Iniciar API
./scripts/api.sh start -d    # Background (producción)
./scripts/api.sh start       # Foreground (desarrollo)

# 6. Verificar
./scripts/api.sh status
curl http://127.0.0.1:8000/health
```

## Agregar servicio api a nginx
```
# Agregar a /etc/nginx/sites-available/default 
# O crear /etc/nginx/sites-available/brokerwiz

server {
    listen 80;
    server_name orquestadorbots.brokerwiz.co;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Tests manuales (API - MQTT)

### Paso 1: Levantar Mosquitto (Terminal 1)

```powershell
# Iniciar broker Mosquitto en modo verbose
mosquitto -p 1883 -v
```

### Paso 2: Suscribirse a topics (Terminal 2)

```powershell
# Escuchar TODOS los mensajes de cotización
mosquitto_sub -h localhost -t "bots/queue/#" -v
```

Esta terminal mostrará los mensajes cuando lleguen.

### Paso 3: Levantar la API (Terminal 3)

```powershell
cd C:\Users\juanf\Desktop\bots_brokerWiz
python -m scripts.start_api
```

### Paso 4: Verificar conexión

```powershell
# Health check (PowerShell)
Invoke-RestMethod http://localhost:8000/health

# Debería mostrar:
# status        : healthy
# mqtt_connected: True
# service       : brokerwiz-api
```

### Paso 5: Enviar cotización de prueba (Terminal 4)

```powershell
# Crear cotización HDI
$headers = @{
    "Authorization" = "Bearer test-api-bots"
    "Content-Type" = "application/json"
}

$body = @{
    in_strIDSolicitudAseguradora = "test-manual-001"
    in_strPlaca = "ABC123"
    in_strNumDoc = "1234567890"
} | ConvertTo-Json

Invoke-RestMethod -Method POST `
    -Uri "http://localhost:8000/api/hdi/cotizar" `
    -Headers $headers `
    -Body $body
```

**Respuesta esperada:**
```
success : True
message : Tarea encolada
data    : @{job_id=abc123-uuid; aseguradora=hdi; status=pending; ...}
```

### Paso 6: Verificar mensaje en Mosquitto

En la **Terminal 2** (mosquitto_sub) deberías ver:
```
bots/queue/hdi {"job_id": "abc123-uuid", "in_strIDSolicitudAseguradora": "test-manual-001", "payload": {"in_strPlaca": "ABC123", "in_strNumDoc": "1234567890"}, ...}
```

### Consultar logs

```powershell
# Ver últimas 50 líneas del log de la API
Invoke-RestMethod "http://localhost:8000/logs?service=api&lines=50"

# Listar archivos de log
Invoke-RestMethod "http://localhost:8000/logs/list"

# Descargar log completo
Invoke-WebRequest "http://localhost:8000/logs/download?service=api" -OutFile "api.log"
```

### Resumen de terminales

| Terminal | Comando | Propósito |
|----------|---------|-----------|
| 1 | `mosquitto -v` | Broker MQTT |
| 2 | `mosquitto_sub -t "bots/queue/#" -v` | Ver mensajes |
| 3 | `python -m scripts.start_api` | API FastAPI |
| 4 | `Invoke-RestMethod ...` | Enviar requests |

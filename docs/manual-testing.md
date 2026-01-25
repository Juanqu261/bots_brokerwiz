# Tests Manuales - API y MQTT

Guía paso a paso para probar la integración API → MQTT localmente.

## Requisitos

- Python 3.11+
- Mosquitto instalado (`choco install mosquitto` en Windows)
- Variables de entorno configuradas (`.env`)

## Paso 1: Levantar Mosquitto (Terminal 1)

```powershell
mosquitto -p 1883 -v
```

## Paso 2: Suscribirse a topics (Terminal 2)

```powershell
# Escuchar TODOS los mensajes de cotización
mosquitto_sub -h localhost -t "bots/queue/#" -v
```

## Paso 3: Levantar la API (Terminal 3)

```powershell
cd C:\Users\juanf\Desktop\bots_brokerWiz
python -m scripts.start_api
```

## Paso 4: Verificar conexión

```powershell
Invoke-RestMethod http://localhost:8000/health

# Respuesta esperada:
# status        : healthy
# mqtt_connected: True
# service       : brokerwiz-api
```

## Paso 5: Enviar cotización de prueba (Terminal 4)

```powershell
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

## Paso 6: Verificar mensaje en Mosquitto

En Terminal 2 deberías ver:
```
bots/queue/hdi {"job_id": "abc123-uuid", "in_strIDSolicitudAseguradora": "test-manual-001", ...}
```

## Consultar Logs

```powershell
# Ver últimas 50 líneas
Invoke-RestMethod "http://localhost:8000/logs?service=api&lines=50"

# Listar archivos de log
Invoke-RestMethod "http://localhost:8000/logs/list"

# Descargar log completo
Invoke-WebRequest "http://localhost:8000/logs/download?service=api" -OutFile "api.log"
```

## Probar Shared Subscriptions (Workers)

```bash
# Terminal A: Worker 1
mosquitto_sub -t '$share/workers/bots/queue/+' -v

# Terminal B: Worker 2  
mosquitto_sub -t '$share/workers/bots/queue/+' -v

# Terminal C: Publicar mensajes
for i in 1 2 3 4 5; do mosquitto_pub -t 'bots/queue/hdi' -m "Mensaje $i"; done

# Observar: cada terminal recibe mensajes diferentes (round-robin)
```

## Resumen de Terminales

| Terminal | Comando | Propósito |
|----------|---------|-----------|
| 1 | `mosquitto -v` | Broker MQTT |
| 2 | `mosquitto_sub -t "bots/queue/#" -v` | Ver mensajes |
| 3 | `python -m scripts.start_api` | API FastAPI |
| 4 | `Invoke-RestMethod ...` | Enviar requests |

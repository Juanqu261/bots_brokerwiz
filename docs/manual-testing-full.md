# Test Manual - Flujo Completo

Guía para probar el sistema completo: **API → MQTT → Worker → Bot (Selenium)**

## Arquitectura del Flujo

```
┌─────────┐    ┌──────────┐    ┌────────┐    ┌─────────┐
│   API   │───►│  MQTT    │───►│ Worker │───►│   Bot   │
│ FastAPI │    │ Mosquitto│    │ Python │    │ Selenium│
└─────────┘    └──────────┘    └────────┘    └─────────┘
   POST           Queue          Listen        Chrome
  /cotizar      bots/queue/*    subscribe     navigate
```

## Configuración Previa

Asegúrate de tener en tu `.env`:

```env
ENVIRONMENT=development    # Chrome visible para debugging
MAX_CONCURRENT_BOTS=3      # Máximo de bots simultáneos
API_KEY=test-api-bots      # Key para autenticación
MQTT_HOST=localhost
MQTT_PORT=1883
```

---

## Parte 1: Flujo Completo Básico

### Paso 1.1: Levantar Mosquitto (Terminal 1)

```powershell
mosquitto -p 1883 -v
```

### Paso 1.2: Levantar la API (Terminal 2)

```powershell
cd C:\Users\juanf\Desktop\bots_brokerWiz
python -m app.main
```

### Paso 1.3: Verificar API conectada

```powershell
Invoke-RestMethod http://localhost:8000/health

# Respuesta esperada:
# status        : healthy
# mqtt_connected: True
```

### Paso 1.4: Iniciar Worker (Terminal 3)

```powershell
cd C:\Users\juanf\Desktop\bots_brokerWiz
python -m workers.mqtt_worker --id worker-1
```

Deberías ver:
```
Worker [worker-1] iniciado
  Aseguradoras: TODAS
  Persistente: True
  Max concurrent: 3
  Bots disponibles: ['hdi']
Worker listo. Esperando tareas...
```

### Paso 1.5: Enviar tarea de cotización (Terminal 4)

```powershell
$headers = @{
    "Authorization" = "Bearer test-api-bots"
    "Content-Type" = "application/json"
}

$body = @{
    in_strIDSolicitudAseguradora = "test-full-001"
    in_strPlaca = "ABC123"
    in_strNumDoc = "1234567890"
} | ConvertTo-Json

Invoke-RestMethod -Method POST `
    -Uri "http://localhost:8000/api/hdi/cotizar" `
    -Headers $headers `
    -Body $body
```

### Paso 1.6: Observar ejecución

- **Terminal 1** (Mosquitto): Mensaje publicado y recibido
- **Terminal 3** (Worker): Logs de recepción y ejecución
- **Ventana Chrome**: Se abre automáticamente (ENVIRONMENT=development)

> El bot fallará al navegar a URLs de ejemplo, pero verás el navegador abrirse.

---

## Parte 2: Múltiples Workers (Load Balancing)

### Paso 2.1: Iniciar Worker adicional (Terminal 5)

```powershell
cd C:\Users\juanf\Desktop\bots_brokerWiz
python -m workers.mqtt_worker --id worker-2
```

### Paso 2.2: Enviar múltiples tareas

```powershell
$headers = @{
    "Authorization" = "Bearer test-api-bots"
    "Content-Type" = "application/json"
}

# Enviar 4 tareas rápidamente
1..4 | ForEach-Object {
    $body = @{
        in_strIDSolicitudAseguradora = "test-parallel-$_"
        in_strPlaca = "PAR$_"
        in_strNumDoc = "100000000$_"
    } | ConvertTo-Json
    
    Invoke-RestMethod -Method POST `
        -Uri "http://localhost:8000/api/hdi/cotizar" `
        -Headers $headers `
        -Body $body
    
    Write-Host "Enviada tarea $_ de 4"
}
```

### Paso 2.3: Verificar distribución

Observa los logs de **worker-1** y **worker-2**:
- Las tareas se distribuyen entre ambos (shared subscription)
- Cada worker procesa tareas diferentes
- Se abren múltiples ventanas de Chrome

---

## Parte 3: Worker Específico por Aseguradora

### Paso 3.1: Iniciar worker dedicado a HDI

```powershell
cd C:\Users\juanf\Desktop\bots_brokerWiz
python -m workers.mqtt_worker --id worker-hdi-only --aseguradora hdi
```

Este worker SOLO procesará mensajes de `bots/queue/hdi`.

---

## Parte 4: Test de Control de Recursos

### Paso 4.1: Enviar más tareas que el límite

```powershell
$headers = @{
    "Authorization" = "Bearer test-api-bots"
    "Content-Type" = "application/json"
}

# Enviar 6 tareas (más que MAX_CONCURRENT_BOTS=3)
1..6 | ForEach-Object {
    $body = @{
        in_strIDSolicitudAseguradora = "stress-$_"
        in_strPlaca = "STR$_"
        in_strNumDoc = "200000000$_"
    } | ConvertTo-Json
    
    Invoke-RestMethod -Method POST `
        -Uri "http://localhost:8000/api/hdi/cotizar" `
        -Headers $headers `
        -Body $body
    
    Write-Host "Enviada tarea $_"
}
```

### Paso 4.2: Observar comportamiento

En los logs del worker verás:
```
[HDI] Slot adquirido para job stress-1 (1/3 activos)
[HDI] Slot adquirido para job stress-2 (2/3 activos)
[HDI] Slot adquirido para job stress-3 (3/3 activos)
[HDI] Recursos no disponibles para job stress-4: Sin slots disponibles
```

Las tareas extra quedan en cola MQTT y se procesan cuando hay slots libres.

---

## Parte 5: Modo Headless vs Visible

### Cambiar a modo headless

Edita `.env`:
```env
ENVIRONMENT=production
```

Reinicia el worker y envía una tarea. Chrome NO se abrirá visualmente pero el bot ejecutará.

### Volver a modo visible

```env
ENVIRONMENT=development
```

---

## Resumen de Terminales

| Terminal | Comando | Propósito |
|----------|---------|-----------|
| 1 | `mosquitto -v` | Broker MQTT |
| 2 | `python -m scripts.start_api` | API FastAPI |
| 3 | `python -m workers.mqtt_worker --id worker-1` | Worker principal |
| 4 | PowerShell para requests | Enviar tareas |
| 5 | `python -m workers.mqtt_worker --id worker-2` | Worker secundario |

---

## Troubleshooting

### Chrome no se abre
- Verifica `ENVIRONMENT=development` en `.env`
- Reinicia el worker después de cambiar `.env`

### Worker no recibe mensajes
1. Verifica Mosquitto corriendo: `mosquitto -v`
2. Verifica API conectada: `GET /health` → `mqtt_connected: True`
3. Revisa el topic correcto: `bots/queue/hdi`

### Error "ResourceUnavailableError"
Sistema saturado. Espera o aumenta `MAX_CONCURRENT_BOTS` en `.env`

### Bot falla con error de navegación
Normal con URLs de ejemplo. Lo importante es ver:
- Chrome abrirse
- Logs del worker procesando
- El flujo completo ejecutándose

---

## Limpieza

Para detener todo:
1. `Ctrl+C` en cada terminal
2. Cerrar ventanas de Chrome residuales (si las hay)

# Request Tracking - Seguimiento de Peticiones

## 1. Enviar Request y Capturar job_id

```bash
API_KEY=$(grep "^API_KEY=" .env | cut -d= -f2)
API_PORT=$(grep "^API_PORT=" .env | cut -d= -f2)

RESPONSE=$(curl -s -X POST http://localhost:$API_PORT/api/sbs/cotizar \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "TEST-SBS-001",
    "payload": {
      "in_strTipoIdentificacionAsesorUsuario": "CC",
      "in_strUsuarioAsesor": "dseguroltda@gmail.com",
      "in_strContrasenaAsesor": "SBSseguros2026+",
      "in_strTipoDoc": "CC",
      "in_strNumDoc": "1234567890",
      "in_strEmail": "cliente@example.com",
      "in_strCelular": "3001234567",
      "in_strPlaca": "ABC123",
      "in_strKmVehiculo": "50000",
      "in_strCodigoFasecolda": "76",
      "in_strModelo": "2020",
      "in_strPlan": "ESTANDAR"
    }
  }')

JOB_ID=$(echo $RESPONSE | jq -r '.data.job_id')
echo "Job ID: $JOB_ID"
```

## 2. Seguir en Logs

```bash
# API recibió la petición
./scripts/api.sh logs | grep $JOB_ID

# Worker procesando
./scripts/worker.sh logs | grep $JOB_ID

# MQTT encolado
sudo tail -50 /var/log/mosquitto/mosquitto.log
```

## 3. Monitoreo en Tiempo Real

```bash
# Ver todo combinado
tail -f logs/api.log logs/worker-*.log | grep $JOB_ID

# O status general
./scripts/worker.sh status
```

## 4. Resultados Esperados

| Etapa | Log | Resultado |
|-------|-----|-----------|
| **API** | `Job abc123 encolado` | ✅ Recibido |
| **MQTT** | `bots/queue/sbs` | ✅ Publicado |
| **Worker** | `Recibido job: abc123` | ✅ Procesando |
| **Bot** | `completado exitosamente` | ✅ Éxito |
| **Error** | `completado con errores` | ⚠️ Fallo (DLQ) |

## 5. Script Automatizado

```bash
#!/bin/bash
API_KEY=$(grep "^API_KEY=" .env | cut -d= -f2)
API_PORT=$(grep "^API_PORT=" .env | cut -d= -f2)

# Enviar
RESPONSE=$(curl -s -X POST http://localhost:$API_PORT/api/sbs/cotizar \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"in_strIDSolicitudAseguradora":"TEST-SBS-001","payload":{"in_strTipoIdentificacionAsesorUsuario":"CC","in_strUsuarioAsesor":"dseguroltda@gmail.com","in_strContrasenaAsesor":"SBSseguros2026+","in_strTipoDoc":"CC","in_strNumDoc":"1234567890","in_strEmail":"cliente@example.com","in_strCelular":"3001234567","in_strPlaca":"ABC123","in_strKmVehiculo":"50000","in_strCodigoFasecolda":"76","in_strModelo":"2020","in_strPlan":"ESTANDAR"}}')

JOB_ID=$(echo $RESPONSE | jq -r '.data.job_id')
echo "✓ Job: $JOB_ID"

# Seguir
echo "API:"
./scripts/api.sh logs | grep $JOB_ID | tail -2

sleep 5

echo "Workers:"
./scripts/worker.sh logs | grep $JOB_ID | tail -5
```

Guardar como `test-request.sh` y ejecutar:
```bash
chmod +x test-request.sh
./test-request.sh
```

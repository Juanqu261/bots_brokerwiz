#!/bin/bash
# Docker entrypoint script para BrokerWiz Bot Automation Server

set -e

echo "Iniciando BrokerWiz Bot Automation Server..."

# Crear directorios si no existen
mkdir -p logs storage

# Inicializar configuración desde .env
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

echo "Iniciando API (FastAPI)..."
uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT:-8000} &
API_PID=$!

echo "Iniciando Workers (MQTT)..."
for i in $(seq 1 ${NUM_WORKERS:-3}); do
    python -m workers.mqtt_worker &
    echo "  Worker $i iniciado"
done

echo "Sistema completo iniciado"
echo "   API: http://localhost:${API_PORT:-8000}"
echo "   MQTT: mosquitto:1883"

# Esperar a que la app se termine
wait $API_PID

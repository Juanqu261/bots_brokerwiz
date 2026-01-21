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
python -m app.main &
API_PID=$!

echo "Iniciando Workers (RQ)..."
for i in $(seq 1 ${NUM_WORKERS:-3}); do
    rq worker -c config.settings &
    echo "  Worker $i iniciado"
done

echo "Sistema completo iniciado"
echo "   API: http://localhost:${API_PORT:-8000}"
echo "   Métricas: http://localhost:${PROMETHEUS_PORT:-8001}/metrics"
echo "   Admin: http://localhost:${API_PORT:-8000}/admin/ui"
echo "   RQ Dashboard: http://localhost:9181"

# Esperar a que la app se termine
wait $API_PID

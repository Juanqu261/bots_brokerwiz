#!/bin/bash
#
# BrokerWiz - Gestión de la API FastAPI
# =====================================
#
# Uso:
#   ./scripts/api.sh start      # Iniciar API (foreground)
#   ./scripts/api.sh start -d   # Iniciar API (background/daemon)
#   ./scripts/api.sh stop       # Detener API
#   ./scripts/api.sh status     # Ver estado
#   ./scripts/api.sh logs       # Ver logs (si corre como daemon)
#   ./scripts/api.sh restart    # Reiniciar
#

set -e

# Directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.api.pid"
LOG_FILE="$PROJECT_DIR/logs/api.log"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; }
log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

cd "$PROJECT_DIR"

# ============================================================================
# Funciones auxiliares
# ============================================================================

check_venv() {
    if [ ! -d ".venv" ]; then
        log_err "Entorno virtual no encontrado. Ejecutar primero: ./scripts/setup.sh"
        exit 1
    fi
}

check_mosquitto() {
    if ! systemctl is-active mosquitto &>/dev/null; then
        log_err "Mosquitto no está corriendo. Ejecutar: sudo ./scripts/mosquitto.sh setup"
        exit 1
    fi
}

get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    fi
}

is_running() {
    local pid=$(get_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

# ============================================================================
# start - Iniciar API
# ============================================================================

cmd_start() {
    local DAEMON=false
    
    if [ "$1" = "-d" ] || [ "$1" = "--daemon" ]; then
        DAEMON=true
    fi
    
    check_venv
    check_mosquitto
    
    if is_running; then
        log_info "API ya está corriendo (PID: $(get_pid))"
        return 0
    fi
    
    source .venv/bin/activate
    
    # Leer configuración del .env
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    fi
    
    HOST="${API_HOST:-127.0.0.1}"
    PORT="${API_PORT:-8000}"
    WORKERS="${API_WORKERS:-2}"
    
    log_info "Iniciando API en $HOST:$PORT..."
    
    if [ "$DAEMON" = true ]; then
        # Modo daemon (background)
        mkdir -p logs
        nohup .venv/bin/uvicorn app.main:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            >> "$LOG_FILE" 2>&1 &
        
        echo $! > "$PID_FILE"
        sleep 2
        
        if is_running; then
            log_ok "API iniciada en background (PID: $(get_pid))"
            log_info "Logs: tail -f $LOG_FILE"
        else
            log_err "API no pudo iniciar. Ver logs: cat $LOG_FILE"
            exit 1
        fi
    else
        # Modo foreground (desarrollo)
        log_info "Modo foreground. Ctrl+C para detener."
        echo ""
        
        .venv/bin/uvicorn app.main:app \
            --host "$HOST" \
            --port "$PORT" \
            --reload
    fi
}

# ============================================================================
# stop - Detener API
# ============================================================================

cmd_stop() {
    if ! is_running; then
        log_info "API no está corriendo"
        rm -f "$PID_FILE"
        return 0
    fi
    
    local pid=$(get_pid)
    log_info "Deteniendo API (PID: $pid)..."
    
    kill "$pid" 2>/dev/null || true
    
    # Esperar que termine
    for i in {1..10}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            break
        fi
        sleep 1
    done
    
    # Forzar si no termina
    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
    fi
    
    rm -f "$PID_FILE"
    log_ok "API detenida"
}

# ============================================================================
# status - Ver estado
# ============================================================================

cmd_status() {
    echo ""
    echo "═══════════════════════════════════════"
    echo "         BrokerWiz API Status"
    echo "═══════════════════════════════════════"
    echo ""
    
    # API
    printf "API:        "
    if is_running; then
        echo -e "${GREEN}corriendo${NC} (PID: $(get_pid))"
    else
        echo -e "${RED}detenida${NC}"
    fi
    
    # Mosquitto
    printf "Mosquitto:  "
    if systemctl is-active mosquitto &>/dev/null; then
        echo -e "${GREEN}corriendo${NC}"
    else
        echo -e "${RED}detenido${NC}"
    fi
    
    # Health check (si está corriendo)
    if is_running; then
        printf "Health:     "
        if [ -f ".env" ]; then
            source .env
        fi
        PORT="${API_PORT:-8000}"
        
        if curl -s "http://127.0.0.1:$PORT/health" | grep -q "healthy"; then
            echo -e "${GREEN}healthy${NC}"
        else
            echo -e "${YELLOW}degraded${NC}"
        fi
    fi
    
    echo ""
}

# ============================================================================
# logs - Ver logs
# ============================================================================

cmd_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        log_info "No hay logs. La API no ha corrido en modo daemon."
        return 0
    fi
    
    tail -f "$LOG_FILE"
}

# ============================================================================
# restart - Reiniciar
# ============================================================================

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start "$@"
}

# ============================================================================
# Main
# ============================================================================

case ${1:-help} in
    start)
        cmd_start "$2"
        ;;
    stop)
        cmd_stop
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs
        ;;
    restart)
        cmd_restart "$2"
        ;;
    *)
        echo "Uso: $0 <comando>"
        echo ""
        echo "Comandos:"
        echo "  start       Iniciar API (foreground, con reload)"
        echo "  start -d    Iniciar API (background/daemon)"
        echo "  stop        Detener API"
        echo "  status      Ver estado de servicios"
        echo "  logs        Ver logs (modo daemon)"
        echo "  restart     Reiniciar API"
        echo ""
        ;;
esac

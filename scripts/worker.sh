#!/bin/bash
#
# BrokerWiz - Gestión de Workers MQTT
# ====================================
#
# Uso:
#   ./scripts/worker.sh start               # Iniciar workers según NUM_WORKERS en .env
#   ./scripts/worker.sh start -n 2 -b 4     # Iniciar 2 workers, cada uno con 4 bots max
#   ./scripts/worker.sh start -n 1 -a hdi   # 1 worker solo para HDI
#   ./scripts/worker.sh stop                # Detener todos los workers
#   ./scripts/worker.sh status              # Ver estado de workers
#   ./scripts/worker.sh logs [worker-id]    # Ver logs de un worker específico
#   ./scripts/worker.sh restart             # Reiniciar workers
#
# Configuración por defecto (desde .env):
#   NUM_WORKERS=1           # Número de workers a iniciar
#   MAX_CONCURRENT_BOTS=3   # Bots simultáneos POR worker
#
# Ejemplos de configuraciones:
#   2 workers × 4 bots = 8 Chrome máximo simultáneos
#   3 workers × 3 bots = 9 Chrome máximo simultáneos
#   1 worker  × 2 bots = 2 Chrome máximo simultáneos
#

set -e

# Directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_DIR/.pids"
LOG_DIR="$PROJECT_DIR/logs"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; }
log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }
log_worker() { echo -e "${CYAN}[WORKER]${NC} $1"; }

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

load_env() {
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi
}

get_worker_pids() {
    # Retorna lista de archivos PID
    if [ -d "$PID_DIR" ]; then
        find "$PID_DIR" -name "worker-*.pid" 2>/dev/null
    fi
}

is_worker_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

get_running_workers_count() {
    local count=0
    for pid_file in $(get_worker_pids); do
        if is_worker_running "$pid_file"; then
            ((count++))
        fi
    done
    echo $count
}

# ============================================================================
# start - Iniciar Workers
# ============================================================================

cmd_start() {
    local NUM_WORKERS_ARG=""
    local MAX_BOTS_ARG=""
    local ASEGURADORA=""
    local PERSISTENT="true"
    
    # Parsear argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--num-workers)
                NUM_WORKERS_ARG="$2"
                shift 2
                ;;
            -b|--max-bots)
                MAX_BOTS_ARG="$2"
                shift 2
                ;;
            -a|--aseguradora)
                ASEGURADORA="$2"
                shift 2
                ;;
            --no-persistent)
                PERSISTENT="false"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    check_venv
    check_mosquitto
    load_env
    
    # Determinar número de workers
    local NUM_WORKERS=${NUM_WORKERS_ARG:-${NUM_WORKERS:-3}}
    local MAX_BOTS=${MAX_BOTS_ARG:-${MAX_CONCURRENT_BOTS:-3}}
    
    # Verificar si ya hay workers corriendo
    local running=$(get_running_workers_count)
    if [ "$running" -gt 0 ]; then
        log_info "Ya hay $running worker(s) corriendo. Usa 'stop' primero o 'status' para ver."
        return 0
    fi
    
    # Crear directorios necesarios
    mkdir -p "$PID_DIR" "$LOG_DIR"
    
    source .venv/bin/activate
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "                   Iniciando Workers"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "  Workers:              $NUM_WORKERS"
    echo "  Max bots por worker:  $MAX_BOTS"
    echo "  Total Chrome máximo:  $((NUM_WORKERS * MAX_BOTS))"
    echo "  Aseguradora:          ${ASEGURADORA:-todas}"
    echo "  Sesión persistente:   $PERSISTENT"
    echo ""
    
    # Iniciar cada worker
    for i in $(seq 1 $NUM_WORKERS); do
        local WORKER_ID="worker-$i"
        local PID_FILE="$PID_DIR/$WORKER_ID.pid"
        local WORKER_LOG="$LOG_DIR/$WORKER_ID.log"
        
        # Construir comando
        local CMD=".venv/bin/python -m workers.mqtt_worker --id $WORKER_ID"
        
        if [ -n "$ASEGURADORA" ]; then
            CMD="$CMD --aseguradora $ASEGURADORA"
        fi
        
        if [ "$PERSISTENT" = "false" ]; then
            CMD="$CMD --no-persistent"
        fi
        
        # Exportar MAX_CONCURRENT_BOTS para este worker
        export MAX_CONCURRENT_BOTS="$MAX_BOTS"
        
        # Iniciar worker en background
        nohup $CMD >> "$WORKER_LOG" 2>&1 &
        local PID=$!
        echo "$PID" > "$PID_FILE"
        
        # Verificar que inició
        sleep 1
        if is_worker_running "$PID_FILE"; then
            log_worker "$WORKER_ID iniciado (PID: $PID, max_bots: $MAX_BOTS)"
        else
            log_err "$WORKER_ID falló al iniciar. Ver: tail $WORKER_LOG"
        fi
    done
    
    echo ""
    log_ok "Workers iniciados. Ver logs con: $0 logs"
    log_info "Detener con: $0 stop"
}

# ============================================================================
# stop - Detener Workers
# ============================================================================

cmd_stop() {
    echo ""
    log_info "Deteniendo workers..."
    
    local stopped=0
    
    for pid_file in $(get_worker_pids); do
        local worker_id=$(basename "$pid_file" .pid)
        
        if is_worker_running "$pid_file"; then
            local pid=$(cat "$pid_file")
            
            # Enviar SIGTERM (graceful shutdown)
            kill "$pid" 2>/dev/null || true
            
            # Esperar que termine (max 10 segundos)
            for i in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            
            # Forzar si no termina
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
                log_info "$worker_id forzado a terminar (PID: $pid)"
            else
                log_worker "$worker_id detenido (PID: $pid)"
            fi
            
            ((stopped++))
        fi
        
        rm -f "$pid_file"
    done
    
    if [ "$stopped" -eq 0 ]; then
        log_info "No había workers corriendo"
    else
        log_ok "$stopped worker(s) detenido(s)"
    fi
}

# ============================================================================
# status - Ver estado de Workers
# ============================================================================

cmd_status() {
    load_env
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "                   Estado de Workers"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    # Mosquitto
    printf "  Mosquitto:     "
    if systemctl is-active mosquitto &>/dev/null; then
        echo -e "${GREEN}corriendo${NC}"
    else
        echo -e "${RED}detenido${NC}"
    fi
    
    # API
    printf "  API:           "
    if [ -f "$PROJECT_DIR/.api.pid" ] && kill -0 "$(cat "$PROJECT_DIR/.api.pid")" 2>/dev/null; then
        echo -e "${GREEN}corriendo${NC}"
    else
        echo -e "${YELLOW}no iniciada${NC}"
    fi
    
    echo ""
    echo "  Workers:"
    echo "  ─────────────────────────────────────────────────────────────"
    
    local total=0
    local running=0
    
    for pid_file in $(get_worker_pids); do
        local worker_id=$(basename "$pid_file" .pid)
        ((total++))
        
        printf "    %-12s " "$worker_id:"
        
        if is_worker_running "$pid_file"; then
            local pid=$(cat "$pid_file")
            echo -e "${GREEN}corriendo${NC} (PID: $pid)"
            ((running++))
        else
            echo -e "${RED}detenido${NC}"
        fi
    done
    
    if [ "$total" -eq 0 ]; then
        echo "    (ningún worker registrado)"
    fi
    
    echo ""
    echo "  ─────────────────────────────────────────────────────────────"
    echo "  Total: $running/$total workers activos"
    
    # Recursos del sistema
    echo ""
    echo "  Recursos del Sistema:"
    echo "  ─────────────────────────────────────────────────────────────"
    printf "    CPU:         %.1f%%\n" "$(grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}')" 2>/dev/null || echo "    CPU:         N/A"
    printf "    RAM:         %.1f%%\n" "$(free | grep Mem | awk '{print $3/$2 * 100.0}')" 2>/dev/null || echo "    RAM:         N/A"
    printf "    Chrome:      %d procesos\n" "$(pgrep -c chrome 2>/dev/null || echo 0)"
    echo ""
}

# ============================================================================
# logs - Ver logs de Workers
# ============================================================================

cmd_logs() {
    local WORKER_ID="$1"
    
    if [ -n "$WORKER_ID" ]; then
        # Log de un worker específico
        local log_file="$LOG_DIR/$WORKER_ID.log"
        if [ -f "$log_file" ]; then
            tail -f "$log_file"
        else
            log_err "Log no encontrado: $log_file"
            log_info "Workers disponibles:"
            ls -1 "$LOG_DIR"/worker-*.log 2>/dev/null | xargs -I {} basename {} .log || echo "  (ninguno)"
        fi
    else
        # Todos los logs combinados
        if ls "$LOG_DIR"/worker-*.log 1>/dev/null 2>&1; then
            tail -f "$LOG_DIR"/worker-*.log
        else
            log_info "No hay logs de workers. Iniciar con: $0 start"
        fi
    fi
}

# ============================================================================
# restart - Reiniciar Workers
# ============================================================================

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start "$@"
}

# ============================================================================
# scale - Escalar número de workers en caliente
# ============================================================================

cmd_scale() {
    local TARGET=${1:-3}
    local current=$(get_running_workers_count)
    
    load_env
    local MAX_BOTS=${MAX_CONCURRENT_BOTS:-3}
    
    echo ""
    log_info "Escalando workers: $current → $TARGET"
    
    if [ "$TARGET" -gt "$current" ]; then
        # Agregar workers
        local to_add=$((TARGET - current))
        
        source .venv/bin/activate
        mkdir -p "$PID_DIR" "$LOG_DIR"
        
        for i in $(seq 1 $to_add); do
            # Encontrar siguiente ID disponible
            local next_id=1
            while [ -f "$PID_DIR/worker-$next_id.pid" ]; do
                ((next_id++))
            done
            
            local WORKER_ID="worker-$next_id"
            local PID_FILE="$PID_DIR/$WORKER_ID.pid"
            local WORKER_LOG="$LOG_DIR/$WORKER_ID.log"
            
            export MAX_CONCURRENT_BOTS="$MAX_BOTS"
            nohup .venv/bin/python -m workers.mqtt_worker --id "$WORKER_ID" >> "$WORKER_LOG" 2>&1 &
            echo $! > "$PID_FILE"
            
            sleep 1
            if is_worker_running "$PID_FILE"; then
                log_worker "$WORKER_ID agregado"
            fi
        done
        
    elif [ "$TARGET" -lt "$current" ]; then
        # Remover workers (los últimos)
        local to_remove=$((current - TARGET))
        local removed=0
        
        for pid_file in $(get_worker_pids | sort -r); do
            if [ "$removed" -ge "$to_remove" ]; then
                break
            fi
            
            local worker_id=$(basename "$pid_file" .pid)
            if is_worker_running "$pid_file"; then
                local pid=$(cat "$pid_file")
                kill "$pid" 2>/dev/null || true
                sleep 2
                kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
                log_worker "$worker_id removido"
                ((removed++))
            fi
            rm -f "$pid_file"
        done
    else
        log_info "Ya hay $TARGET workers corriendo"
    fi
    
    echo ""
    log_ok "Escalado completado. Workers activos: $(get_running_workers_count)"
}

# ============================================================================
# Main
# ============================================================================

case ${1:-help} in
    start)
        shift
        cmd_start "$@"
        ;;
    stop)
        cmd_stop
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "$2"
        ;;
    restart)
        shift
        cmd_restart "$@"
        ;;
    scale)
        cmd_scale "$2"
        ;;
    *)
        echo ""
        echo "BrokerWiz Worker Manager"
        echo "========================"
        echo ""
        echo "Uso: $0 <comando> [opciones]"
        echo ""
        echo "Comandos:"
        echo "  start           Iniciar workers (configuración desde .env)"
        echo "  stop            Detener todos los workers"
        echo "  status          Ver estado de workers y sistema"
        echo "  logs [id]       Ver logs (todos o de un worker específico)"
        echo "  restart         Reiniciar workers"
        echo "  scale <n>       Escalar a n workers en caliente"
        echo ""
        echo "Opciones de start:"
        echo "  -n, --num-workers <n>    Número de workers (default: NUM_WORKERS del .env)"
        echo "  -b, --max-bots <n>       Max bots por worker (default: MAX_CONCURRENT_BOTS)"
        echo "  -a, --aseguradora <x>    Solo procesar una aseguradora (hdi, sura, etc.)"
        echo "  --no-persistent          Deshabilitar sesiones persistentes"
        echo ""
        echo "Ejemplos:"
        echo "  $0 start                    # Usar configuración del .env"
        echo "  $0 start -n 2 -b 4          # 2 workers × 4 bots = 8 Chrome max"
        echo "  $0 start -n 1 -b 2          # VM pequeña: 1 worker × 2 bots"
        echo "  $0 start -n 3 -a hdi        # 3 workers solo para HDI"
        echo "  $0 scale 5                  # Escalar a 5 workers en caliente"
        echo ""
        echo "Configuración en .env:"
        echo "  NUM_WORKERS=3               # Workers por defecto"
        echo "  MAX_CONCURRENT_BOTS=3       # Bots por worker por defecto"
        echo ""
        echo "Recursos por Chrome (headless): ~300-500MB RAM"
        echo "Recomendación:"
        echo "   4GB RAM → 1 worker × 2-3 bots"
        echo "   8GB RAM → 2 workers × 3-4 bots"
        echo "  16GB RAM → 3-4 workers × 4-5 bots"
        echo ""
        ;;
esac

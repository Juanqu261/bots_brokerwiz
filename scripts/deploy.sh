#!/bin/bash
#
# BrokerWiz - Deployment Script
# ==============================
#
# Automated deployment script for updates from GitHub
#
# Uso:
#   ./scripts/deploy.sh              # Deploy from main branch
#   ./scripts/deploy.sh --branch dev # Deploy from specific branch
#   ./scripts/deploy.sh --rollback   # Rollback to previous commit
#

set -e

# Directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}[✓]${NC} $1"; }
log_err() { echo -e "${RED}[✗]${NC} $1"; }
log_info() { echo -e "${YELLOW}[i]${NC} $1"; }
log_step() { echo -e "${BLUE}[→]${NC} $1"; }

cd "$PROJECT_DIR"

# ============================================================================
# Funciones
# ============================================================================

check_git() {
    if [ ! -d ".git" ]; then
        log_err "No es un repositorio Git"
        exit 1
    fi
}

backup_env() {
    if [ -f ".env" ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        log_ok "Backup de .env creado"
    fi
}

check_disk_space() {
    local available=$(df . | tail -1 | awk '{print $4}')
    local required=1048576  # 1GB en KB
    
    if [ "$available" -lt "$required" ]; then
        log_err "Espacio en disco insuficiente (disponible: $(($available/1024))MB)"
        exit 1
    fi
}

check_services_running() {
    local api_running=false
    local workers_running=false
    
    if [ -f ".api.pid" ] && kill -0 "$(cat .api.pid)" 2>/dev/null; then
        api_running=true
    fi
    
    if [ -d ".pids" ] && [ -n "$(find .pids -name 'worker-*.pid' 2>/dev/null)" ]; then
        workers_running=true
    fi
    
    echo "$api_running:$workers_running"
}

health_check() {
    local max_attempts=10
    local attempt=1
    
    log_step "Verificando salud del servicio..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            log_ok "Servicio saludable"
            return 0
        fi
        
        log_info "Intento $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    log_err "Health check falló después de $max_attempts intentos"
    return 1
}

# ============================================================================
# Comandos
# ============================================================================

cmd_deploy() {
    local branch="${1:-main}"
    
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║              BrokerWiz - Deployment                           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Pre-checks
    log_step "Verificando requisitos..."
    check_git
    check_disk_space
    
    # Guardar estado de servicios
    local services_state=$(check_services_running)
    local api_was_running=$(echo $services_state | cut -d: -f1)
    local workers_were_running=$(echo $services_state | cut -d: -f2)
    
    log_info "API corriendo: $api_was_running"
    log_info "Workers corriendo: $workers_were_running"
    
    # Backup
    log_step "Creando backups..."
    backup_env
    
    # Guardar commit actual para rollback
    local current_commit=$(git rev-parse HEAD)
    echo "$current_commit" > .last_deploy_commit
    
    # Pull código
    log_step "Actualizando código desde GitHub..."
    git fetch origin
    
    if ! git diff --quiet HEAD "origin/$branch"; then
        log_info "Cambios detectados, actualizando..."
        git reset --hard "origin/$branch"
        log_ok "Código actualizado a origin/$branch"
    else
        log_info "Ya estás en la última versión"
    fi
    
    # Verificar cambios en requirements.txt
    if git diff "$current_commit" HEAD --name-only | grep -q "requirements.txt"; then
        log_step "Actualizando dependencias..."
        source .venv/bin/activate
        pip install -r requirements.txt --quiet --upgrade
        log_ok "Dependencias actualizadas"
    else
        log_info "Sin cambios en dependencias"
    fi
    
    # Reiniciar servicios si estaban corriendo
    if [ "$api_was_running" = "true" ]; then
        log_step "Reiniciando API..."
        ./scripts/api.sh restart -d
        log_ok "API reiniciada"
    fi
    
    if [ "$workers_were_running" = "true" ]; then
        log_step "Reiniciando workers..."
        ./scripts/worker.sh restart
        log_ok "Workers reiniciados"
    fi
    
    # Health check
    if [ "$api_was_running" = "true" ]; then
        if health_check; then
            log_ok "Deployment exitoso"
        else
            log_err "Health check falló. Considera hacer rollback."
            exit 1
        fi
    fi
    
    # Resumen
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    log_ok "Deployment completado"
    echo ""
    echo "  Commit anterior: ${current_commit:0:8}"
    echo "  Commit actual:   $(git rev-parse HEAD | cut -c1-8)"
    echo "  Branch:          $branch"
    echo ""
    echo "Para rollback: ./scripts/deploy.sh --rollback"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
}

cmd_rollback() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║              BrokerWiz - Rollback                             ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    
    if [ ! -f ".last_deploy_commit" ]; then
        log_err "No hay información de deployment anterior"
        exit 1
    fi
    
    local previous_commit=$(cat .last_deploy_commit)
    local current_commit=$(git rev-parse HEAD)
    
    log_info "Commit actual:   ${current_commit:0:8}"
    log_info "Rollback a:      ${previous_commit:0:8}"
    echo ""
    
    read -p "¿Confirmar rollback? [y/N] " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Rollback cancelado"
        exit 0
    fi
    
    # Guardar estado de servicios
    local services_state=$(check_services_running)
    local api_was_running=$(echo $services_state | cut -d: -f1)
    local workers_were_running=$(echo $services_state | cut -d: -f2)
    
    # Rollback
    log_step "Haciendo rollback..."
    git reset --hard "$previous_commit"
    log_ok "Código restaurado"
    
    # Restaurar .env si existe backup
    if [ -f ".env.backup" ]; then
        log_step "¿Restaurar .env desde backup? [y/N]"
        read -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.backup .env
            log_ok ".env restaurado"
        fi
    fi
    
    # Reinstalar dependencias
    log_step "Reinstalando dependencias..."
    source .venv/bin/activate
    pip install -r requirements.txt --quiet
    log_ok "Dependencias instaladas"
    
    # Reiniciar servicios
    if [ "$api_was_running" = "true" ]; then
        log_step "Reiniciando API..."
        ./scripts/api.sh restart -d
    fi
    
    if [ "$workers_were_running" = "true" ]; then
        log_step "Reiniciando workers..."
        ./scripts/worker.sh restart
    fi
    
    # Health check
    if [ "$api_was_running" = "true" ]; then
        health_check
    fi
    
    log_ok "Rollback completado"
}

cmd_status() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║              BrokerWiz - Deployment Status                    ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Git info
    echo "Git:"
    echo "  Branch:        $(git branch --show-current)"
    echo "  Commit:        $(git rev-parse HEAD | cut -c1-8)"
    echo "  Last deploy:   $([ -f .last_deploy_commit ] && cat .last_deploy_commit | cut -c1-8 || echo 'N/A')"
    echo ""
    
    # Services
    echo "Services:"
    ./scripts/worker.sh status
    echo ""
    
    # Disk space
    echo "Disk Space:"
    df -h . | tail -1 | awk '{print "  Available:     " $4 " (" $5 " used)"}'
    echo ""
    
    # Recent commits
    echo "Recent Commits:"
    git log --oneline -5 | sed 's/^/  /'
    echo ""
}

# ============================================================================
# Main
# ============================================================================

case ${1:-deploy} in
    deploy)
        cmd_deploy "${2:-main}"
        ;;
    rollback|revert)
        cmd_rollback
        ;;
    status|info)
        cmd_status
        ;;
    *)
        echo "Uso: $0 <comando> [opciones]"
        echo ""
        echo "Comandos:"
        echo "  deploy [branch]    Deploy desde GitHub (default: main)"
        echo "  rollback           Rollback al commit anterior"
        echo "  status             Ver estado del deployment"
        echo ""
        echo "Ejemplos:"
        echo "  $0 deploy              # Deploy desde main"
        echo "  $0 deploy dev          # Deploy desde branch dev"
        echo "  $0 rollback            # Rollback"
        echo "  $0 status              # Ver estado"
        echo ""
        ;;
esac

#!/bin/bash
#
# BrokerWiz - Setup inicial del proyecto
# ======================================
#
# Uso:
#   ./scripts/setup.sh
#

set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; }
log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

# Directorio del proyecto (donde está este script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              BrokerWiz - Setup Inicial                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# 1. Verificar Python
# ============================================================================

log_info "Verificando Python..."

if command -v python3.12 &>/dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    log_err "Python 3 no encontrado. Instalar con: sudo apt install python3.12 python3.12-venv"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+')
log_ok "Python encontrado: $($PYTHON_CMD --version)"

# ============================================================================
# 2. Crear entorno virtual
# ============================================================================

log_info "Configurando entorno virtual..."

if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
    log_ok "Entorno virtual creado en .venv/"
else
    log_ok "Entorno virtual ya existe"
fi

# Activar venv
source .venv/bin/activate

# ============================================================================
# 3. Instalar dependencias
# ============================================================================

log_info "Instalando dependencias..."

pip install --upgrade pip -q
pip install -r requirements.txt -q

# Extras para producción
pip install uvloop httptools -q 2>/dev/null || true

log_ok "Dependencias instaladas"

# ============================================================================
# 4. Configurar .env
# ============================================================================

log_info "Verificando configuración..."

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_info "Archivo .env creado desde .env.example"
        log_info "IMPORTANTE: Edita .env con tus valores de producción"
    else
        log_err ".env.example no encontrado"
    fi
else
    log_ok ".env ya existe"
fi

# ============================================================================
# 5. Crear directorios necesarios
# ============================================================================

log_info "Creando directorios..."

mkdir -p logs storage/screenshots storage/temp

log_ok "Directorios creados"

# ============================================================================
# 6. Verificar instalación
# ============================================================================

log_info "Verificando instalación..."

# Test import
if python -c "from app.main import app; print('OK')" &>/dev/null; then
    log_ok "Módulos importan correctamente"
else
    log_err "Error importando módulos. Revisar dependencias."
    exit 1
fi

deactivate

# ============================================================================
# Resumen
# ============================================================================

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                    Setup Completado"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Próximos pasos:"
echo ""
echo "  1. Configurar Mosquitto:"
echo "     sudo ./scripts/mosquitto.sh setup"
echo ""
echo "  2. Editar .env con valores de producción:"
echo "     nano .env"
echo ""
echo "  3. Iniciar API:"
echo "     ./scripts/api.sh start"
echo ""

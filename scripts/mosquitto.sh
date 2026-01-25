#!/bin/bash
#
# BrokerWiz - Setup de Mosquitto MQTT con persistencia
# =====================================================
#
# Uso:
#   sudo ./scripts/mosquitto.sh setup       # Configurar Mosquitto
#   ./scripts/mosquitto.sh healthcheck      # Verificar estado del broker
#   ./scripts/mosquitto.sh test             # Publicar mensaje de prueba
#   ./scripts/mosquitto.sh version          # Verificar versión y soporte MQTT 5
#   ./scripts/mosquitto.sh test-shared [n]  # Probar Shared Subscriptions con n mensajes
#

set -e

# Detectar directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

MOSQUITTO_DATA="/var/lib/mosquitto"
BROKERWIZ_LOGS="${PROJECT_DIR}/logs"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; }
log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

# ============================================================================
# setup - Configurar Mosquitto con persistencia
# ============================================================================

cmd_setup() {
    if [ "$EUID" -ne 0 ]; then
        log_err "Requiere sudo: sudo $0 setup"
        exit 1
    fi

    log_info "Instalando Mosquitto..."
    apt-get update -qq
    apt-get install -y -qq mosquitto mosquitto-clients

    log_info "Configurando persistencia..."
    mkdir -p $MOSQUITTO_DATA "$BROKERWIZ_LOGS"
    chown mosquitto:mosquitto $MOSQUITTO_DATA
    chmod 755 "$BROKERWIZ_LOGS"

    cat > /etc/mosquitto/conf.d/brokerwiz.conf <<EOF
# ============================================================================
# BrokerWiz - Mosquitto MQTT Broker Configuration
# ============================================================================
# Arquitectura: API → MQTT → Workers (Shared Subscriptions)
# Requiere: Mosquitto 2.0+ para soporte de MQTT 5 y Shared Subscriptions
# ============================================================================

# ------------------------------------------------------------------------------
# Listener principal
# ------------------------------------------------------------------------------
listener 1883 0.0.0.0
allow_anonymous true

# ------------------------------------------------------------------------------
# Persistencia - Recuperar mensajes tras reinicio del broker
# ------------------------------------------------------------------------------
persistence true
persistence_location ${MOSQUITTO_DATA}/
persistence_file mosquitto.db
autosave_interval 60

# ------------------------------------------------------------------------------
# Límites de colas y mensajes
# ------------------------------------------------------------------------------
# max_queued_messages: Mensajes en cola por cliente (QoS 1/2)
#   - Afecta workers desconectados con sesión persistente
#   - 10000 permite ~10k tareas pendientes por worker
max_queued_messages 10000

# max_inflight_messages: Mensajes simultáneos en tránsito (sin ACK)
#   - Para workers Selenium que procesan secuencialmente, 20 es suficiente
max_inflight_messages 20

# max_queued_bytes: Límite de memoria por cola (0 = sin límite de bytes)
max_queued_bytes 0

# ------------------------------------------------------------------------------
# Timeouts y Keep-Alive
# ------------------------------------------------------------------------------
# keepalive_interval: Segundos entre pings cliente-broker (0 = usar del cliente)
#keepalive_interval 60

# persistent_client_expiration: Tiempo para limpiar sesiones huérfanas
#   - Workers con client_id fijo mantienen sesión entre reinicios
#   - 1d = limpiar si no reconecta en 1 día
persistent_client_expiration 1d

# ------------------------------------------------------------------------------
# Logs
# ------------------------------------------------------------------------------
log_dest file ${BROKERWIZ_LOGS}/mosquitto.log
log_dest stdout
log_type error
log_type warning
log_type notice
log_type information
log_type subscribe
log_type unsubscribe
log_timestamp true
log_timestamp_format %Y-%m-%d %H:%M:%S

# ------------------------------------------------------------------------------
# Notas sobre Shared Subscriptions (MQTT 5)
# ------------------------------------------------------------------------------
# Mosquitto 2.0+ soporta shared subscriptions automáticamente.
# Los workers se suscriben a: \$share/workers/bots/queue/+
# El broker distribuye mensajes round-robin entre workers del grupo.
# No requiere configuración adicional, solo Mosquitto 2.x.
# ------------------------------------------------------------------------------
EOF

    # Configurar logrotate para Mosquitto (rotación diaria, mantener 1 día)
    cat > /etc/logrotate.d/brokerwiz-mosquitto <<EOF
${BROKERWIZ_LOGS}/mosquitto.log {
    daily
    rotate 1
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    dateext
    dateformat -%Y-%m-%d
}
EOF

    # Dar permisos a mosquitto para escribir en logs
    touch "$BROKERWIZ_LOGS/mosquitto.log"
    chown mosquitto:mosquitto "$BROKERWIZ_LOGS/mosquitto.log"

    systemctl enable mosquitto
    systemctl restart mosquitto

    log_ok "Mosquitto configurado"
    log_ok "Logs en: $BROKERWIZ_LOGS/mosquitto.log"
    echo ""
    cmd_healthcheck
}

# ============================================================================
# healthcheck - Verificar estado del broker
# ============================================================================

cmd_healthcheck() {
    echo "═══════════════════════════════════════"
    echo "       Mosquitto Health Check"
    echo "═══════════════════════════════════════"
    echo ""

    # Estado del servicio
    printf "Servicio:              "
    if systemctl is-active mosquitto &>/dev/null; then
        echo -e "${GREEN}activo${NC}"
    else
        echo -e "${RED}inactivo${NC}"
        exit 1
    fi

    # Clientes conectados
    printf "Clientes conectados:   "
    mosquitto_sub -t '$SYS/broker/clients/connected' -C 1 -W 2 2>/dev/null || echo "N/A"

    # Mensajes almacenados (persistidos)
    printf "Mensajes almacenados:  "
    mosquitto_sub -t '$SYS/broker/messages/stored' -C 1 -W 2 2>/dev/null || echo "N/A"

    # Mensajes recibidos
    printf "Mensajes recibidos:    "
    mosquitto_sub -t '$SYS/broker/messages/received' -C 1 -W 2 2>/dev/null || echo "N/A"

    # Uptime
    printf "Uptime (segundos):     "
    mosquitto_sub -t '$SYS/broker/uptime' -C 1 -W 2 2>/dev/null || echo "N/A"

    echo ""
}

# ============================================================================
# test - Publicar mensaje de prueba
# ============================================================================

cmd_test() {
    local ASEGURADORA=${1:-hdi}
    local JOB_ID="test-$(date +%s)"
    local TOPIC="bots/queue/$ASEGURADORA"
    local PAYLOAD="{\"job_id\":\"$JOB_ID\",\"timestamp\":\"$(date -Iseconds)\",\"payload\":{\"test\":true}}"

    log_info "Publicando mensaje de prueba..."
    echo "  Topic:   $TOPIC"
    echo "  Payload: $PAYLOAD"
    echo ""

    if mosquitto_pub -t "$TOPIC" -m "$PAYLOAD" -q 1; then
        log_ok "Mensaje publicado con QoS 1"
    else
        log_err "Error publicando mensaje"
        exit 1
    fi
}

# ============================================================================
# version - Verificar versión y soporte de MQTT 5
# ============================================================================

cmd_version() {
    echo "═══════════════════════════════════════"
    echo "     Mosquitto Version & Features"
    echo "═══════════════════════════════════════"
    echo ""
    
    # Versión
    printf "Versión instalada:     "
    MOSQUITTO_VERSION=$(mosquitto -h 2>&1 | head -1 | grep -oP '\d+\.\d+\.\d+' || echo "N/A")
    echo "$MOSQUITTO_VERSION"
    
    # Verificar soporte MQTT 5 (Mosquitto 2.0+)
    printf "Soporte MQTT 5:        "
    MAJOR_VERSION=$(echo "$MOSQUITTO_VERSION" | cut -d. -f1)
    if [ "$MAJOR_VERSION" -ge 2 ] 2>/dev/null; then
        echo -e "${GREEN}Sí (v2.0+)${NC}"
        echo ""
        echo -e "${GREEN}✓${NC} Shared Subscriptions soportadas"
        echo "  Workers pueden suscribirse a: \$share/workers/bots/queue/+"
    else
        echo -e "${RED}No (requiere v2.0+)${NC}"
        echo ""
        log_err "Shared Subscriptions NO disponibles"
        log_info "Actualizar Mosquitto: apt-get install mosquitto=2.0*"
    fi
    echo ""
}

# ============================================================================
# test-shared - Probar distribución con Shared Subscriptions
# ============================================================================

cmd_test_shared() {
    local NUM_MESSAGES=${1:-5}
    local TOPIC="bots/queue/hdi"
    local SHARED_TOPIC="\$share/workers/$TOPIC"
    
    echo "═══════════════════════════════════════"
    echo "   Test: Shared Subscriptions"
    echo "═══════════════════════════════════════"
    echo ""
    echo "Este test verifica que los mensajes se distribuyan"
    echo "entre múltiples suscriptores (round-robin)."
    echo ""
    echo "Pasos manuales para verificar:"
    echo ""
    echo "1. Abre 2-3 terminales y en cada una ejecuta:"
    echo -e "   ${YELLOW}mosquitto_sub -t '\$share/workers/$TOPIC' -v${NC}"
    echo ""
    echo "2. En otra terminal, publica mensajes:"
    echo -e "   ${YELLOW}for i in 1 2 3 4 5; do mosquitto_pub -t '$TOPIC' -m \"Mensaje \$i\"; done${NC}"
    echo ""
    echo "3. Observa que cada terminal recibe mensajes diferentes (round-robin)"
    echo ""
    
    read -p "¿Publicar $NUM_MESSAGES mensajes de prueba ahora? [y/N] " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Publicando $NUM_MESSAGES mensajes a $TOPIC..."
        for i in $(seq 1 $NUM_MESSAGES); do
            mosquitto_pub -t "$TOPIC" -m "{\"job_id\":\"shared-test-$i\",\"seq\":$i}" -q 1
            echo "  → Mensaje $i publicado"
            sleep 0.2
        done
        log_ok "Mensajes publicados. Verifica distribución en los suscriptores."
    fi
}

# ============================================================================
# Main
# ============================================================================

case ${1:-help} in
    setup)
        cmd_setup
        ;;
    healthcheck|health|status)
        cmd_healthcheck
        ;;
    version|ver)
        cmd_version
        ;;
    test)
        cmd_test "${2:-hdi}"
        ;;
    test-shared)
        cmd_test_shared "${2:-5}"
        ;;
    *)
        echo "Uso: $0 <comando>"
        echo ""
        echo "Comandos:"
        echo "  setup           Instalar y configurar Mosquitto (requiere sudo)"
        echo "  healthcheck     Verificar estado del broker"
        echo "  version         Verificar versión y soporte MQTT 5"
        echo "  test [aseg]     Publicar mensaje de prueba (default: hdi)"
        echo "  test-shared [n] Probar Shared Subscriptions con n mensajes"
        echo ""
        echo "Arquitectura BrokerWiz:"
        echo "  API publica a:        bots/queue/{aseguradora}"
        echo "  Workers escuchan:     \$share/workers/bots/queue/+"
        echo "  Distribución:         Round-robin (1 mensaje → 1 worker)"
        echo ""
        ;;
esac

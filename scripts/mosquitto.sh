#!/bin/bash
#
# BrokerWiz - Setup de Mosquitto MQTT con persistencia
# =====================================================
#
# Uso:
#   sudo ./scripts/mosquitto.sh setup       # Configurar Mosquitto
#   ./scripts/mosquitto.sh healthcheck      # Verificar estado del broker
#   ./scripts/mosquitto.sh test             # Publicar mensaje de prueba
#

set -e

MOSQUITTO_DATA="/var/lib/mosquitto"

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
    mkdir -p $MOSQUITTO_DATA /var/log/mosquitto
    chown mosquitto:mosquitto $MOSQUITTO_DATA /var/log/mosquitto

    cat > /etc/mosquitto/conf.d/brokerwiz.conf <<EOF
# BrokerWiz - Mosquitto con persistencia
listener 1883 0.0.0.0
allow_anonymous true

# Persistencia
persistence true
persistence_location ${MOSQUITTO_DATA}/
persistence_file mosquitto.db
autosave_interval 60

# Colas
max_queued_messages 1000
max_inflight_messages 100

# Logs
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_timestamp true
EOF

    systemctl enable mosquitto
    systemctl restart mosquitto

    log_ok "Mosquitto configurado con persistencia en $MOSQUITTO_DATA"
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
# Main
# ============================================================================

case ${1:-help} in
    setup)
        cmd_setup
        ;;
    healthcheck|health|status)
        cmd_healthcheck
        ;;
    test)
        cmd_test "${2:-hdi}"
        ;;
    *)
        echo "Uso: $0 <comando>"
        echo ""
        echo "Comandos:"
        echo "  setup        Instalar y configurar Mosquitto (requiere sudo)"
        echo "  healthcheck  Verificar estado del broker"
        echo "  test [aseg]  Publicar mensaje de prueba (default: hdi)"
        echo ""
        ;;
esac

#!/bin/bash
# Script de deploy a VM Linux remota
# Uso: ./scripts/deploy.sh brokerwiz@192.168.1.100

TARGET_HOST=${1:-brokerwiz@localhost}
APP_PATH="/opt/brokerwiz"

if [ -z "$1" ]; then
    echo "Uso: $0 <usuario@host>"
    echo "   Ejemplo: $0 brokerwiz@192.168.1.100"
    exit 1
fi

echo "=========================================="
echo "Desplegando BrokerWiz a $TARGET_HOST"
echo "=========================================="

# Verificar conectividad
if ! ssh -q $TARGET_HOST "exit"; then
    echo "No se puede conectar a $TARGET_HOST"
    exit 1
fi

# 1. Crear directorios
echo "Preparando directorios en servidor remoto..."
ssh $TARGET_HOST "mkdir -p $APP_PATH"

# 2. Copiar código (excluyendo archivos innecesarios)
echo "Sincronizando código..."
rsync -avz --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='logs/*' \
    --exclude='storage/*' \
    ./ $TARGET_HOST:$APP_PATH/

# 3. Instalar dependencias Python
echo "Instalando dependencias de Python..."
ssh $TARGET_HOST "source $APP_PATH/venv/bin/activate && pip install -r $APP_PATH/requirements.txt"

# 4. Reiniciar servicios
echo "Reiniciando servicios..."
ssh $TARGET_HOST "sudo systemctl restart brokerwiz-api brokerwiz-workers"

# 5. Verificar estado
echo ""
echo "=========================================="
echo "Deploy completado"
echo "=========================================="
echo ""
echo "Ver estado de servicios:"
echo "   ssh $TARGET_HOST 'sudo systemctl status brokerwiz-api brokerwiz-workers'"
echo ""
echo "Ver logs:"
echo "   ssh $TARGET_HOST 'sudo journalctl -u brokerwiz-api -f'"
echo "   ssh $TARGET_HOST 'sudo journalctl -u brokerwiz-workers -f'"
echo ""

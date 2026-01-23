#!/bin/bash
# Setup inicial en VM de Linux para BrokerWiz
# Este script instala todas las dependencias necesarias

set -e

echo "=========================================="
echo "   Iniciando setup de BrokerWiz en VM"
echo "=========================================="

# Actualizar repositorios
echo "Actualizando repositorios del sistema..."
sudo apt-get update
sudo apt-get upgrade -y

# Instalar Python y dependencias del sistema
echo "Instalando Python 3.12 y dependencias del sistema..."
sudo apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    mosquitto \
    mosquitto-clients \
    build-essential \
    curl \
    git \
    supervisor

# Crear usuario brokerwiz (si no existe)
if ! id "brokerwiz" &>/dev/null; then
    echo "Creando usuario brokerwiz..."
    sudo useradd -m -s /bin/bash brokerwiz
else
    echo "Usuario brokerwiz ya existe"
fi

# Crear directorios de la aplicación
echo "Creando estructura de directorios..."
sudo mkdir -p /opt/brokerwiz
sudo mkdir -p /opt/brokerwiz/logs
sudo mkdir -p /opt/brokerwiz/storage
sudo mkdir -p /opt/brokerwiz/mosquitto/config

# Permisos iniciales
sudo chown -R brokerwiz:brokerwiz /opt/brokerwiz
sudo chmod -R 755 /opt/brokerwiz

# Crear virtual environment
echo "Creando virtual environment de Python..."
sudo -u brokerwiz python3.12 -m venv /opt/brokerwiz/venv

# Activar venv e instalar dependencias de Python
echo "Instalando dependencias de Python..."
sudo -u brokerwiz bash -c 'source /opt/brokerwiz/venv/bin/activate && \
    pip install --upgrade pip setuptools wheel'

# Nota: requirements.txt debe estar en el repo
echo "Asegúrate de copiar el código del repositorio a /opt/brokerwiz"
echo "Luego ejecuta:"
echo "    sudo -u brokerwiz bash -c 'source /opt/brokerwiz/venv/bin/activate && pip install -r /opt/brokerwiz/requirements.txt'"

# Configurar Mosquitto
echo "Configurando Mosquitto..."
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Crear systemd services
echo "Creando systemd services..."
sudo tee /etc/systemd/system/brokerwiz-api.service > /dev/null <<EOF
[Unit]
Description=BrokerWiz API FastAPI Service
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=brokerwiz
WorkingDirectory=/opt/brokerwiz
Environment="PATH=/opt/brokerwiz/venv/bin"
EnvironmentFile=/opt/brokerwiz/.env
ExecStart=/opt/brokerwiz/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/brokerwiz-workers.service > /dev/null <<EOF
[Unit]
Description=BrokerWiz MQTT Workers
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=brokerwiz
WorkingDirectory=/opt/brokerwiz
Environment="PATH=/opt/brokerwiz/venv/bin"
EnvironmentFile=/opt/brokerwiz/.env
ExecStart=/bin/bash -c 'for i in \$(seq 1 \${NUM_WORKERS:-3}); do /opt/brokerwiz/venv/bin/python -m workers.tasks & done; wait'
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Recargar systemd
sudo systemctl daemon-reload

# Mostrar resumen
echo ""
echo "=========================================="
echo "Setup completado"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. Copiar código a /opt/brokerwiz"
echo "2. Copiar .env a /opt/brokerwiz/.env"
echo "3. Instalar requerimientos: sudo -u brokerwiz bash -c 'source /opt/brokerwiz/venv/bin/activate && pip install -r /opt/brokerwiz/requirements.txt'"
echo "4. Copiar configuración de Mosquitto"
echo "5. Habilitar servicios:"
echo "   sudo systemctl enable brokerwiz-api brokerwiz-workers"
echo "   sudo systemctl start brokerwiz-api brokerwiz-workers"
echo ""
echo "Ver logs:"
echo "   sudo journalctl -u brokerwiz-api -f"
echo "   sudo journalctl -u brokerwiz-workers -f"
echo ""

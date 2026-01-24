# BrokerWiz Bot Automation Server

Sistema de automatización de bots Selenium para cotización de seguros, con API REST y cola de tareas MQTT.

## Quick Start

```bash
# 1. Clonar repo
git clone <repo> /opt/brokerwiz
cd /opt/brokerwiz

# 2. Setup inicial (una vez)
chmod +x scripts/*.sh
./scripts/setup.sh

# 3. Configurar Mosquitto (una vez)
sudo ./scripts/mosquitto.sh setup

# 4. Editar .env para producción
nano .env
# Cambiar: API_HOST=127.0.0.1, ENVIRONMENT=production, API_KEY=<seguro>

# 5. Iniciar API
./scripts/api.sh start -d    # Background (producción)
./scripts/api.sh start       # Foreground (desarrollo)

# 6. Verificar
./scripts/api.sh status
curl http://127.0.0.1:8000/health
```

## Agregar servicio api a nginx
```
# Agregar a /etc/nginx/sites-available/default 
# O crear /etc/nginx/sites-available/brokerwiz

server {
    listen 80;
    server_name orquestadorbots.brokerwiz.co;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
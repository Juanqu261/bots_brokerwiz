# Multi-stage Dockerfile para BrokerWiz Bot Automation Server

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /app

# Instalar dependencias del sistema para build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Crear venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Instalar Chromium y ChromeDriver (para Selenium)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium-browser \
    chromium-driver \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar venv del builder
COPY --from=builder /opt/venv /opt/venv

# Configurar PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copiar código
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs storage

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Exponer puertos
EXPOSE 8000 8001

# Comando por defecto (ejecutar app + workers)
CMD ["/app/docker-entrypoint.sh"]

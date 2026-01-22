#!/bin/bash
# Generar certificados TLS para MQTT Mosquitto
# Uso: ./generate_certs.sh

set -e

CERT_DIR="./certs"
DAYS=365

echo "Generando certificados TLS para MQTT..."
mkdir -p "$CERT_DIR"

# CA
echo "Crear Autoridad Certificadora..."

openssl genrsa -out "$CERT_DIR/ca.key" 2048
openssl req -new -x509 -days $DAYS -key "$CERT_DIR/ca.key" -out "$CERT_DIR/ca.crt" \
  -subj "/CN=BrokerWiz-CA/O=BrokerWiz/C=CO"

echo "CA creada: $CERT_DIR/ca.crt"

# Certificado Servidor
echo "Crear Certificado Servidor..."

openssl genrsa -out "$CERT_DIR/server.key" 2048
openssl req -new -key "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" \
  -subj "/CN=mosquitto/O=BrokerWiz/C=CO"

# Firmar con CA
openssl x509 -req -in "$CERT_DIR/server.csr" \
  -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
  -CAcreateserial -out "$CERT_DIR/server.crt" -days $DAYS

echo "Certificado servidor: $CERT_DIR/server.crt"

# Certificado Cliente (Autenticación Mutua Opcional)
echo ""
echo "Crear Certificado Cliente..."

openssl genrsa -out "$CERT_DIR/client.key" 2048
openssl req -new -key "$CERT_DIR/client.key" -out "$CERT_DIR/client.csr" \
  -subj "/CN=broker-wiz-api/O=BrokerWiz/C=CO"

# Firmar con CA
openssl x509 -req -in "$CERT_DIR/client.csr" \
  -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
  -CAcreateserial -out "$CERT_DIR/client.crt" -days $DAYS

echo "Certificado cliente: $CERT_DIR/client.crt"

# Limpiar archivos temporales
echo ""
echo "Limpiando archivos temporales..."

rm -f "$CERT_DIR/server.csr" "$CERT_DIR/client.csr" "$CERT_DIR/ca.srl"
echo "Archivos temporales eliminados."

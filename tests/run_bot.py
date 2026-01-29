#!/usr/bin/env python
"""
Script para ejecutar un bot específico de forma aislada.

python -m tests.run_bot sbs
python -m tests.run_bot hdi
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from mosquitto.mqtt_service import configure_event_loop
from workers.mqtt_worker import get_bot_class, BOT_REGISTRY

# Cargar variables de entorno
load_dotenv()

# Configurar event loop para Windows
configure_event_loop()

# Payloads de prueba - EXACTAMENTE como en bot_executor.py
BOT_PAYLOADS = {
    "sbs": {
        "in_strIDSolicitudAseguradora": "u68KETrjE6wdyrz5oa9o2",
        "in_strTipoIdentificacionAsesorUsuario": "string",
        "in_strUsuarioAsesor": os.getenv("SBS_USUARIO"),
        "in_strContrasenaAsesor": os.getenv("SBS_CONTRASENA"),
        "in_strTipoDoc": "string",
        "in_strNumDoc": "8102331",
        "in_strEmail": "prueba@gmail.com",
        "in_strCelular": "3598467889",
        "in_strPlaca": "JIX179",
        "in_strKmVehiculo": "string",
        "in_strCodigoFasecolda": "string",
        "in_strModelo": "string",
        "in_strPlan": [
            "string"
        ]
    },
    "hdi": {
        "in_strIDSolicitudAseguradora": "TEST-HDI-001",
        "in_strNumDoc": "1234567890",
        "in_strPlaca": "ABC123",
        "in_strCelular": "3001234567",
        "in_strEmail": "test@mail.com",
        "in_strPlan": ["PREMIUM"],
    },
}


async def main():
    if len(sys.argv) < 2:
        print(f"Aseguradoras disponibles: {', '.join(BOT_REGISTRY.keys())}")
        sys.exit(1)
    
    aseguradora = sys.argv[1].lower()
    
    # Validar que la aseguradora existe
    if aseguradora not in BOT_REGISTRY:
        print(f"Error: Aseguradora '{aseguradora}' no encontrada")
        print(f"Disponibles: {', '.join(BOT_REGISTRY.keys())}")
        sys.exit(1)
    
    # Obtener clase del bot
    bot_class = get_bot_class(aseguradora)
    
    # Obtener payload
    payload = BOT_PAYLOADS.get(aseguradora, {})
    if not payload:
        print(f"Error: No hay payload de prueba para {aseguradora}")
        sys.exit(1)
    
    # Generar job_id
    job_id = f"test-{aseguradora}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"\n{'='*60}")
    print(f"Ejecutando bot: {aseguradora.upper()}")
    print(f"Job ID: {job_id}")
    print(f"{'='*60}\n")
    
    # Instanciar y ejecutar bot
    bot = bot_class(job_id=job_id, payload=payload)
    
    try:
        async with bot:
            success = await bot.run()
            
            if success:
                print(f"\n✓ Bot completado exitosamente")
                sys.exit(0)
            else:
                print(f"\n✗ Bot completado con errores")
                sys.exit(1)
    
    except Exception as e:
        print(f"\n✗ Error ejecutando bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

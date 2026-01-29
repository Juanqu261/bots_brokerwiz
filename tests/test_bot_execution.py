"""
Test de ejecución de bots - Prueba el flujo completo de un bot sin servicios externos.

Uso:
    # Ejecutar bot SBS
    python -m pytest tests/test_bot_execution.py::test_execute_bot[sbs] -v -s
    
    # Ejecutar bot HDI
    python -m pytest tests/test_bot_execution.py::test_execute_bot[hdi] -v -s
    
    # Ejecutar todos los bots
    python -m pytest tests/test_bot_execution.py::test_execute_bot -v -s

Notas:
    - Requiere credenciales en el payload
    - Ejecuta el bot completo
    - Genera logs en logs/bots/{aseguradora}/{job_id}/
    - Captura screenshots en caso de error
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime

from workers.mqtt_worker import BOT_REGISTRY, get_bot_class
from mosquitto.mqtt_service import configure_event_loop

# Configurar event loop para Windows
configure_event_loop()


# Payloads de prueba para cada bot
BOT_TEST_PAYLOADS = {
    "sbs": {
        "in_strIDSolicitudAseguradora": "TEST-SBS-001",
        "in_strNumDoc": "8102331",
        "in_strPlaca": "JIX179",
        "in_strCelular": "3598467889",
        "in_strEmail": "prueba@gmail.com",
        "in_strPlan": "PREMIUM",
        "in_strUsuarioAsesor": "dseguroltda@gmail.com",
        "in_strContrasenaAsesor": "SBSseguros2026+",
        "in_strAPIKey2Captcha": "",  # Agregar si se tiene
    },
    "hdi": {
        "in_strIDSolicitudAseguradora": "TEST-HDI-001",
        "in_strNumDoc": "1234567890",
        "in_strPlaca": "ABC123",
        "in_strCelular": "3001234567",
        "in_strEmail": "test@mail.com",
        "in_strPlan": "PREMIUM",
        # Agregar credenciales específicas de HDI
    },
}


@pytest.fixture(params=list(BOT_REGISTRY.keys()))
def aseguradora(request):
    """Fixture que proporciona cada aseguradora registrada."""
    return request.param


@pytest.mark.asyncio
async def test_execute_bot(aseguradora):
    """
    Ejecutar bot específico y validar flujo completo.
    
    Args:
        aseguradora: Nombre de la aseguradora (ej: "sbs", "hdi")
    """
    # Obtener clase del bot
    bot_class = get_bot_class(aseguradora)
    assert bot_class is not None, f"Bot {aseguradora} no encontrado"
    
    # Obtener payload de prueba
    payload = BOT_TEST_PAYLOADS.get(aseguradora, {})
    if not payload:
        pytest.skip(f"No hay payload de prueba para {aseguradora}")
    
    # Generar job_id único
    job_id = f"test-{aseguradora}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"\n{'='*60}")
    print(f"Ejecutando bot: {aseguradora.upper()}")
    print(f"Job ID: {job_id}")
    print(f"{'='*60}\n")
    
    # Instanciar bot
    bot = bot_class(job_id=job_id, payload=payload)
    
    # Validar que el bot se instanció correctamente
    assert bot.bot_id == aseguradora
    assert bot.job_id == job_id
    assert bot.logger is not None
    
    print(f"✓ Bot instanciado correctamente")
    print(f"  - Bot ID: {bot.bot_id}")
    print(f"  - Job ID: {bot.job_id}")
    print(f"  - Logger: {bot.logger.name}")
    print(f"  - Log dir: {bot._bot_logger.execution_dir}\n")
    
    # Ejecutar bot con context manager (setup/teardown automático)
    try:
        async with bot:
            print(f"✓ Driver inicializado")
            print(f"  - Screenshots dir: {bot._bot_logger.screenshots_dir}\n")
            
            # Ejecutar flujo del bot
            print(f"Iniciando flujo del bot...\n")
            success = await bot.run()
            
            # Validar resultado
            if success:
                print(f"\n✓ Bot completado exitosamente")
                assert True
            else:
                print(f"\n✗ Bot completado con errores")
                assert False, "Bot retornó False"
    
    except Exception as e:
        print(f"\n✗ Error ejecutando bot: {e}")
        raise
    
    finally:
        # Mostrar información de logs
        log_file = bot._bot_logger.log_file
        screenshots_dir = bot._bot_logger.screenshots_dir
        
        print(f"\n{'='*60}")
        print(f"Información de ejecución:")
        print(f"{'='*60}")
        print(f"Log file: {log_file}")
        print(f"Log exists: {log_file.exists()}")
        
        if log_file.exists():
            print(f"Log size: {log_file.stat().st_size} bytes")
            print(f"\nÚltimas líneas del log:")
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print(f"  {line.rstrip()}")
        
        print(f"\nScreenshots dir: {screenshots_dir}")
        if screenshots_dir.exists():
            screenshots = list(screenshots_dir.glob("*.png"))
            print(f"Screenshots capturados: {len(screenshots)}")
            for screenshot in screenshots:
                print(f"  - {screenshot.name}")
        
        print(f"{'='*60}\n")


@pytest.mark.asyncio
async def test_execute_bot_sbs_only():
    """
    Test específico para ejecutar solo el bot SBS.
    
    Útil para debugging de un bot específico.
    """
    aseguradora = "sbs"
    
    # Obtener clase del bot
    bot_class = get_bot_class(aseguradora)
    assert bot_class is not None
    
    # Payload con credenciales reales
    payload = BOT_TEST_PAYLOADS["sbs"]
    
    # Generar job_id
    job_id = f"test-sbs-manual-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"\n{'='*60}")
    print(f"TEST MANUAL - BOT SBS")
    print(f"{'='*60}")
    print(f"Job ID: {job_id}")
    print(f"Payload: {payload}\n")
    
    # Instanciar y ejecutar
    bot = bot_class(job_id=job_id, payload=payload)
    
    async with bot:
        print(f"✓ Driver inicializado\n")
        success = await bot.run()
        
        if success:
            print(f"\n✓ Cotización completada exitosamente")
        else:
            print(f"\n✗ Cotización falló")
        
        assert success, "Bot SBS falló"


@pytest.mark.asyncio
async def test_bot_initialization_and_teardown():
    """
    Test que valida inicialización y limpieza del bot.
    
    No ejecuta el flujo completo, solo verifica setup/teardown.
    """
    aseguradora = "sbs"
    bot_class = get_bot_class(aseguradora)
    
    payload = BOT_TEST_PAYLOADS["sbs"]
    job_id = f"test-init-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"\nTest de inicialización del bot {aseguradora}")
    
    bot = bot_class(job_id=job_id, payload=payload)
    
    # Verificar estado antes de setup
    assert bot.selenium.driver is None, "Driver debe ser None antes de setup"
    assert bot._setup_done is False, "Setup debe ser False antes de setup"
    
    print(f"✓ Estado inicial correcto")
    
    # Setup
    await bot.setup()
    
    assert bot.selenium.driver is not None, "Driver debe existir después de setup"
    assert bot._setup_done is True, "Setup debe ser True después de setup"
    
    print(f"✓ Setup completado correctamente")
    print(f"  - Driver: {bot.selenium.driver}")
    print(f"  - Driver type: {type(bot.selenium.driver).__name__}")
    
    # Teardown
    await bot.teardown()
    
    assert bot.selenium.driver is None, "Driver debe ser None después de teardown"
    assert bot._setup_done is False, "Setup debe ser False después de teardown"
    
    print(f"✓ Teardown completado correctamente")


@pytest.mark.asyncio
async def test_bot_error_handling():
    """
    Test que valida manejo de errores del bot.
    
    Simula un error y verifica que se capture screenshot y se reporte.
    """
    aseguradora = "sbs"
    bot_class = get_bot_class(aseguradora)
    
    payload = BOT_TEST_PAYLOADS["sbs"]
    job_id = f"test-error-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"\nTest de manejo de errores del bot {aseguradora}")
    
    bot = bot_class(job_id=job_id, payload=payload)
    
    async with bot:
        print(f"✓ Bot inicializado")
        
        # Simular error
        await bot.report_error(
            error_code="TEST_ERROR",
            message="Este es un error de prueba",
            severity="ERROR",
            take_screenshot=True
        )
        
        print(f"✓ Error reportado")
        
        # Verificar que se tomó screenshot
        screenshots = list(bot._bot_logger.screenshots_dir.glob("*.png"))
        assert len(screenshots) > 0, "Debe haber al menos un screenshot"
        
        print(f"✓ Screenshot capturado: {screenshots[0].name}")
        
        # Verificar que se escribió en el log
        log_file = bot._bot_logger.log_file
        assert log_file.exists(), "Archivo de log debe existir"
        
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "TEST_ERROR" in log_content, "Error debe estar en el log"
        
        print(f"✓ Error registrado en log")


def test_bot_registry_has_bots():
    """Verificar que hay bots registrados."""
    assert len(BOT_REGISTRY) > 0, "Debe haber al menos un bot registrado"
    print(f"\nBots registrados: {list(BOT_REGISTRY.keys())}")


def test_bot_payloads_defined():
    """Verificar que hay payloads de prueba para los bots."""
    for bot_name in BOT_REGISTRY.keys():
        assert bot_name in BOT_TEST_PAYLOADS, f"No hay payload de prueba para {bot_name}"
        payload = BOT_TEST_PAYLOADS[bot_name]
        assert isinstance(payload, dict), f"Payload de {bot_name} debe ser dict"
        print(f"✓ Payload definido para {bot_name}")

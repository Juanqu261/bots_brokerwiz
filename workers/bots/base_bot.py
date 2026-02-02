"""
Base Bot - Clase orquestadora para bots de Selenium.

Proporciona una clase base que orquesta las utilidades de Selenium y HTTP.
Cada bot específico hereda de esta clase y define su propio método run().

Uso:
    class HDIBot(BaseBot):
        def __init__(self, job_id: str, payload: dict):
            super().__init__(bot_id="hdi", job_id=job_id, payload=payload)
        
        async def run(self) -> bool:
            async with self:  # setup/teardown automático
                # Usar self.selenium para operaciones del navegador
                await self.selenium.get("https://hdi.com.co")
                elem = await self.selenium.wait_for(By.ID, "usuario")
                await self.selenium.type_text(elem, "user@mail.com")
                
                # Usar self.api para comunicación con BrokerWiz
                await self.api.report_error(...)
                return True

Estructura de logs por ejecución:
    logs/bots/{aseguradora}/{job_id}/
    ├── bot.log          ← Logs específicos de esta ejecución
    └── screenshots/     ← Screenshots de esta ejecución
"""

from pathlib import Path
from typing import TYPE_CHECKING

from workers.http import AppWebClient
from workers.selenium import SeleniumDriverManager
from workers.bots.bot_logger import BotExecutionLogger

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


class BaseBot:
    """
    Clase base que orquesta las utilidades de Selenium y HTTP.
    
    Expone dos componentes principales:
        - self.selenium: SeleniumDriverManager con todos los helpers integrados
        - self.api: AppWebClient para comunicación con BrokerWiz API
    
    Attributes:
        bot_id: Identificador del bot (ej: "hdi", "sura")
        job_id: ID único del job/tarea
        payload: Datos recibidos de MQTT para la cotización
        selenium: Driver manager con helpers (wait_for, click, type_text, etc.)
        api: Cliente HTTP para upload de PDFs y reporte de errores
    """
    
    def __init__(self, bot_id: str, job_id: str, payload: dict):
        """
        Inicializar bot base.
        
        Args:
            bot_id: Identificador del bot (ej: "hdi", "sura")
            job_id: ID único del job/tarea (usualmente solicitudAseguradoraId)
            payload: Datos recibidos de MQTT para la cotización
        """
        self.bot_id = bot_id
        self.job_id = job_id
        self.payload = payload
        
        # Logger específico para esta ejecución (escribe a logs/bots/{bot_id}/{job_id}/)
        self._bot_logger = BotExecutionLogger(bot_id, job_id)
        self.logger = self._bot_logger.get_logger()
        
        # Componentes expuestos - el bot los usa directamente
        self.selenium = SeleniumDriverManager(
            bot_id, 
            job_id,
            screenshots_dir=self._bot_logger.screenshots_dir
        )
        self.api = AppWebClient()
        
        # Estado interno
        self._setup_done = False
    
    
    @property
    def driver(self) -> "WebDriver":
        """Acceso directo al WebDriver (atajo para self.selenium.driver)."""
        if not self.selenium.driver:
            raise RuntimeError("Driver no inicializado. Usa 'async with self' o llama setup().")
        return self.selenium.driver
    
    @property
    def solicitud_id(self) -> str:
        """ID de solicitud del payload (usado en reportes a API)."""
        return self.payload.get("in_strIDSolicitudAseguradora", self.job_id)
    
    
    async def setup(self) -> None:
        """Inicializar WebDriver."""
        self.logger.info(f"Iniciando bot {self.bot_id} para job {self.job_id}")
        await self.selenium.create_driver()
        self._setup_done = True
    
    async def teardown(self) -> None:
        """Cerrar WebDriver y limpiar recursos."""
        await self.selenium.quit()
        self._setup_done = False
        self.logger.info(f"Bot {self.bot_id} finalizado para job {self.job_id}")
        # Limpiar handler del logger específico
        self._bot_logger.cleanup()
    
    async def run(self) -> bool:
        """
        Ejecutar la lógica principal del bot.
        
        Este método debe ser implementado por cada bot específico.
        Se ejecuta dentro del context manager (driver ya inicializado).
        
        Returns:
            True si la cotización fue exitosa, False si hubo errores
        
        Raises:
            NotImplementedError: Si no se implementa en la subclase
        """
        raise NotImplementedError(
            f"El bot {self.bot_id} debe implementar el método run()"
        )
    
    
    async def upload_result(self, pdf_path: Path) -> bool:
        """
        Subir PDF resultante a la API.
        
        Renombra el PDF con formato: Autos - Cotizacion SBS [placa] - plan.pdf
        Elimina el archivo después de enviarlo.
        
        Args:
            pdf_path: Ruta al archivo PDF
        
        Returns:
            True si se subió exitosamente
        """
        try:
            # Renombrar PDF con formato estándar
            placa = self.payload.get("in_strPlaca", "UNKNOWN").upper()
            plan = self.payload.get("in_strPlan", "ESTANDAR")
            
            # Si plan es lista, tomar el primer elemento
            if isinstance(plan, list):
                plan = plan[0] if plan else "ESTANDAR"
            
            nuevo_nombre = f"Autos - Cotizacion SBS [{placa}] - {plan}.pdf"
            pdf_renombrado = pdf_path.parent / nuevo_nombre
            
            if pdf_path.exists():
                pdf_path.rename(pdf_renombrado)
                self.logger.info(f"PDF renombrado: {pdf_path.name} → {nuevo_nombre}")
                pdf_path = pdf_renombrado
            
            # Subir PDF
            result = await self.api.upload_pdf(
                pdf_path=pdf_path,
                solicitud_aseguradora_id=self.solicitud_id,
                tipo_subida="bot"
            )
            
            if result.success:
                self.logger.info(f"PDF subido exitosamente: {result.data.get('id', 'N/A')}")
            else:
                self.logger.error(f"Error subiendo PDF: {result.message}")
            
            return result.success
            
        except Exception as e:
            self.logger.error(f"Error en upload_result: {e}")
            return False
        
        finally:
            # Limpiar archivo PDF después de enviarlo
            try:
                if pdf_path.exists():
                    pdf_path.unlink()
                    self.logger.debug(f"PDF eliminado: {pdf_path.name}")
            except Exception as e:
                self.logger.warning(f"No se pudo eliminar PDF: {e}")
    
    async def report_error(
        self,
        error_code: str,
        message: str,
        severity: str = "ERROR",
        take_screenshot: bool = True
    ) -> None:
        """
        Reportar error a la API.
        
        Args:
            error_code: Código de error (ej: "LOGIN_FAILED", "TIMEOUT")
            message: Descripción del error
            severity: "ERROR" | "WARNING"
            take_screenshot: Capturar pantalla antes de reportar
        """
        if take_screenshot and self._setup_done:
            try:
                await self.selenium.screenshot(f"error_{error_code}")
            except Exception as e:
                self.logger.debug(f"No se pudo tomar screenshot: {e}")
        
        # Solo reportar a API en producción
        from config.settings import settings
        if settings.general.ENVIRONMENT == "production":
            await self.api.report_error(
                solicitud_aseguradora_id=self.solicitud_id,
                aseguradora=self.bot_id.upper(),
                error_code=error_code,
                message=message,
                severity=severity
            )
        else:
            self.logger.debug(f"[DEV] Reporte a API omitido (ENVIRONMENT={settings.general.ENVIRONMENT})")
        
        self.logger.error(f"[{error_code}] {message}")
    
    async def __aenter__(self) -> "BaseBot":
        """Permite usar el bot como context manager."""
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Cleanup automático al salir del context manager."""
        await self.teardown()

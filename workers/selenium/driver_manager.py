"""
Selenium Driver Manager - Ciclo de vida del WebDriver con ejecución async.

Gestiona la creación, configuración y destrucción de instancias de Chrome WebDriver.
Usa asyncio.to_thread() para no bloquear el event loop durante operaciones síncronas.

Características:
- Configuración headless fija para producción
- Gestión de descargas de PDFs
- Limpieza automática de archivos temporales
- Integración con CookiesManager
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from workers.selenium.cookies_manager import CookiesManager

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)


class SeleniumDriverManager:
    """Gestiona el ciclo de vida del WebDriver con ejecución async."""
    
    CHROME_ARGS = [
        "--headless=new",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-blink-features=AutomationControlled",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-infobars",
        "--disable-notifications",
        "--disable-popup-blocking",
        "--window-size=1920,1080",
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    # Timeouts
    IMPLICIT_TIMEOUT = 15  # segundos
    PAGE_LOAD_TIMEOUT = 30  # segundos
    SCRIPT_TIMEOUT = 30  # segundos
    
    # Directorio para PDFs temporales
    TEMP_PDF_DIR = Path("temp/pdfs")
    
    # Limpiar PDFs más viejos que esto
    PDF_RETENTION_HOURS = 1
    
    # Directorio para screenshots
    SCREENSHOTS_DIR = Path("logs/bots/screenshots")
    
    def __init__(self, bot_id: str, job_id: str):
        """
        Inicializar manager del driver.
        
        Args:
            bot_id: Identificador del bot (ej: "hdi", "sura")
            job_id: ID único del job/tarea
        """
        self.bot_id = bot_id
        self.job_id = job_id
        self.driver: Optional[webdriver.Chrome] = None
        self._cookies_manager = CookiesManager(bot_id)
        self._created_at: Optional[float] = None
    
    async def create_driver(self) -> webdriver.Chrome:
        """
        Crear WebDriver en thread separado (no bloquea event loop).
        
        Returns:
            Instancia de Chrome WebDriver configurada
        """
        logger.info(f"[{self.bot_id}] Creando WebDriver para job {self.job_id}")
        
        # Asegurar que exista directorio de descargas
        self.TEMP_PDF_DIR.mkdir(parents=True, exist_ok=True)
        
        self.driver = await asyncio.to_thread(self._create_driver_sync)
        self._created_at = time.time()
        
        logger.debug(f"[{self.bot_id}] WebDriver creado exitosamente")
        return self.driver
    
    def _create_driver_sync(self) -> webdriver.Chrome:
        """
        Creación síncrona del driver (ejecutada en thread).
        
        Returns:
            Chrome WebDriver configurado
        """
        options = Options()
        
        # Agregar argumentos de configuración
        for arg in self.CHROME_ARGS:
            options.add_argument(arg)
        
        # Configurar preferencias de Chrome
        prefs = {
            # Descargas
            "download.default_directory": str(self.TEMP_PDF_DIR.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            
            # PDFs: abrir externamente en lugar de viewer interno
            "plugins.always_open_pdf_externally": True,
            
            # Deshabilitar notificaciones
            "profile.default_content_setting_values.notifications": 2,
            
            # Imágenes: mantener habilitadas (algunas páginas las requieren)
            # "profile.managed_default_content_settings.images": 2,  # Descomentar para deshabilitar
        }
        options.add_experimental_option("prefs", prefs)
        
        # Excluir switches que delatan automatización
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Crear servicio con ChromeDriverManager (gestiona versiones automáticamente)
        service = Service(ChromeDriverManager().install())
        
        # Crear driver
        driver = webdriver.Chrome(service=service, options=options)
        
        # Configurar timeouts
        driver.implicitly_wait(self.IMPLICIT_TIMEOUT)
        driver.set_page_load_timeout(self.PAGE_LOAD_TIMEOUT)
        driver.set_script_timeout(self.SCRIPT_TIMEOUT)
        
        # Ejecutar script para ocultar webdriver
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            }
        )
        
        return driver
    
    async def quit(self) -> None:
        """Cerrar driver y limpiar recursos."""
        if self.driver:
            try:
                await asyncio.to_thread(self.driver.quit)
                logger.debug(f"[{self.bot_id}] WebDriver cerrado")
            except Exception as e:
                logger.warning(f"[{self.bot_id}] Error cerrando WebDriver: {e}")
            finally:
                self.driver = None
                self._created_at = None
        
        # Limpiar PDFs viejos
        await self._cleanup_old_pdfs()
    
    async def _cleanup_old_pdfs(self) -> None:
        """Eliminar PDFs temporales más viejos que PDF_RETENTION_HOURS."""
        if not self.TEMP_PDF_DIR.exists():
            return
        
        try:
            current_time = time.time()
            max_age_seconds = self.PDF_RETENTION_HOURS * 3600
            deleted_count = 0
            
            for pdf_file in self.TEMP_PDF_DIR.glob("*.pdf"):
                file_age = current_time - pdf_file.stat().st_mtime
                if file_age > max_age_seconds:
                    pdf_file.unlink()
                    deleted_count += 1
            
            # También limpiar archivos temporales de Chrome
            for temp_file in self.TEMP_PDF_DIR.glob("*.crdownload"):
                temp_file.unlink()
                deleted_count += 1
            
            if deleted_count > 0:
                logger.debug(f"[{self.bot_id}] Eliminados {deleted_count} archivos temporales")
                
        except Exception as e:
            logger.warning(f"[{self.bot_id}] Error limpiando PDFs: {e}")
    
    # === Operaciones de navegación async ===
    
    async def get(self, url: str) -> None:
        """
        Navegar a URL.
        
        Args:
            url: URL destino
        """
        logger.debug(f"[{self.bot_id}] Navegando a: {url}")
        await asyncio.to_thread(self.driver.get, url)
    
    async def refresh(self) -> None:
        """Recargar página actual."""
        await asyncio.to_thread(self.driver.refresh)
    
    async def back(self) -> None:
        """Navegar hacia atrás."""
        await asyncio.to_thread(self.driver.back)
    
    async def forward(self) -> None:
        """Navegar hacia adelante."""
        await asyncio.to_thread(self.driver.forward)
    
    @property
    def current_url(self) -> str:
        """URL actual del navegador."""
        return self.driver.current_url if self.driver else ""
    
    @property
    def page_source(self) -> str:
        """HTML de la página actual."""
        return self.driver.page_source if self.driver else ""
    
    # === Operaciones con elementos async ===
    
    async def find_element(self, by: By, value: str) -> "WebElement":
        """
        Buscar elemento en la página.
        
        Args:
            by: Tipo de localizador (By.ID, By.CSS_SELECTOR, etc.)
            value: Valor del localizador
        
        Returns:
            WebElement encontrado
        """
        return await asyncio.to_thread(self.driver.find_element, by, value)
    
    async def find_elements(self, by: By, value: str) -> list["WebElement"]:
        """
        Buscar múltiples elementos.
        
        Args:
            by: Tipo de localizador
            value: Valor del localizador
        
        Returns:
            Lista de WebElements
        """
        return await asyncio.to_thread(self.driver.find_elements, by, value)
    
    # === Screenshots ===
    
    async def screenshot(self, name: str = "capture") -> Path:
        """
        Capturar pantalla y guardar en directorio de screenshots.
        
        Args:
            name: Nombre descriptivo para el archivo
        
        Returns:
            Path del archivo guardado
        """
        self.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.bot_id}_{self.job_id}_{name}_{timestamp}.png"
        path = self.SCREENSHOTS_DIR / filename
        
        await asyncio.to_thread(self.driver.save_screenshot, str(path))
        logger.debug(f"[{self.bot_id}] Screenshot guardado: {path}")
        
        return path
    
    # === Gestión de cookies (delegación) ===
    
    async def save_cookies(self) -> None:
        """Guardar cookies actuales a archivo."""
        await self._cookies_manager.save(self.driver)
    
    async def load_cookies(self, domain: str) -> bool:
        """
        Cargar cookies desde archivo.
        
        Args:
            domain: Dominio base (ej: "hdi.com.co")
        
        Returns:
            True si se cargaron cookies
        """
        return await self._cookies_manager.load(self.driver, domain)
    
    def clear_cookies(self) -> None:
        """Eliminar archivo de cookies."""
        self._cookies_manager.clear()
    
    async def delete_all_cookies(self) -> None:
        """Eliminar todas las cookies del navegador."""
        await asyncio.to_thread(self.driver.delete_all_cookies)
    
    # === Context manager ===
    
    async def __aenter__(self) -> "SeleniumDriverManager":
        """Crear driver al entrar al context manager."""
        await self.create_driver()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Cerrar driver al salir del context manager."""
        await self.quit()

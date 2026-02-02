"""
Selenium Driver Manager - Ciclo de vida del WebDriver con ejecución async.

Hereda de SeleniumHelpers para tener todos los métodos de interacción.
Agrega gestión de lifecycle (crear, cerrar), cookies, y configuración de Chrome.

Uso:
    async with SeleniumDriverManager("hdi", "job-123") as selenium:
        await selenium.get("https://hdi.com.co")
        elem = await selenium.wait_for(By.ID, "usuario")
        await selenium.type_text(elem, "user@mail.com")
"""

import asyncio
import logging
import platform
import time
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

from config.settings import settings
from workers.selenium.cookies_manager import CookiesManager
from workers.selenium.helpers import SeleniumHelpers

logger = logging.getLogger(__name__)


class SeleniumDriverManager(SeleniumHelpers):
    """
    Gestiona el ciclo de vida del WebDriver.
    
    Hereda todos los helpers de SeleniumHelpers (wait_for, click, type_text, etc.)
    """
    
    # Argumentos base de Chrome
    CHROME_ARGS_BASE = [
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
        "--start-maximized",
        # "--incognito",
    ]
    
    @staticmethod
    def _get_user_agent() -> str:
        """
        Obtener User-Agent según el SO para evitar bloqueos por plataforma.
        
        Returns:
            User-Agent string apropiado para Windows/Linux
        """
        if platform.system() == "Linux":
            return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        else:  # Windows, Darwin (Mac)
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # Timeouts
    IMPLICIT_TIMEOUT = 15
    PAGE_LOAD_TIMEOUT = 30
    SCRIPT_TIMEOUT = 30
    
    # Directorios
    TEMP_PDF_DIR = Path("temp/pdfs")
    DEFAULT_SCREENSHOTS_DIR = Path("logs/bots/screenshots")
    PDF_RETENTION_HOURS = 1
    
    def __init__(self, bot_id: str, job_id: str, screenshots_dir: Path | None = None):
        """
        Inicializar manager del driver.
        
        Args:
            bot_id: Identificador del bot (ej: "hdi", "sura")
            job_id: ID único del job/tarea
            screenshots_dir: Directorio para screenshots (opcional, usa default si no se pasa)
        """
        self.bot_id = bot_id
        self.job_id = job_id
        self.driver: Optional[webdriver.Chrome] = None
        self._cookies_manager = CookiesManager(bot_id)
        self._created_at: Optional[float] = None
        self._screenshots_dir = screenshots_dir or self.DEFAULT_SCREENSHOTS_DIR
    
    # === Lifecycle ===
    
    async def create_driver(self) -> webdriver.Chrome:
        """Crear WebDriver en thread separado."""
        logger.info(f"[{self.bot_id}] Creando WebDriver para job {self.job_id}")
        self.TEMP_PDF_DIR.mkdir(parents=True, exist_ok=True)
        
        self.driver = await asyncio.to_thread(self._create_driver_sync)
        self._created_at = time.time()
        
        logger.debug(f"[{self.bot_id}] WebDriver creado exitosamente")
        return self.driver
    
    def _create_driver_sync(self) -> webdriver.Chrome:
        """Creación síncrona del driver (ejecutada en thread)."""
        # Preferir undetected-chromedriver si está disponible (evita bloqueos de Cloudflare)
        if UNDETECTED_AVAILABLE:
            logger.info(f"[{self.bot_id}] Usando undetected-chromedriver para evitar bloqueos de Cloudflare")
            return self._create_undetected_driver()
        else:
            logger.info(f"[{self.bot_id}] Usando chromedriver estándar (instala 'undetected-chromedriver' para mejor compatibilidad)")
            return self._create_standard_driver()
    
    def _create_undetected_driver(self) -> webdriver.Chrome:
        """Crear driver con undetected-chromedriver (evita detección de bots)."""
        options = Options()
        
        # Headless en producción
        is_production = settings.general.ENVIRONMENT == "production"
        if is_production:
            options.add_argument("--headless=new")
            logger.debug(f"[{self.bot_id}] Chrome en modo headless (production)")
        else:
            logger.info(f"[{self.bot_id}] Chrome en modo visible (ENVIRONMENT={settings.general.ENVIRONMENT})")
        
        for arg in self.CHROME_ARGS_BASE:
            options.add_argument(arg)
        
        # User-Agent dinámico
        user_agent = self._get_user_agent()
        options.add_argument(f"--user-agent={user_agent}")
        logger.debug(f"[{self.bot_id}] User-Agent: {user_agent}")
        
        # Preferencias de descarga
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "download.default_directory": str(self.TEMP_PDF_DIR.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_setting_values.notifications": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            # Crear driver con undetected-chromedriver
            driver = uc.Chrome(options=options, version_main=None, suppress_welcome=True)
            
            driver.implicitly_wait(self.IMPLICIT_TIMEOUT)
            driver.set_page_load_timeout(self.PAGE_LOAD_TIMEOUT)
            driver.set_script_timeout(self.SCRIPT_TIMEOUT)
            
            # Inyectar headers
            self._inject_headers(driver)
            
            logger.debug(f"[{self.bot_id}] Driver undetected creado exitosamente")
            return driver
        
        except Exception as e:
            logger.warning(f"[{self.bot_id}] Error con undetected-chromedriver: {e}, usando estándar")
            return self._create_standard_driver()
    
    def _create_standard_driver(self) -> webdriver.Chrome:
        """Crear driver estándar de Selenium (fallback)."""
        options = Options()
        
        is_production = settings.general.ENVIRONMENT == "production"
        if is_production:
            options.add_argument("--headless=new")
            logger.debug(f"[{self.bot_id}] Chrome en modo headless (production)")
        else:
            logger.info(f"[{self.bot_id}] Chrome en modo visible (ENVIRONMENT={settings.general.ENVIRONMENT})")
        
        for arg in self.CHROME_ARGS_BASE:
            options.add_argument(arg)
        
        user_agent = self._get_user_agent()
        options.add_argument(f"--user-agent={user_agent}")
        logger.debug(f"[{self.bot_id}] User-Agent: {user_agent}")
        
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "download.default_directory": str(self.TEMP_PDF_DIR.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_setting_values.notifications": 2,
        }
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        driver = webdriver.Chrome(options=options)
        
        driver.implicitly_wait(self.IMPLICIT_TIMEOUT)
        driver.set_page_load_timeout(self.PAGE_LOAD_TIMEOUT)
        driver.set_script_timeout(self.SCRIPT_TIMEOUT)
        
        # Ocultar webdriver
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"}
        )
        
        # Inyectar headers
        self._inject_headers(driver)
        
        logger.debug(f"[{self.bot_id}] Driver estándar creado exitosamente")
        return driver
    
    def _inject_headers(self, driver: webdriver.Chrome) -> None:
        """
        Inyectar headers HTTP que evitan bloqueos de Cloudflare.
        Esto engaña al WAF para que no detecte el bot.
        """
        headers = {
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "DNT": "1",
            "Referer": "https://www.google.com/",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Linux"' if platform.system() == "Linux" else '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        
        try:
            # Usar CDP para inyectar headers en todas las peticiones
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": self._get_user_agent()
            })
            
            # Inyectar headers por defecto
            for key, value in headers.items():
                driver.execute_cdp_cmd(
                    "Network.setExtraHTTPHeaders",
                    {"headers": {key: value}}
                )
            
            logger.debug(f"[{self.bot_id}] Headers HTTP inyectados para evitar WAF")
        except Exception as e:
            logger.warning(f"[{self.bot_id}] No se pudieron inyectar headers: {e}")
    
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
        
        await self._cleanup_old_pdfs()
    
    async def _cleanup_old_pdfs(self) -> None:
        """Eliminar PDFs temporales viejos."""
        if not self.TEMP_PDF_DIR.exists():
            return
        
        try:
            current_time = time.time()
            max_age = self.PDF_RETENTION_HOURS * 3600
            deleted = 0
            
            for f in self.TEMP_PDF_DIR.glob("*.pdf"):
                if current_time - f.stat().st_mtime > max_age:
                    f.unlink()
                    deleted += 1
            
            for f in self.TEMP_PDF_DIR.glob("*.crdownload"):
                f.unlink()
                deleted += 1
            
            if deleted:
                logger.debug(f"[{self.bot_id}] Eliminados {deleted} archivos temporales")
        except Exception as e:
            logger.warning(f"[{self.bot_id}] Error limpiando PDFs: {e}")
    
    # === Navegación ===
    
    async def get(self, url: str) -> None:
        """Navegar a URL."""
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
    
    # === Búsqueda de elementos ===
    
    async def find_element(self, by: By, value: str):
        """Buscar elemento en la página."""
        return await asyncio.to_thread(self.driver.find_element, by, value)
    
    async def find_elements(self, by: By, value: str):
        """Buscar múltiples elementos."""
        return await asyncio.to_thread(self.driver.find_elements, by, value)
    
    # === Screenshots ===
    
    async def screenshot(self, name: str = "capture") -> Path:
        """Capturar pantalla."""
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%H%M%S")
        filename = f"{timestamp}_{name}.png"
        path = self._screenshots_dir / filename
        
        await asyncio.to_thread(self.driver.save_screenshot, str(path))
        logger.debug(f"[{self.bot_id}] Screenshot: {path}")
        
        return path
    
    # === Cookies ===
    
    async def save_cookies(self) -> None:
        """Guardar cookies actuales a archivo."""
        await self._cookies_manager.save(self.driver)
    
    async def load_cookies(self, domain: str) -> bool:
        """Cargar cookies desde archivo."""
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

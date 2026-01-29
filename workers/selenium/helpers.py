"""
Selenium Helpers - Clase base con operaciones comunes de Selenium.

Proporciona métodos async para operaciones frecuentes como esperar elementos,
clicks seguros, envío de texto, y espera de descargas.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Literal

from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)

# Tipo para condiciones de espera
WaitCondition = Literal["presence", "visible", "clickable", "invisible"]


class SeleniumHelpers:
    """
    Clase base con helpers de Selenium.
    
    Diseñada para ser heredada. Requiere que la clase hija defina:
        - self.driver: WebDriver
        - self.TEMP_PDF_DIR: Path (para wait_for_download)
    """
    
    # Constantes (pueden ser sobreescritas por la clase hija)
    DEFAULT_TIMEOUT = 15
    TEMP_PDF_DIR: Path = Path("temp/pdfs")
    
    # Referencia al driver (definida por la clase hija)
    driver: Optional["WebDriver"] = None
    
    # === Espera de elementos ===
    
    async def wait_for(
        self,
        by: By,
        value: str,
        timeout: int = DEFAULT_TIMEOUT,
        condition: WaitCondition = "presence"
    ) -> "WebElement":
        """
        Esperar elemento con WebDriverWait.
        
        Args:
            by: Tipo de localizador (By.ID, By.CSS_SELECTOR, etc.)
            value: Valor del localizador
            timeout: Tiempo máximo de espera en segundos
            condition: Tipo de condición:
                - "presence": elemento existe en DOM
                - "visible": elemento visible en pantalla
                - "clickable": elemento visible y habilitado
                - "invisible": elemento no visible (útil para loaders)
        
        Returns:
            WebElement encontrado
        
        Raises:
            TimeoutException: Si el elemento no aparece
        """
        conditions_map = {
            "presence": EC.presence_of_element_located,
            "visible": EC.visibility_of_element_located,
            "clickable": EC.element_to_be_clickable,
            "invisible": EC.invisibility_of_element_located,
        }
        
        locator = (by, value)
        wait = WebDriverWait(self.driver, timeout)
        
        return await asyncio.to_thread(
            wait.until, 
            conditions_map[condition](locator)
        )
    
    async def wait_for_all(
        self,
        by: By,
        value: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> list["WebElement"]:
        """Esperar múltiples elementos."""
        locator = (by, value)
        wait = WebDriverWait(self.driver, timeout)
        
        return await asyncio.to_thread(
            wait.until,
            EC.presence_of_all_elements_located(locator)
        )
    
    # === Interacción con elementos ===
    
    async def click(
        self,
        element: "WebElement",
        scroll: bool = True,
        use_js: bool = False
    ) -> None:
        """
        Click con scroll previo y fallback a JS.
        
        Args:
            element: Elemento a clickear
            scroll: Si hacer scroll al elemento primero
            use_js: Usar JavaScript click directamente
        """
        if scroll:
            await asyncio.to_thread(
                self.driver.execute_script,
                "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
                element
            )
            await asyncio.sleep(0.2)
        
        try:
            if use_js:
                await asyncio.to_thread(
                    self.driver.execute_script,
                    "arguments[0].click();",
                    element
                )
            else:
                await asyncio.to_thread(element.click)
                
        except ElementClickInterceptedException:
            logger.debug("Click interceptado, usando JavaScript click")
            await asyncio.to_thread(
                self.driver.execute_script,
                "arguments[0].click();",
                element
            )
    
    async def type_text(
        self,
        element: "WebElement",
        text: str,
        clear: bool = True,
        delay: float = 0
    ) -> None:
        """
        Enviar texto a un elemento.
        
        Args:
            element: Elemento input/textarea
            text: Texto a enviar
            clear: Limpiar campo antes
            delay: Pausa entre caracteres (simula humano)
        """
        if clear:
            await asyncio.to_thread(element.clear)
            await asyncio.sleep(0.1)
        
        if delay > 0:
            for char in text:
                await asyncio.to_thread(element.send_keys, char)
                await asyncio.sleep(delay)
        else:
            await asyncio.to_thread(element.send_keys, text)
    
    async def select_by_text(self, element: "WebElement", text: str) -> None:
        """Seleccionar opción de <select> por texto visible."""
        select = Select(element)
        await asyncio.to_thread(select.select_by_visible_text, text)
    
    async def select_by_value(self, element: "WebElement", value: str) -> None:
        """Seleccionar opción de <select> por valor."""
        select = Select(element)
        await asyncio.to_thread(select.select_by_value, value)
    
    # === Obtener información de elementos ===
    
    async def get_text(self, element: "WebElement") -> str:
        """Obtener texto de un elemento."""
        return await asyncio.to_thread(lambda: element.text)
    
    async def get_attribute(self, element: "WebElement", name: str) -> Optional[str]:
        """Obtener atributo de un elemento."""
        return await asyncio.to_thread(element.get_attribute, name)
    
    async def is_displayed(self, element: "WebElement") -> bool:
        """Verificar si elemento está visible."""
        try:
            return await asyncio.to_thread(element.is_displayed)
        except StaleElementReferenceException:
            return False
    
    # === Esperas especiales ===
    
    async def wait_for_download(
        self,
        timeout: int = 30,
        extension: str = ".pdf"
    ) -> Optional[Path]:
        """
        Esperar a que se complete una descarga.
        
        Args:
            timeout: Tiempo máximo de espera
            extension: Extensión del archivo esperado
        
        Returns:
            Path del archivo descargado, o None si timeout
        """
        self.TEMP_PDF_DIR.mkdir(parents=True, exist_ok=True)
        
        initial_count = len(list(self.TEMP_PDF_DIR.glob(f"*{extension}")))
        start = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start) < timeout:
            files = list(self.TEMP_PDF_DIR.glob(f"*{extension}"))
            temp_files = list(self.TEMP_PDF_DIR.glob("*.crdownload"))
            complete_files = [f for f in files if f.suffix != ".crdownload"]
            
            if len(complete_files) > initial_count and len(temp_files) == 0:
                newest = max(complete_files, key=lambda f: f.stat().st_mtime)
                logger.debug(f"Descarga completada: {newest.name}")
                return newest
            
            await asyncio.sleep(0.5)
        
        logger.warning("Timeout esperando descarga")
        return None
    
    async def wait_for_url(self, text: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        """Esperar a que la URL contenga un texto."""
        wait = WebDriverWait(self.driver, timeout)
        try:
            await asyncio.to_thread(wait.until, EC.url_contains(text))
            return True
        except TimeoutException:
            return False
    
    async def wait_page_load(self, timeout: int = 30) -> None:
        """Esperar a que la página termine de cargar."""
        wait = WebDriverWait(self.driver, timeout)
        await asyncio.to_thread(
            wait.until,
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    
    # === Iframes ===
    
    async def switch_to_frame(self, frame: "WebElement") -> None:
        """Cambiar contexto a un iframe."""
        await asyncio.to_thread(self.driver.switch_to.frame, frame)
    
    async def switch_to_default(self) -> None:
        """Volver al contexto principal desde un iframe."""
        await asyncio.to_thread(self.driver.switch_to.default_content)
    
    # === JavaScript ===
    
    async def execute_js(self, script: str, *args) -> any:
        """Ejecutar JavaScript en el navegador."""
        return await asyncio.to_thread(self.driver.execute_script, script, *args)
    
    # === Ventanas y handles ===
    
    async def get_current_window(self) -> str:
        """Obtener handle de la ventana actual."""
        return await asyncio.to_thread(lambda: self.driver.current_window_handle)
    
    async def get_window_handles(self) -> list[str]:
        """Obtener lista de handles de todas las ventanas."""
        return await asyncio.to_thread(lambda: self.driver.window_handles)
    
    async def switch_to_window(self, window_handle: str) -> None:
        """Cambiar a una ventana específica."""
        await asyncio.to_thread(self.driver.switch_to.window, window_handle)
    
    # === Screenshots ===
    
    async def take_screenshot(self, element: Optional["WebElement"] = None) -> bytes:
        """
        Tomar screenshot de la página o de un elemento.
        
        Args:
            element: Elemento específico (opcional). Si no se proporciona, toma de toda la página.
        
        Returns:
            Bytes de la imagen PNG
        """
        if element:
            return await asyncio.to_thread(element.screenshot_as_png)
        else:
            return await asyncio.to_thread(self.driver.get_screenshot_as_png)
    
    # === Cookies ===
    
    async def save_cookies(self) -> None:
        """
        Guardar cookies de la sesión actual.
        
        Requiere que la clase hija tenga un atributo _cookies_manager.
        """
        if hasattr(self, '_cookies_manager'):
            await self._cookies_manager.save(self.driver)
        else:
            logger.warning("No hay _cookies_manager disponible para guardar cookies")
    
    async def load_cookies(self, domain: str) -> bool:
        """
        Cargar cookies guardadas para un dominio.
        
        IMPORTANTE: El driver debe haber navegado primero al dominio
        antes de cargar cookies (requisito de Selenium).
        
        Args:
            domain: Dominio base para filtrar cookies (ej: "sbseguros.co")
        
        Returns:
            True si se cargaron cookies, False si no existían o hubo error
        """
        if hasattr(self, '_cookies_manager'):
            return await self._cookies_manager.load(self.driver, domain)
        else:
            logger.warning("No hay _cookies_manager disponible para cargar cookies")
            return False
    
    # === Acceso directo al driver ===
    
    def get_raw_driver(self) -> "WebDriver":
        """
        Obtener acceso al driver crudo para operaciones no cubiertas.
        
        Útil para extensiones personalizadas que necesitan acceso directo a Selenium.
        
        Returns:
            WebDriver instancia sin wrapper
        """
        return self.driver

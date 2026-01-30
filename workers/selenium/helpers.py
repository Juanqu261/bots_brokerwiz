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

from workers.selenium.human_interaction import HumanInteraction

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
    
    Proporciona acceso a:
        - self.human: HumanInteraction para simular comportamiento humano
    """
    
    # Constantes (pueden ser sobreescritas por la clase hija)
    DEFAULT_TIMEOUT = 15
    TEMP_PDF_DIR: Path = Path("temp/pdfs")
    
    # Referencia al driver (definida por la clase hija)
    driver: Optional["WebDriver"] = None
    _human: Optional[HumanInteraction] = None
    
    @property
    def human(self) -> HumanInteraction:
        """
        Acceso a métodos de interacción humana.
        
        Uso:
            await self.human.pause(1, 3)
            await self.human.click("#button")
            await self.human.input("#input", "texto")
        """
        if not self.driver:
            raise RuntimeError("Driver no inicializado")
        
        if self._human is None:
            self._human = HumanInteraction(self.driver)
        
        return self._human
    
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
        extension: str = ".pdf",
        initial_count: int = None
    ) -> Optional[Path]:
        """
        Esperar a que se complete una descarga.
        
        Verifica que el archivo exista, no esté en descarga (.crdownload),
        y que su tamaño sea estable (no cambie entre lecturas).
        
        Args:
            timeout: Tiempo máximo de espera
            extension: Extensión del archivo esperado
            initial_count: Número de archivos iniciales (si None, se cuenta al inicio)
        
        Returns:
            Path del archivo descargado, o None si timeout
        """
        import time
        
        self.TEMP_PDF_DIR.mkdir(parents=True, exist_ok=True)
        
        # Contar archivos iniciales
        if initial_count is None:
            initial_files = list(self.TEMP_PDF_DIR.glob(f"*{extension}"))
            initial_count = len(initial_files)
        else:
            initial_files = list(self.TEMP_PDF_DIR.glob(f"*{extension}"))
        
        logger.info(f"Esperando descarga en {self.TEMP_PDF_DIR.absolute()}")
        logger.info(f"Archivos iniciales: {initial_count}")
        if initial_files:
            logger.info(f"Archivos existentes: {[f.name for f in initial_files]}")
        
        start_time = time.time()
        last_log_time = start_time
        
        while (time.time() - start_time) < timeout:
            try:
                # Buscar archivos PDF
                all_pdfs = list(self.TEMP_PDF_DIR.glob(f"*{extension}"))
                
                # Buscar archivos en descarga
                temp_files = list(self.TEMP_PDF_DIR.glob("*.crdownload"))
                
                # Log cada 5 segundos para no saturar
                current_time = time.time()
                if (current_time - last_log_time) > 5:
                    logger.debug(f"PDFs encontrados: {len(all_pdfs)}, en descarga: {len(temp_files)}")
                    if all_pdfs:
                        logger.debug(f"Archivos: {[f.name for f in all_pdfs]}")
                    last_log_time = current_time
                
                # Si hay más archivos que al inicio y no hay archivos en descarga
                if len(all_pdfs) > initial_count and len(temp_files) == 0:
                    # Obtener el archivo más reciente
                    newest = max(all_pdfs, key=lambda f: f.stat().st_mtime)
                    
                    logger.info(f"Archivo más reciente detectado: {newest.name}")
                    
                    # Verificar que el tamaño sea estable (no está siendo escrito)
                    size1 = newest.stat().st_size
                    await asyncio.sleep(1)
                    size2 = newest.stat().st_size
                    
                    logger.debug(f"Validación de tamaño: {size1} → {size2} bytes")
                    
                    if size1 == size2 and size1 > 0:
                        logger.info(f"Descarga completada: {newest.name} ({size1} bytes)")
                        return newest
                    else:
                        logger.debug(f"Tamaño inestable, esperando más...")
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error verificando descarga: {e}")
                await asyncio.sleep(0.5)
        
        # Timeout
        logger.error(f"Timeout esperando descarga después de {timeout}s")
        logger.error(f"Directorio: {self.TEMP_PDF_DIR.absolute()}")
        
        # Listar todos los archivos en el directorio para debugging
        try:
            all_files = list(self.TEMP_PDF_DIR.glob("*"))
            logger.error(f"Archivos en directorio: {[f.name for f in all_files]}")
            
            # Mostrar archivos por extensión
            for ext in [".pdf", ".crdownload", ""]:
                files = list(self.TEMP_PDF_DIR.glob(f"*{ext}"))
                if files:
                    logger.error(f"Archivos {ext}: {[f.name for f in files]}")
        except Exception as e:
            logger.error(f"Error listando archivos: {e}")
        
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

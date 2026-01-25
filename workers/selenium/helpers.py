"""
Selenium Helpers - Utilidades comunes para operaciones de Selenium.

Funciones estáticas async para operaciones frecuentes como esperar elementos,
clicks seguros, envío de texto, y espera de descargas.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Literal

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
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
    """Helpers estáticos para operaciones comunes de Selenium."""
    
    # Timeout por defecto para esperas
    DEFAULT_TIMEOUT = 15
    
    @staticmethod
    async def wait_for_element(
        driver: "WebDriver",
        by: By,
        value: str,
        timeout: int = DEFAULT_TIMEOUT,
        condition: WaitCondition = "presence"
    ) -> "WebElement":
        """
        Esperar elemento con WebDriverWait.
        
        Args:
            driver: WebDriver activo
            by: Tipo de localizador (By.ID, By.CSS_SELECTOR, etc.)
            value: Valor del localizador
            timeout: Tiempo máximo de espera en segundos
            condition: Tipo de condición a esperar:
                - "presence": elemento existe en DOM
                - "visible": elemento visible en pantalla
                - "clickable": elemento visible y habilitado para click
                - "invisible": elemento no visible (útil para loaders)
        
        Returns:
            WebElement encontrado
        
        Raises:
            TimeoutException: Si el elemento no aparece en el tiempo dado
        """
        conditions_map = {
            "presence": EC.presence_of_element_located,
            "visible": EC.visibility_of_element_located,
            "clickable": EC.element_to_be_clickable,
            "invisible": EC.invisibility_of_element_located,
        }
        
        locator = (by, value)
        wait = WebDriverWait(driver, timeout)
        
        return await asyncio.to_thread(
            wait.until, 
            conditions_map[condition](locator)
        )
    
    @staticmethod
    async def wait_for_elements(
        driver: "WebDriver",
        by: By,
        value: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> list["WebElement"]:
        """
        Esperar múltiples elementos.
        
        Args:
            driver: WebDriver activo
            by: Tipo de localizador
            value: Valor del localizador
            timeout: Tiempo máximo de espera
        
        Returns:
            Lista de WebElements encontrados
        """
        locator = (by, value)
        wait = WebDriverWait(driver, timeout)
        
        return await asyncio.to_thread(
            wait.until,
            EC.presence_of_all_elements_located(locator)
        )
    
    @staticmethod
    async def safe_click(
        driver: "WebDriver",
        element: "WebElement",
        scroll: bool = True,
        use_js: bool = False
    ) -> None:
        """
        Click con scroll previo y manejo de excepciones.
        
        Args:
            driver: WebDriver activo
            element: Elemento a clickear
            scroll: Si hacer scroll al elemento primero
            use_js: Usar JavaScript click (útil cuando el click normal falla)
        """
        if scroll:
            # Scroll al elemento para asegurar visibilidad
            await asyncio.to_thread(
                driver.execute_script,
                "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
                element
            )
            await asyncio.sleep(0.2)  # Pausa para que complete el scroll
        
        try:
            if use_js:
                await asyncio.to_thread(
                    driver.execute_script,
                    "arguments[0].click();",
                    element
                )
            else:
                await asyncio.to_thread(element.click)
                
        except ElementClickInterceptedException:
            # Si el click normal falla, intentar con JavaScript
            logger.debug("Click interceptado, usando JavaScript click")
            await asyncio.to_thread(
                driver.execute_script,
                "arguments[0].click();",
                element
            )
    
    @staticmethod
    async def safe_send_keys(
        element: "WebElement",
        text: str,
        clear: bool = True,
        delay: float = 0
    ) -> None:
        """
        Enviar texto a un elemento con limpieza opcional.
        
        Args:
            element: Elemento input/textarea
            text: Texto a enviar
            clear: Limpiar campo antes de escribir
            delay: Pausa entre caracteres (simula escritura humana)
        """
        if clear:
            await asyncio.to_thread(element.clear)
            await asyncio.sleep(0.1)
        
        if delay > 0:
            # Escribir caracter por caracter con delay
            for char in text:
                await asyncio.to_thread(element.send_keys, char)
                await asyncio.sleep(delay)
        else:
            await asyncio.to_thread(element.send_keys, text)
    
    @staticmethod
    async def select_by_text(
        element: "WebElement",
        text: str
    ) -> None:
        """
        Seleccionar opción de un <select> por texto visible.
        
        Args:
            element: Elemento <select>
            text: Texto visible de la opción
        """
        select = Select(element)
        await asyncio.to_thread(select.select_by_visible_text, text)
    
    @staticmethod
    async def select_by_value(
        element: "WebElement",
        value: str
    ) -> None:
        """
        Seleccionar opción de un <select> por valor.
        
        Args:
            element: Elemento <select>
            value: Valor del atributo value de la opción
        """
        select = Select(element)
        await asyncio.to_thread(select.select_by_value, value)
    
    @staticmethod
    async def get_text(element: "WebElement") -> str:
        """Obtener texto de un elemento."""
        return await asyncio.to_thread(lambda: element.text)
    
    @staticmethod
    async def get_attribute(element: "WebElement", name: str) -> Optional[str]:
        """Obtener atributo de un elemento."""
        return await asyncio.to_thread(element.get_attribute, name)
    
    @staticmethod
    async def is_displayed(element: "WebElement") -> bool:
        """Verificar si elemento está visible."""
        try:
            return await asyncio.to_thread(element.is_displayed)
        except StaleElementReferenceException:
            return False
    
    @staticmethod
    async def wait_for_download(
        download_dir: Path,
        timeout: int = 30,
        extension: str = ".pdf",
        initial_count: int = 0
    ) -> Optional[Path]:
        """
        Esperar a que se complete una descarga.
        
        Args:
            download_dir: Directorio de descargas
            timeout: Tiempo máximo de espera en segundos
            extension: Extensión del archivo esperado
            initial_count: Número de archivos con esa extensión antes de iniciar descarga
        
        Returns:
            Path del archivo descargado, o None si timeout
        """
        download_dir.mkdir(parents=True, exist_ok=True)
        start = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start) < timeout:
            # Buscar archivos con la extensión
            files = list(download_dir.glob(f"*{extension}"))
            
            # Filtrar archivos temporales de Chrome (.crdownload)
            temp_files = list(download_dir.glob("*.crdownload"))
            
            # Si hay archivos nuevos y no hay temporales, descarga completada
            complete_files = [f for f in files if f.suffix != ".crdownload"]
            
            if len(complete_files) > initial_count and len(temp_files) == 0:
                # Retornar el archivo más reciente
                newest = max(complete_files, key=lambda f: f.stat().st_mtime)
                logger.debug(f"Descarga completada: {newest.name}")
                return newest
            
            await asyncio.sleep(0.5)
        
        logger.warning(f"Timeout esperando descarga en {download_dir}")
        return None
    
    @staticmethod
    async def wait_for_url_contains(
        driver: "WebDriver",
        text: str,
        timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        """
        Esperar a que la URL contenga un texto específico.
        
        Args:
            driver: WebDriver activo
            text: Texto que debe contener la URL
            timeout: Tiempo máximo de espera
        
        Returns:
            True si la URL contiene el texto, False si timeout
        """
        wait = WebDriverWait(driver, timeout)
        try:
            await asyncio.to_thread(wait.until, EC.url_contains(text))
            return True
        except TimeoutException:
            return False
    
    @staticmethod
    async def wait_for_page_load(
        driver: "WebDriver",
        timeout: int = DEFAULT_TIMEOUT
    ) -> None:
        """
        Esperar a que la página termine de cargar.
        
        Args:
            driver: WebDriver activo
            timeout: Tiempo máximo de espera
        """
        wait = WebDriverWait(driver, timeout)
        await asyncio.to_thread(
            wait.until,
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    
    @staticmethod
    async def switch_to_frame(
        driver: "WebDriver",
        frame: "WebElement"
    ) -> None:
        """Cambiar contexto a un iframe."""
        await asyncio.to_thread(driver.switch_to.frame, frame)
    
    @staticmethod
    async def switch_to_default(driver: "WebDriver") -> None:
        """Volver al contexto principal desde un iframe."""
        await asyncio.to_thread(driver.switch_to.default_content)
    
    @staticmethod
    async def execute_script(
        driver: "WebDriver",
        script: str,
        *args
    ) -> any:
        """
        Ejecutar JavaScript en el navegador.
        
        Args:
            driver: WebDriver activo
            script: Código JavaScript a ejecutar
            *args: Argumentos para el script (accesibles como arguments[0], etc.)
        
        Returns:
            Resultado del script
        """
        return await asyncio.to_thread(driver.execute_script, script, *args)

"""
Human Interaction - Métodos para simular comportamiento humano en Selenium.

Proporciona métodos para interactuar con el navegador de forma que simule
un usuario humano (delays aleatorios, pausas, etc.).

Uso:
    human = HumanInteraction(selenium_driver_manager)
    await human.pause(1, 3)
    await human.click("#button-id")
    await human.input("#input-id", "texto")
"""

import asyncio
import random
import logging
from typing import TYPE_CHECKING

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


class HumanInteraction:
    """
    Simula comportamiento humano en interacciones con Selenium.
    
    Proporciona métodos para:
    - Pausas aleatorias (simula tiempo de lectura/reflexión)
    - Clicks con delays (simula movimiento del mouse)
    - Input de texto carácter por carácter (simula escritura)
    """
    
    def __init__(self, driver: "WebDriver"):
        """
        Inicializar interacción humana.
        
        Args:
            driver: WebDriver de Selenium
        """
        self.driver = driver
        self.logger = logging.getLogger(f"{__name__}.human")
    
    async def pause(self, min_seconds: float = 0.8, max_seconds: float = 2.5) -> None:
        """
        Pausa aleatoria simulando comportamiento humano.
        
        Args:
            min_seconds: Mínimo de segundos a esperar
            max_seconds: Máximo de segundos a esperar
        """
        pause_time = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(pause_time)
    
    async def click(
        self,
        selector: str,
        timeout: int = 30,
        pause_before: tuple = (1.2, 2.8),
        pause_after: tuple = (0.5, 1.5)
    ) -> None:
        """
        Click en elemento con pausa previa (simula movimiento del mouse).
        
        Args:
            selector: CSS selector del elemento
            timeout: Timeout en segundos
            pause_before: Tupla (min, max) de pausa antes del click
            pause_after: Tupla (min, max) de pausa después del click
        """
        try:
            loop = asyncio.get_running_loop()
            
            def _click():
                wait = WebDriverWait(self.driver, timeout)
                element = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                return element
            
            element = await loop.run_in_executor(None, _click)
            
            # Pausa antes del click (simula movimiento del mouse)
            await self.pause(pause_before[0], pause_before[1])
            
            # Click
            await loop.run_in_executor(None, element.click)
            
            # Pausa después del click
            await self.pause(pause_after[0], pause_after[1])
            
        except Exception as e:
            self.logger.error(f"Error en click({selector}): {e}")
            raise
    
    async def input(
        self,
        selector: str,
        text: str,
        timeout: int = 30,
        char_delay: tuple = (0.05, 0.15),
        clear: bool = True
    ) -> None:
        """
        Enviar texto carácter por carácter (simula escritura humana).
        
        Args:
            selector: CSS selector del elemento input
            text: Texto a enviar
            timeout: Timeout en segundos
            char_delay: Tupla (min, max) de delay entre caracteres
            clear: Limpiar campo antes de escribir
        """
        try:
            loop = asyncio.get_running_loop()
            
            def _get_element():
                wait = WebDriverWait(self.driver, timeout)
                element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                return element
            
            element = await loop.run_in_executor(None, _get_element)
            
            # Limpiar campo si se solicita
            if clear:
                await loop.run_in_executor(None, element.clear)
                await self.pause(0.1, 0.3)
            
            # Enviar texto carácter por carácter
            for char in text:
                await loop.run_in_executor(None, element.send_keys, char)
                # Delay aleatorio entre caracteres
                char_wait = random.uniform(char_delay[0], char_delay[1])
                await asyncio.sleep(char_wait)
            
        except Exception as e:
            self.logger.error(f"Error en input({selector}): {e}")
            raise
    
    async def type_text(
        self,
        selector: str,
        text: str,
        timeout: int = 30,
        char_delay: tuple = (0.05, 0.15)
    ) -> None:
        """
        Alias para input() - Enviar texto carácter por carácter.
        
        Args:
            selector: CSS selector del elemento input
            text: Texto a enviar
            timeout: Timeout en segundos
            char_delay: Tupla (min, max) de delay entre caracteres
        """
        await self.input(selector, text, timeout, char_delay, clear=True)

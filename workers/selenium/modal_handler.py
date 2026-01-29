"""
Modal Handler - Manejo de alertas, modales y loaders.

Módulo para detectar y cerrar modales, aceptar alertas, y esperar a que desaparezcan loaders.
"""

import asyncio
import logging
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoAlertPresentException

logger = logging.getLogger(__name__)


class ModalHandler:
    """
    Manejador de alertas, modales y loaders.
    
    Uso:
        handler = ModalHandler(selenium_driver_manager)
        
        # Esperar y aceptar alerta
        if await handler.wait_for_alert(timeout=5):
            await handler.accept_alert()
        
        # Cerrar modal por selector
        await handler.close_modal("[id='modal-close']")
        
        # Esperar a que desaparezca loader
        await handler.wait_for_loader_disappear("[class='spinner']")
    """
    
    def __init__(self, selenium_manager):
        """
        Inicializar handler de modales.
        
        Args:
            selenium_manager: Instancia de SeleniumDriverManager
        """
        self.selenium = selenium_manager
        self.logger = logging.getLogger(f"{__name__}.{selenium_manager.bot_id}")
    
    async def wait_for_alert(self, timeout: int = 5) -> bool:
        """
        Esperar a que aparezca una alerta de JavaScript.
        
        Args:
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            True si aparece alerta, False si timeout
        """
        try:
            self.logger.debug("Esperando alerta de JavaScript...")
            
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            wait = WebDriverWait(self.selenium.driver, timeout)
            await asyncio.to_thread(wait.until, EC.alert_is_present())
            
            self.logger.debug("Alerta detectada")
            return True
            
        except TimeoutException:
            self.logger.debug("Timeout esperando alerta")
            return False
        except Exception as e:
            self.logger.debug(f"Error esperando alerta: {e}")
            return False
    
    async def get_alert_text(self) -> Optional[str]:
        """
        Obtener texto de la alerta actual.
        
        Returns:
            Texto de la alerta, o None si no hay alerta
        """
        try:
            alert = await asyncio.to_thread(lambda: self.selenium.driver.switch_to.alert)
            text = await asyncio.to_thread(lambda: alert.text)
            self.logger.debug(f"Texto de alerta: {text}")
            return text
        except NoAlertPresentException:
            return None
        except Exception as e:
            self.logger.warning(f"Error obteniendo texto de alerta: {e}")
            return None
    
    async def accept_alert(self) -> None:
        """Aceptar (OK) la alerta actual."""
        try:
            alert = await asyncio.to_thread(lambda: self.selenium.driver.switch_to.alert)
            await asyncio.to_thread(alert.accept)
            self.logger.debug("Alerta aceptada")
        except NoAlertPresentException:
            self.logger.warning("No hay alerta para aceptar")
        except Exception as e:
            self.logger.error(f"Error aceptando alerta: {e}")
    
    async def dismiss_alert(self) -> None:
        """Rechazar (Cancelar) la alerta actual."""
        try:
            alert = await asyncio.to_thread(lambda: self.selenium.driver.switch_to.alert)
            await asyncio.to_thread(alert.dismiss)
            self.logger.debug("Alerta rechazada")
        except NoAlertPresentException:
            self.logger.warning("No hay alerta para rechazar")
        except Exception as e:
            self.logger.error(f"Error rechazando alerta: {e}")
    
    async def send_alert_text(self, text: str) -> None:
        """
        Enviar texto a un prompt de alerta.
        
        Args:
            text: Texto a enviar
        """
        try:
            alert = await asyncio.to_thread(lambda: self.selenium.driver.switch_to.alert)
            await asyncio.to_thread(alert.send_keys, text)
            self.logger.debug(f"Texto enviado a alerta: {text}")
        except NoAlertPresentException:
            self.logger.warning("No hay alerta para enviar texto")
        except Exception as e:
            self.logger.error(f"Error enviando texto a alerta: {e}")
    
    async def close_modal(self, close_button_selector: str, timeout: int = 10) -> bool:
        """
        Cerrar modal clickeando botón de cierre.
        
        Args:
            close_button_selector: CSS selector del botón de cierre
            timeout: Tiempo máximo de espera
        
        Returns:
            True si se cerró exitosamente, False si no se encontró botón
        """
        try:
            self.logger.debug(f"Cerrando modal: {close_button_selector}")
            
            close_btn = await self.selenium.wait_for(
                By.CSS_SELECTOR,
                close_button_selector,
                timeout=timeout
            )
            
            await self.selenium.click(close_btn)
            await asyncio.sleep(0.5)
            
            self.logger.debug("Modal cerrado")
            return True
            
        except TimeoutException:
            self.logger.debug(f"Botón de cierre no encontrado: {close_button_selector}")
            return False
        except Exception as e:
            self.logger.error(f"Error cerrando modal: {e}")
            return False
    
    async def wait_for_loader_disappear(
        self,
        loader_selector: str,
        timeout: int = 30
    ) -> bool:
        """
        Esperar a que desaparezca un loader/spinner.
        
        Args:
            loader_selector: CSS selector del elemento loader
            timeout: Tiempo máximo de espera
        
        Returns:
            True si desapareció, False si timeout
        """
        try:
            self.logger.debug(f"Esperando que desaparezca loader: {loader_selector}")
            
            await self.selenium.wait_for(
                By.CSS_SELECTOR,
                loader_selector,
                timeout=timeout,
                condition="invisible"
            )
            
            self.logger.debug("Loader desapareció")
            return True
            
        except TimeoutException:
            self.logger.warning(f"Timeout esperando que desaparezca loader")
            return False
        except Exception as e:
            self.logger.error(f"Error esperando loader: {e}")
            return False
    
    async def wait_for_modal_appear(
        self,
        modal_selector: str,
        timeout: int = 10
    ) -> bool:
        """
        Esperar a que aparezca un modal.
        
        Args:
            modal_selector: CSS selector del modal
            timeout: Tiempo máximo de espera
        
        Returns:
            True si aparece, False si timeout
        """
        try:
            self.logger.debug(f"Esperando que aparezca modal: {modal_selector}")
            
            await self.selenium.wait_for(
                By.CSS_SELECTOR,
                modal_selector,
                timeout=timeout,
                condition="visible"
            )
            
            self.logger.debug("Modal apareció")
            return True
            
        except TimeoutException:
            self.logger.debug(f"Timeout esperando modal")
            return False
        except Exception as e:
            self.logger.error(f"Error esperando modal: {e}")
            return False
    
    async def wait_for_modal_disappear(
        self,
        modal_selector: str,
        timeout: int = 10
    ) -> bool:
        """
        Esperar a que desaparezca un modal.
        
        Args:
            modal_selector: CSS selector del modal
            timeout: Tiempo máximo de espera
        
        Returns:
            True si desaparece, False si timeout
        """
        try:
            self.logger.debug(f"Esperando que desaparezca modal: {modal_selector}")
            
            await self.selenium.wait_for(
                By.CSS_SELECTOR,
                modal_selector,
                timeout=timeout,
                condition="invisible"
            )
            
            self.logger.debug("Modal desapareció")
            return True
            
        except TimeoutException:
            self.logger.debug(f"Timeout esperando que desaparezca modal")
            return False
        except Exception as e:
            self.logger.error(f"Error esperando modal: {e}")
            return False

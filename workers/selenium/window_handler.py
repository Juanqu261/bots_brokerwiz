"""
Window Handler - Manejo de ventanas y tabs.

Módulo para cambiar entre ventanas, esperar nuevas ventanas, y cerrar ventanas.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WindowHandler:
    """
    Manejador de ventanas y tabs.
    
    Uso:
        handler = WindowHandler(selenium_driver_manager)
        
        # Esperar nueva ventana
        await handler.wait_for_new_window(timeout=10)
        await handler.switch_to_new_window()
        
        # Cambiar por título
        await handler.switch_to_window_by_title("Cotización")
        
        # Cerrar ventana actual
        await handler.close_current_window()
    """
    
    def __init__(self, selenium_manager):
        """
        Inicializar handler de ventanas.
        
        Args:
            selenium_manager: Instancia de SeleniumDriverManager
        """
        self.selenium = selenium_manager
        self.logger = logging.getLogger(f"{__name__}.{selenium_manager.bot_id}")
    
    async def wait_for_new_window(self, timeout: int = 10) -> bool:
        """
        Esperar a que se abra una nueva ventana.
        
        Args:
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            True si se abre nueva ventana, False si timeout
        """
        try:
            self.logger.debug("Esperando nueva ventana...")
            
            initial_handles = await self.selenium.get_window_handles()
            initial_count = len(initial_handles)
            
            start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start) < timeout:
                current_handles = await self.selenium.get_window_handles()
                
                if len(current_handles) > initial_count:
                    self.logger.debug(f"Nueva ventana detectada (total: {len(current_handles)})")
                    return True
                
                await asyncio.sleep(0.5)
            
            self.logger.warning(f"Timeout esperando nueva ventana ({timeout}s)")
            return False
            
        except Exception as e:
            self.logger.error(f"Error esperando nueva ventana: {e}")
            return False
    
    async def switch_to_new_window(self) -> bool:
        """
        Cambiar a la ventana más recientemente abierta.
        
        Returns:
            True si se cambió exitosamente, False si no hay nueva ventana
        """
        try:
            self.logger.debug("Cambiando a nueva ventana...")
            
            handles = await self.selenium.get_window_handles()
            
            if len(handles) < 2:
                self.logger.warning("No hay nueva ventana para cambiar")
                return False
            
            # Cambiar a la última ventana (la más reciente)
            new_window = handles[-1]
            await self.selenium.switch_to_window(new_window)
            
            await asyncio.sleep(0.5)
            
            self.logger.debug(f"Cambiado a nueva ventana: {new_window}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cambiando a nueva ventana: {e}")
            return False
    
    async def switch_to_window_by_title(self, title: str, timeout: int = 10) -> bool:
        """
        Cambiar a ventana por título.
        
        Args:
            title: Título (o parte del título) de la ventana
            timeout: Tiempo máximo de espera
        
        Returns:
            True si se encontró y cambió, False si no
        """
        try:
            self.logger.debug(f"Buscando ventana con título: {title}")
            
            start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start) < timeout:
                handles = await self.selenium.get_window_handles()
                
                for handle in handles:
                    await self.selenium.switch_to_window(handle)
                    current_title = await asyncio.to_thread(lambda: self.selenium.driver.title)
                    
                    if title.lower() in current_title.lower():
                        self.logger.debug(f"Ventana encontrada: {current_title}")
                        return True
                
                await asyncio.sleep(0.5)
            
            self.logger.warning(f"Ventana con título '{title}' no encontrada")
            return False
            
        except Exception as e:
            self.logger.error(f"Error buscando ventana por título: {e}")
            return False
    
    async def switch_to_window_by_url(self, url_part: str, timeout: int = 10) -> bool:
        """
        Cambiar a ventana por URL.
        
        Args:
            url_part: Parte de la URL a buscar
            timeout: Tiempo máximo de espera
        
        Returns:
            True si se encontró y cambió, False si no
        """
        try:
            self.logger.debug(f"Buscando ventana con URL: {url_part}")
            
            start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start) < timeout:
                handles = await self.selenium.get_window_handles()
                
                for handle in handles:
                    await self.selenium.switch_to_window(handle)
                    current_url = await asyncio.to_thread(lambda: self.selenium.driver.current_url)
                    
                    if url_part.lower() in current_url.lower():
                        self.logger.debug(f"Ventana encontrada: {current_url}")
                        return True
                
                await asyncio.sleep(0.5)
            
            self.logger.warning(f"Ventana con URL '{url_part}' no encontrada")
            return False
            
        except Exception as e:
            self.logger.error(f"Error buscando ventana por URL: {e}")
            return False
    
    async def close_current_window(self) -> bool:
        """
        Cerrar la ventana actual.
        
        Returns:
            True si se cerró exitosamente
        """
        try:
            self.logger.debug("Cerrando ventana actual...")
            
            await asyncio.to_thread(self.selenium.driver.close)
            
            # Cambiar a la primera ventana disponible
            handles = await self.selenium.get_window_handles()
            if handles:
                await self.selenium.switch_to_window(handles[0])
            
            self.logger.debug("Ventana cerrada")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cerrando ventana: {e}")
            return False
    
    async def close_all_windows_except_main(self) -> int:
        """
        Cerrar todas las ventanas excepto la primera (principal).
        
        Returns:
            Número de ventanas cerradas
        """
        try:
            self.logger.debug("Cerrando ventanas adicionales...")
            
            handles = await self.selenium.get_window_handles()
            main_window = handles[0]
            closed_count = 0
            
            for handle in handles[1:]:
                try:
                    await self.selenium.switch_to_window(handle)
                    await asyncio.to_thread(self.selenium.driver.close)
                    closed_count += 1
                except Exception as e:
                    self.logger.warning(f"Error cerrando ventana {handle}: {e}")
            
            # Volver a ventana principal
            await self.selenium.switch_to_window(main_window)
            
            self.logger.debug(f"Cerradas {closed_count} ventanas")
            return closed_count
            
        except Exception as e:
            self.logger.error(f"Error cerrando ventanas: {e}")
            return 0
    
    async def get_window_count(self) -> int:
        """Obtener número de ventanas abiertas."""
        try:
            handles = await self.selenium.get_window_handles()
            return len(handles)
        except Exception as e:
            self.logger.error(f"Error obteniendo número de ventanas: {e}")
            return 0

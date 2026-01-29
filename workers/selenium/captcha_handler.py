"""
Captcha Handler - Resolución de captchas usando API 2Captcha.

Módulo para capturar, enviar y resolver captchas de forma asíncrona.
"""

import asyncio
import base64
import logging
from typing import Optional

import httpx
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


class CaptchaHandler:
    """
    Manejador de captchas con integración a 2Captcha API.
    
    Uso:
        handler = CaptchaHandler(selenium_driver_manager)
        captcha_text = await handler.resolve_captcha(
            api_key="...",
            captcha_selector="[id='captcha-image']",
            input_selector="[id='captcha-input']"
        )
    """
    
    def __init__(self, selenium_manager):
        """
        Inicializar handler de captcha.
        
        Args:
            selenium_manager: Instancia de SeleniumDriverManager
        """
        self.selenium = selenium_manager
        self.logger = logging.getLogger(f"{__name__}.{selenium_manager.bot_id}")
    
    async def capture_captcha_image(self, selector: str) -> Optional[str]:
        """
        Capturar imagen del captcha y convertir a base64.
        
        Args:
            selector: CSS selector del elemento de imagen del captcha
        
        Returns:
            String base64 de la imagen, o None si falla
        """
        try:
            self.logger.debug(f"Capturando captcha: {selector}")
            
            # Esperar elemento
            captcha_elem = await self.selenium.wait_for(
                By.CSS_SELECTOR,
                selector,
                timeout=10
            )
            
            # Tomar screenshot del elemento (usar el driver directamente)
            loop = asyncio.get_running_loop()
            
            def _screenshot():
                return captcha_elem.screenshot_as_png
            
            img_bytes = await loop.run_in_executor(None, _screenshot)
            
            # Convertir a base64
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            self.logger.debug("Captcha capturado y convertido a base64")
            return img_base64
            
        except Exception as e:
            self.logger.error(f"Error capturando captcha: {e}")
            return None
    
    async def send_to_2captcha(
        self,
        api_key: str,
        image_base64: str,
        language: str = "en"
    ) -> Optional[dict]:
        """
        Enviar imagen a API 2Captcha para resolución.
        
        Args:
            api_key: API key de 2Captcha
            image_base64: Imagen en base64
            language: Idioma del captcha (default: "en")
        
        Returns:
            Dict con taskId, o None si falla
        """
        try:
            self.logger.debug("Enviando captcha a API 2Captcha...")
            
            url = "https://api.2captcha.com/createTask"
            
            payload = {
                "clientKey": api_key,
                "task": {
                    "type": "ImageToTextTask",
                    "body": image_base64
                },
                "languagePool": language
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                result = response.json()
            
            if result.get("errorId") != 0:
                error_desc = result.get("errorDescription", "Error desconocido")
                self.logger.error(f"Error en 2Captcha: {error_desc}")
                return None
            
            task_id = result.get("taskId")
            if not task_id:
                self.logger.error("No se obtuvo task_id de 2Captcha")
                return None
            
            self.logger.debug(f"Tarea de captcha creada: {task_id}")
            return {"taskId": task_id}
            
        except Exception as e:
            self.logger.error(f"Error enviando a 2Captcha: {e}")
            return None
    
    async def wait_for_resolution(
        self,
        api_key: str,
        task_id: int,
        max_attempts: int = 30,
        retry_delay: tuple = (3, 5)
    ) -> Optional[str]:
        """
        Esperar resolución del captcha con reintentos.
        Llena automáticamente el campo de entrada si se resuelve.
        
        Args:
            api_key: API key de 2Captcha
            task_id: ID de la tarea
            max_attempts: Máximo número de intentos
            retry_delay: Tupla (min, max) de segundos entre intentos
        
        Returns:
            Texto del captcha resuelto, o None si timeout
        """
        import random
        
        try:
            url = "https://api.2captcha.com/getTaskResult"
            
            for intento in range(1, max_attempts + 1):
                # Esperar con delay aleatorio (simula humano)
                delay = random.uniform(retry_delay[0], retry_delay[1])
                await asyncio.sleep(delay)
                
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            url,
                            json={
                                "clientKey": api_key,
                                "taskId": task_id
                            }
                        )
                        result = response.json()
                except Exception as e:
                    self.logger.debug(f"Error consultando resultado (intento {intento}): {e}")
                    continue
                
                if result.get("errorId") != 0:
                    self.logger.debug(f"Captcha no resuelto aún (intento {intento}/{max_attempts})")
                    continue
                
                captcha_text = result.get("solution", {}).get("text", "")
                if captcha_text:
                    self.logger.info(f"Captcha resuelto en intento {intento}: {captcha_text}")
                    
                    # Llenar campo de captcha automáticamente
                    try:
                        captcha_input = await self.selenium.wait_for(
                            By.CSS_SELECTOR,
                            "#captchaInput",  # Selector por defecto
                            timeout=5
                        )
                        await self.selenium.type_text(captcha_input, captcha_text)
                        self.logger.info(f"Captcha llenado en campo de entrada")
                    except Exception as e:
                        self.logger.warning(f"No se pudo llenar campo de captcha: {e}")
                    
                    return captcha_text
            
            self.logger.error(f"Timeout esperando resolución de captcha ({max_attempts} intentos)")
            return None
            
        except Exception as e:
            self.logger.error(f"Error esperando resolución: {e}")
            return None
    
    async def resolve_captcha(
        self,
        api_key: str,
        captcha_selector: str,
        input_selector: Optional[str] = None,
        language: str = "en"
    ) -> Optional[str]:
        """
        Resolver captcha completo: capturar → enviar → esperar → llenar.
        
        Args:
            api_key: API key de 2Captcha
            captcha_selector: CSS selector de la imagen del captcha
            input_selector: CSS selector del campo de entrada (opcional)
            language: Idioma del captcha
        
        Returns:
            Texto del captcha resuelto, o None si falla
        """
        try:
            # Paso 1: Capturar imagen
            image_base64 = await self.capture_captcha_image(captcha_selector)
            if not image_base64:
                return None
            
            # Paso 2: Enviar a 2Captcha
            task_info = await self.send_to_2captcha(api_key, image_base64, language)
            if not task_info:
                return None
            
            # Paso 3: Esperar resolución
            captcha_text = await self.wait_for_resolution(api_key, task_info["taskId"])
            if not captcha_text:
                return None
            
            # Paso 4: Llenar campo si se proporciona selector
            if input_selector:
                try:
                    input_elem = await self.selenium.wait_for(
                        By.CSS_SELECTOR,
                        input_selector,
                        timeout=5
                    )
                    await self.selenium.type_text(input_elem, captcha_text)
                    self.logger.info("Captcha llenado en campo de entrada")
                except Exception as e:
                    self.logger.warning(f"No se pudo llenar campo de captcha: {e}")
                    # Retornar el texto de todas formas
            
            return captcha_text
            
        except Exception as e:
            self.logger.error(f"Error resolviendo captcha: {e}")
            return None

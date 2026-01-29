"""
Captcha Handler - Resolución de captchas usando API 2Captcha.

Módulo para capturar, enviar y resolver captchas de forma asíncrona.
"""

import asyncio
import base64
import logging
import random
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
        max_attempts: int = 20,
        retry_delay: int = 10,
        max_retries: int = 10,
        captcha_input_selector: str = None,
        login_button_selector: str = None,
        refresh_button_selector: str = None,
        captcha_image_selector: str = None
    ) -> Optional[str]:
        """
        Esperar resolución del captcha con reintentos y validación.
        
        Valida:
        1. Longitud del captcha (debe ser 6 caracteres)
        2. Disponibilidad del botón de login (intenta llenar y verifica)
        
        Si falla la validación, regenera el captcha y reintenta.
        
        Args:
            api_key: API key de 2Captcha
            task_id: ID de la tarea
            max_attempts: Máximo número de intentos de consulta
            retry_delay: Segundos entre cada intento
            max_retries: Máximo de veces que se puede regenerar el captcha
            captcha_input_selector: Selector del campo de entrada del captcha
            login_button_selector: Selector del botón de login
            refresh_button_selector: Selector del botón para refrescar captcha
            captcha_image_selector: Selector de la imagen del captcha
        
        Returns:
            Texto del captcha resuelto, o None si timeout
        """
        try:
            from workers.bots.ui_elements.sbs_ui_elements import SBSUIElements
            
            # Usar selectores por defecto si no se proporcionan
            captcha_input_selector = captcha_input_selector or SBSUIElements.INPUT_CAPTCHA
            login_button_selector = login_button_selector or SBSUIElements.BUTTON_LOGIN
            refresh_button_selector = refresh_button_selector or SBSUIElements.BUTTON_REFRESH_CAPTCHA
            captcha_image_selector = captcha_image_selector or SBSUIElements.CAPTCHA_IMAGE
            
            url = "https://api.2captcha.com/getTaskResult"
            current_task_id = task_id
            retry_count = 0
            
            for intento in range(1, max_attempts + 1):
                self.logger.debug(f"Intento {intento}/{max_attempts} - Consultando resultado")
                
                # Esperar antes de consultar
                await asyncio.sleep(retry_delay)
                
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            url,
                            json={
                                "clientKey": api_key,
                                "taskId": current_task_id
                            }
                        )
                        result = response.json()
                except Exception as e:
                    self.logger.debug(f"Error consultando resultado: {e}")
                    continue
                
                # Verificar si hay error en la API
                if result.get("errorId", 0) != 0:
                    self.logger.debug(f"Error API: {result.get('errorDescription')}")
                    continue
                
                # Verificar estado
                status = result.get("status")
                
                if status == "ready":
                    captcha_text = result.get("solution", {}).get("text", "")
                    self.logger.debug(f"Captcha resuelto: '{captcha_text}'")
                    
                    # === VALIDACIÓN 1: Longitud ===
                    if len(captcha_text) == 6:
                        # === VALIDACIÓN 2: Disponibilidad del botón ===
                        try:
                            # Llenar campo de captcha
                            captcha_input = await self.selenium.wait_for(
                                By.CSS_SELECTOR,
                                captcha_input_selector,
                                timeout=3
                            )
                            await self.selenium.type_text(captcha_input, captcha_text)
                            
                            # Click en pantalla para confirmar
                            body = await self.selenium.wait_for(
                                By.CSS_SELECTOR,
                                "body",
                                timeout=1
                            )
                            await self.selenium.click(body)
                            
                            # Verificar que el botón de login sea clickable
                            login_btn = await self.selenium.wait_for(
                                By.CSS_SELECTOR,
                                login_button_selector,
                                condition="clickable",
                                timeout=3
                            )
                            
                            self.logger.info(f"Captcha validado y botón disponible: {captcha_text}")
                            return captcha_text
                            
                        except Exception as e:
                            self.logger.warning(f"Botón de login no disponible: {e}")
                            
                            if retry_count >= max_retries:
                                self.logger.error(f"Se alcanzó el máximo de reintentos ({max_retries})")
                                return None
                            
                            retry_count += 1
                            self.logger.info(f"Reintento {retry_count}/{max_retries} - Regenerando captcha...")
                            
                            # Regenerar captcha
                            current_task_id = await self._regenerate_captcha(
                                api_key,
                                refresh_button_selector,
                                captcha_image_selector
                            )
                            if not current_task_id:
                                return None
                            
                            intento = 0
                            continue
                    
                    else:
                        # Captcha con longitud incorrecta
                        self.logger.warning(
                            f"Captcha con longitud incorrecta: '{captcha_text}' "
                            f"(esperado: 6, obtenido: {len(captcha_text)})"
                        )
                        
                        if retry_count >= max_retries:
                            self.logger.error(f"Se alcanzó el máximo de reintentos ({max_retries})")
                            return None
                        
                        retry_count += 1
                        self.logger.info(f"Reintento {retry_count}/{max_retries} - Regenerando captcha...")
                        
                        # Regenerar captcha
                        current_task_id = await self._regenerate_captcha(
                            api_key,
                            refresh_button_selector,
                            captcha_image_selector
                        )
                        if not current_task_id:
                            return None
                        
                        intento = 0
                        continue
                
                elif status == "processing":
                    self.logger.debug(f"Estado: procesando... esperando {retry_delay}s")
                    continue
                
                else:
                    self.logger.debug(f"Estado desconocido: {status}")
                    continue
            
            self.logger.error(f"Timeout esperando resolución de captcha ({max_attempts} intentos)")
            return None
            
        except Exception as e:
            self.logger.error(f"Error esperando resolución: {e}")
            return None
    
    async def _regenerate_captcha(
        self,
        api_key: str,
        refresh_button_selector: str = None,
        captcha_image_selector: str = None
    ) -> Optional[int]:
        """
        Regenerar captcha: refrescar UI y crear nueva tarea.
        
        Args:
            api_key: API key de 2Captcha
            refresh_button_selector: Selector del botón para refrescar
            captcha_image_selector: Selector de la imagen del captcha
        
        Returns:
            ID de la nueva tarea, o None si falla
        """
        try:
            from workers.bots.ui_elements.sbs_ui_elements import SBSUIElements
            
            refresh_button_selector = refresh_button_selector or SBSUIElements.BUTTON_REFRESH_CAPTCHA
            captcha_image_selector = captcha_image_selector or SBSUIElements.CAPTCHA_IMAGE
            
            # Refrescar captcha en la UI
            refresh_btn = await self.selenium.wait_for(
                By.CSS_SELECTOR,
                refresh_button_selector,
                condition="clickable",
                timeout=5
            )
            await self.selenium.click(refresh_btn)
            
            # Pausa aleatoria (simula humano)
            await self.selenium.human.pause(3, 6)
            
            # Capturar nueva imagen
            image_base64 = await self.capture_captcha_image(captcha_image_selector)
            if not image_base64:
                self.logger.error("No se pudo capturar nueva imagen de captcha")
                return None
            
            # Crear nueva tarea
            task_info = await self.send_to_2captcha(api_key, image_base64)
            if not task_info or not task_info.get("taskId"):
                self.logger.error("No se pudo crear nueva tarea de captcha")
                return None
            
            self.logger.debug(f"Nueva tarea de captcha creada: {task_info['taskId']}")
            return task_info["taskId"]
            
        except Exception as e:
            self.logger.error(f"Error regenerando captcha: {e}")
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

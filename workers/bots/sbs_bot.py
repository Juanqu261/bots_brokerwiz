"""
SBS Bot - Bot de cotización para SBS Seguros.

Flujo de cotización:
1. Inicializar driver
2. Login (usuario + contraseña + captcha)
3. Navegación (menu seguros → autos)
4. Formulario de cotización (datos del vehículo)
5. Seleccionar opciones (coberturas)
6. Seleccionar plan (PREMIUM, ESTANDAR, BASICO)
7. Descargar PDF
8. Subir PDF a API
"""

import os
import asyncio
from dotenv import load_dotenv

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from workers.bots import BaseBot
from workers.bots.ui_elements.sbs_ui_elements import SBSUIElements
from workers.selenium import CaptchaHandler, ModalHandler, WindowHandler

# Cargar variables de entorno
load_dotenv()


class SBSBot(BaseBot):
    """
    Bot de cotización para SBS Seguros.
    
    Hereda de BaseBot que proporciona:
        - self.selenium: Driver manager con helpers
        - self.api: Cliente HTTP para upload de PDFs
        - self.logger: Logger configurado
        - self.payload: Datos de cotización desde MQTT
    """
    
    # URLs del portal SBS
    URL_LOGIN = "https://tu.sbseguros.co/escritorio-virtual/"
    
    # Dominio para cookies
    COOKIE_DOMAIN = "tu.sbseguros.co"

    # Mapa de planes a selectores
    PLAN_SELECTOR_MAP = {
        "PREMIUM": SBSUIElements.BUTTON_PREMIUM,
        "ESTANDAR": SBSUIElements.BUTTON_ESTANDAR,
        "BASICO": SBSUIElements.BUTTON_BASICO,
    }
    
    def __init__(self, job_id: str, payload: dict):
        """
        Inicializar bot SBS.
        
        Args:
            job_id: ID único del job
            payload: Datos de cotización desde MQTT
        """
        super().__init__(bot_id="sbs", job_id=job_id, payload=payload)
        
        # Inicializar handlers especializados
        self.captcha_handler = CaptchaHandler(self.selenium)
        self.modal_handler = ModalHandler(self.selenium)
        self.window_handler = WindowHandler(self.selenium)
        
        # Mapa de planes
        self.PLAN_SELECTOR_MAP = {
            "PREMIUM": SBSUIElements.BUTTON_PREMIUM,
            "ESTANDAR": SBSUIElements.BUTTON_ESTANDAR,
            "BASICO": SBSUIElements.BUTTON_BASICO,
        }
    
    async def run(self) -> bool:
        """
        Ejecutar el flujo completo de cotización SBS.
        
        Sigue la estructura exacta del bot_executor.py original.
        
        Returns:
            True si la cotización fue exitosa y el PDF se subió
        """
        try:
            # Navegar a URL de login
            await self.selenium.get(self.URL_LOGIN)
            await self.selenium.human.pause(3, 6)
            
            # Intentar cargar cookies de sesión anterior
            cookies_loaded = await self.selenium.load_cookies(self.COOKIE_DOMAIN)
            if cookies_loaded:
                self.logger.info("Cookies de sesión anterior cargadas, refrescando página...")
                await self.selenium.refresh()
                await self.selenium.wait_page_load()
                
                # Verificar si la sesión es válida
                try:
                    await self.selenium.wait_for(
                        By.CSS_SELECTOR,
                        SBSUIElements.MENU_SEGUROS,
                        timeout=5
                    )
                    self.logger.info("Sesión restaurada exitosamente, saltando login")
                    # Saltar al flujo de cotización
                    await self.selenium.human.pause(2, 4)
                    await self.selenium.human.click(SBSUIElements.BUTTON_CERRAR_VENTANA)
                    await self.selenium.human.click(SBSUIElements.MENU_SEGUROS)
                    await self.selenium.human.click(SBSUIElements.LINK_AUTOS_MOTOS)
                    await self.selenium.human.click(SBSUIElements.BUTTON_COTIZAR)
                    await self.window_handler.wait_for_new_window()
                    await self.window_handler.switch_to_new_window()
                    return await self._complete_quotation(self.payload)
                except:
                    self.logger.debug("Sesión expirada, requiere nuevo login")
            
            # === LOGIN ===
            payload = self.payload
            
            # Llenar usuario
            await self.selenium.human.input(
                SBSUIElements.INPUT_USERNAME,
                payload.get("in_strUsuarioAsesor", "")
            )
            
            # Llenar contraseña
            await self.selenium.human.input(
                SBSUIElements.INPUT_PASSWORD,
                payload.get("in_strContrasenaAsesor", "")
            )
            
            # Resolver captcha
            api_key = os.getenv("API_KEY_2CAPTCHA")
            if api_key:
                try:
                    self.logger.info("Iniciando resolución de captcha...")
                    
                    # Capturar imagen
                    imagen = await self.captcha_handler.capture_captcha_image(
                        SBSUIElements.CAPTCHA_IMAGE
                    )
                    if imagen:
                        # Crear tarea
                        crear_captcha = await self.captcha_handler.send_to_2captcha(
                            api_key=api_key,
                            image_base64=imagen
                        )
                        self.logger.debug(f"Tarea de captcha creada: {crear_captcha}")
                        
                        if crear_captcha and crear_captcha.get("taskId"):
                            # Esperar resolución con validación y reintentos
                            captcha_text = await self.captcha_handler.wait_for_resolution(
                                api_key=api_key,
                                task_id=crear_captcha["taskId"],
                                max_attempts=20,
                                retry_delay=10,
                                max_retries=10,
                                captcha_input_selector=SBSUIElements.INPUT_CAPTCHA,
                                login_button_selector=SBSUIElements.BUTTON_LOGIN,
                                refresh_button_selector=SBSUIElements.BUTTON_REFRESH_CAPTCHA,
                                captcha_image_selector=SBSUIElements.CAPTCHA_IMAGE
                            )
                            
                            if not captcha_text:
                                self.logger.warning("No se pudo resolver el captcha")
                                await self.report_error("CAPTCHA_001", "No se pudo resolver el captcha después de múltiples intentos")
                                return False
                        else:
                            self.logger.warning("No se obtuvo taskId del captcha")
                            await self.report_error("CAPTCHA_002", "Error al crear tarea de captcha")
                            return False
                    else:
                        self.logger.warning("No se pudo capturar la imagen del captcha")
                        await self.report_error("CAPTCHA_003", "No se pudo capturar la imagen del captcha")
                        return False
                        
                except Exception as e:
                    self.logger.warning(f"Error resolviendo captcha: {e}")
                    await self.report_error("CAPTCHA_ERROR", str(e))
                    return False
            else:
                self.logger.warning("API_KEY_2CAPTCHA no configurada en variables de entorno")
                await self.report_error("CONFIG_001", "API_KEY_2CAPTCHA no configurada")
                return False
            
            # Click en login
            await self.selenium.human.click(SBSUIElements.BUTTON_LOGIN)
            
            # === VALIDACIÓN DEL LOGIN ===
            resultado_login = await self._verificar_login()
            if resultado_login == "ERROR_CREDENCIALES":
                await self.report_error("AUTH_001", "Credenciales inválidas: usuario o contraseña incorrectos")
                return False
            
            if resultado_login != "OK":
                await self.report_error("AUTH_002", "No se pudo determinar el estado del login")
                return False
            
            # Guardar cookies de sesión para futuras ejecuciones
            await self.selenium.save_cookies()
            self.logger.info("Cookies de sesión guardadas")
            
            await self.selenium.human.pause(3, 6)
            
            # === NAVEGACIÓN Y COTIZACIÓN ===
            await self.selenium.human.click(SBSUIElements.BUTTON_CERRAR_VENTANA)
            await self.selenium.human.click(SBSUIElements.MENU_SEGUROS)
            await self.selenium.human.click(SBSUIElements.LINK_AUTOS_MOTOS)
            await self.selenium.human.click(SBSUIElements.BUTTON_COTIZAR)
            
            # Cambiar a nueva ventana
            await self.window_handler.wait_for_new_window()
            await self.window_handler.switch_to_new_window()
            
            return await self._complete_quotation(payload)
            
        except Exception as e:
            self.logger.exception(f"Error inesperado en SBSBot: {e}")
            await self.report_error("BOT_EXCEPTION", str(e), severity="CRITICAL")
            return False
    
    # === Métodos privados del flujo ===
    
    async def _complete_quotation(self, payload: dict) -> bool:
        """
        Completar el flujo de cotización (después del login).
        
        Args:
            payload: Datos de cotización
        
        Returns:
            True si la cotización fue exitosa
        """
        try:
            # === FORMULARIO PRINCIPAL ===
            await self.selenium.human.input(
                SBSUIElements.INPUT_IDENTIFICACION,
                payload.get("in_strNumDoc", "")
            )
            await self.selenium.human.input(
                SBSUIElements.INPUT_PLACA,
                payload.get("in_strPlaca", "")
            )
            await self.selenium.human.click(SBSUIElements.BUTTON_CONSULTAR)
            await self.selenium.human.pause(2, 5)
            
            await self.selenium.human.input(
                SBSUIElements.INPUT_CELULAR,
                payload.get("in_strCelular", "")
            )
            await self.selenium.human.input(
                SBSUIElements.INPUT_EMAIL,
                payload.get("in_strEmail", "")
            )
            
            await self._click_checkbox(SBSUIElements.BUTTON_RESPONSABILIDAD_CIVIL_NO)
            await self.selenium.human.pause(3, 5)
            await self._click_checkbox(SBSUIElements.BUTTON_BICICLETA_NO)
            
            # === ESPERAR TABLA DE COTIZACIÓN ===
            ok = await self._esperar_tabla_cotizacion()
            if not ok:
                await self.report_error("QUOTE_001", "No apareció la tabla de cotización en el tiempo esperado")
                return False
            
            # === SELECCIONAR COBERTURAS ===
            await self._click_checkbox(SBSUIElements.BUTTON_GASTOS)
            await self._click_checkbox(SBSUIElements.BUTTON_LLANTAS_ESTALLADAS)
            await self._click_checkbox(SBSUIElements.BUTTON_PEQUEÑOS_ACCESORIOS)
            await self._click_checkbox(SBSUIElements.BUTTON_ACCIDENTES_PERSONALES)
            await self._click_checkbox(SBSUIElements.BUTTON_REMPLAZO_LLAVES)
            
            # === SELECCIONAR PLAN ===
            await self._seleccionar_plan(payload.get("in_strPlan", "ESTANDAR"))
            
            # === DESCARGAR PDF ===
            await self.selenium.human.click(SBSUIElements.BUTTON_COTIZAR2)
            
            # Contar PDFs ANTES de hacer click en descargar
            # Esto es crítico: el PDF se descarga muy rápido
            initial_pdf_count = len(list(self.selenium.TEMP_PDF_DIR.glob("*.pdf")))
            self.logger.debug(f"PDFs antes de descargar: {initial_pdf_count}")
            
            await self.selenium.human.click(SBSUIElements.BUTTON_DESCARGAR_PDF)
            
            # Esperar PDF (pasando el conteo inicial)
            pdf_path = await self.selenium.wait_for_download(
                timeout=90, 
                extension=".pdf",
                initial_count=initial_pdf_count
            )
            if not pdf_path:
                await self.report_error("PDF_001", "No se pudo descargar el PDF")
                return False
            
            # === SUBIR PDF ===
            upload_ok = await self.upload_result(pdf_path)
            
            self.logger.info("Bot finalizado correctamente")
            return upload_ok
            
        except Exception as e:
            self.logger.exception(f"Error en flujo de cotización: {e}")
            await self.report_error("QUOTE_FLOW_ERROR", str(e))
            return False

    
    async def _verificar_login(self, timeout: int = 8) -> str:
        """
        Verifica si el login fue exitoso o fallido.
        
        Returns:
            - "OK": Login exitoso
            - "ERROR_CREDENCIALES": Credenciales inválidas
            - "ESTADO_DESCONOCIDO": No se pudo determinar
        """
        loop = asyncio.get_running_loop()
        
        def _verificar():
            wait = WebDriverWait(self.driver, timeout)
            
            # Verificar error de credenciales
            try:
                wait.until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, SBSUIElements.PANTALLA_ERROR_CREDENCIALES)
                    )
                )
                return "ERROR_CREDENCIALES"
            except TimeoutException:
                pass
            
            # Verificar que estamos logueados (menú visible)
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, SBSUIElements.MENU_SEGUROS)
                    )
                )
                return "OK"
            except TimeoutException:
                pass
            
            return "ESTADO_DESCONOCIDO"
        
        return await loop.run_in_executor(None, _verificar)
    
    async def _esperar_tabla_cotizacion(self, timeout: int = 60) -> bool:
        """
        Esperar a que aparezca la tabla de cotización con filas.
        
        Returns:
            True si la tabla apareció con filas, False si timeout
        """
        loop = asyncio.get_running_loop()
        
        def _wait():
            try:
                wait = WebDriverWait(self.driver, timeout)
                
                # Esperar que la tabla sea visible
                wait.until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, SBSUIElements.TABLE_COTIZACION)
                    )
                )
                
                # Esperar que tenga filas reales (más de 1)
                wait.until(
                    lambda d: len(
                        d.find_elements(
                            By.XPATH,
                            f"//table[@id='ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_tblValoresPlanCoti']//tr"
                        )
                    ) > 1
                )
                
                return True
            except TimeoutException:
                return False
        
        return await loop.run_in_executor(None, _wait)
    
    async def _click_checkbox(self, checkbox_css: str, timeout: int = 60) -> None:
        """
        Click seguro en checkbox (CSS selector).
        Maneja postback ASP.NET y stale elements.
        """
        loop = asyncio.get_running_loop()
        
        def _click():
            wait = WebDriverWait(self.driver, timeout)
            
            # Esperar checkbox clickeable
            checkbox = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, checkbox_css))
            )
            
            # Click
            checkbox.click()
            
            # Esperar que el checkbox se vuelva stale (postback)
            try:
                wait.until(EC.staleness_of(checkbox))
            except TimeoutException:
                pass  # No siempre hay postback total
        
        try:
            await loop.run_in_executor(None, _click)
        except StaleElementReferenceException:
            # Reintento limpio
            await loop.run_in_executor(None, _click)
    
    async def _seleccionar_plan(self, plan: str) -> None:
        """
        Selecciona el plan según el valor recibido en el payload.
        Soporta string o lista (por errores de contrato).
        """
        if not plan:
            raise ValueError("El plan no fue enviado en la petición")
        
        # Si viene como lista, tomamos el primer elemento
        if isinstance(plan, list):
            if len(plan) == 0:
                raise ValueError("La lista de planes está vacía")
            plan = plan[0]
        
        if not isinstance(plan, str):
            raise ValueError(f"Formato de plan inválido: {type(plan)}")
        
        plan_normalizado = plan.strip().upper()
        selector = self.PLAN_SELECTOR_MAP.get(plan_normalizado)
        
        if not selector:
            raise ValueError(f"Plan no soportado: {plan_normalizado}")
        
        await self._click_checkbox(selector)
        self.logger.info(f"Plan seleccionado: {plan_normalizado}")

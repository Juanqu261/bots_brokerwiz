"""
HDI Bot - Bot de cotización para HDI Seguros.

Este bot automatiza el proceso de cotización en el portal de HDI.

Uso:
    # El worker lo instancia automáticamente cuando llega una tarea
    # pero también puede usarse directamente para testing:
    
    bot = HDIBot(job_id="test-123", payload={...})
    async with bot:
        success = await bot.run()
"""

from selenium.webdriver.common.by import By
from asyncio import sleep
from workers.bots import BaseBot


class HDIBot(BaseBot):
    """
    Bot de cotización para HDI Seguros.
    
    Hereda de BaseBot que proporciona:
        - self.selenium: Driver manager con helpers (wait_for, click, type_text, etc.)
        - self.api: Cliente HTTP para upload de PDFs y reporte de errores
        - self.logger: Logger configurado para este bot
        - self.payload: Datos de la cotización recibidos de MQTT
    """
    
    # URLs del portal HDI
    URL_LOGIN = "https://www.hdiseguros.com.co/"
    URL_COTIZADOR = "https://tuseguro.hdiseguros.com.co/seguro-todo-riesgo-carro"
    
    # Dominio para cookies
    COOKIE_DOMAIN = "hdiseguros.com.co"
    
    def __init__(self, job_id: str, payload: dict):
        """
        Inicializar bot HDI.
        
        Args:
            job_id: ID único del job (solicitudAseguradoraId)
            payload: Datos de cotización desde MQTT
        """
        super().__init__(bot_id="hdi", job_id=job_id, payload=payload)
        
        # Extraer credenciales del payload o config
        # TODO: Definir de dónde vienen las credenciales
        self._username = payload.get("credentials", {}).get("username", "")
        self._password = payload.get("credentials", {}).get("password", "")
    
    async def run(self) -> bool:
        """
        Ejecutar el flujo completo de cotización HDI.
        
        Returns:
            True si la cotización fue exitosa y el PDF se subió
        """
        try:
            # Intentar reutilizar sesión con cookies
            session_valid = await self._try_restore_session()
            
            # Si no hay sesión válida, hacer login
            if not session_valid:
                login_ok = await self._login()
                if not login_ok:
                    await self.report_error("LOGIN_FAILED", "No se pudo iniciar sesión en HDI")
                    return False
                # Guardar cookies para futuros usos
                await self.selenium.save_cookies()
            
            # Navegar al cotizador y llenar formulario
            await self._fill_quotation_form()
            
            # Descargar PDF resultante
            pdf_path = await self._download_pdf()
            if not pdf_path:
                await self.report_error("PDF_DOWNLOAD_FAILED", "No se pudo descargar el PDF")
                return False
            
            # Subir PDF a la API
            upload_ok = await self.upload_result(pdf_path)
            
            return upload_ok
            
        except Exception as e:
            self.logger.exception(f"Error inesperado en HDIBot: {e}")
            await self.report_error("BOT_EXCEPTION", str(e), severity="ERROR")
            return False
    
    # === Métodos privados del flujo ===
    
    async def _try_restore_session(self) -> bool:
        """
        Intentar restaurar sesión desde cookies guardadas.
        
        Returns:
            True si la sesión es válida y estamos logueados
        """
        self.logger.debug("Intentando restaurar sesión desde cookies...")
        
        # Navegar al dominio primero (requerido para cargar cookies)
        await self.selenium.get(self.URL_LOGIN)
        await sleep(8)
        
        # Cargar cookies si existen
        cookies_loaded = await self.selenium.load_cookies(self.COOKIE_DOMAIN)
        if not cookies_loaded:
            self.logger.debug("No hay cookies guardadas")
            return False
        
        # Refrescar para aplicar cookies
        await self.selenium.refresh()
        await self.selenium.wait_page_load()
        
        # TODO: Verificar si realmente estamos logueados
        # Ejemplo: buscar elemento que solo aparece cuando estás logueado
        # try:
        #     await self.selenium.wait_for(By.ID, "user-menu", timeout=5)
        #     self.logger.info("Sesión restaurada exitosamente")
        #     return True
        # except:
        #     self.logger.debug("Cookies expiradas, requiere nuevo login")
        #     return False
        
        return False  # TODO: Implementar verificación real
    
    async def _login(self) -> bool:
        """
        Realizar login en el portal HDI.
        
        Returns:
            True si el login fue exitoso
        """
        self.logger.info("Iniciando login en HDI...")
        
        # TODO: Implementar flujo de login
        # Ejemplo de estructura:
        #
        # await self.selenium.get(self.URL_LOGIN)
        # 
        # # Esperar y llenar usuario
        # username_input = await self.selenium.wait_for(By.ID, "txtUsuario")
        # await self.selenium.type_text(username_input, self._username)
        # 
        # # Llenar contraseña
        # password_input = await self.selenium.wait_for(By.ID, "txtPassword")
        # await self.selenium.type_text(password_input, self._password)
        # 
        # # Click en botón login
        # login_btn = await self.selenium.wait_for(By.ID, "btnLogin", condition="clickable")
        # await self.selenium.click(login_btn)
        # 
        # # Esperar redirección o elemento de dashboard
        # try:
        #     await self.selenium.wait_for_url("/dashboard", timeout=10)
        #     self.logger.info("Login exitoso")
        #     return True
        # except TimeoutException:
        #     self.logger.error("Login fallido - no redirigió al dashboard")
        #     return False
        
        return False  # TODO: Implementar login real
    
    async def _fill_quotation_form(self) -> None:
        """
        Navegar al cotizador y llenar el formulario con datos del payload.
        """
        self.logger.info("Llenando formulario de cotización...")
        
        # TODO: Implementar llenado de formulario
        # Los datos vienen en self.payload, ejemplo:
        #
        # datos = self.payload
        # 
        # await self.selenium.get(self.URL_COTIZADOR)
        # 
        # # Ejemplo: seleccionar tipo de vehículo
        # tipo_select = await self.selenium.wait_for(By.ID, "cboTipoVehiculo")
        # await self.selenium.select_by_text(tipo_select, datos.get("tipoVehiculo"))
        # 
        # # Ejemplo: llenar placa
        # placa_input = await self.selenium.wait_for(By.ID, "txtPlaca")
        # await self.selenium.type_text(placa_input, datos.get("placa"))
        # 
        # # ... más campos según el formulario de HDI
        # 
        # # Click en cotizar
        # cotizar_btn = await self.selenium.wait_for(By.ID, "btnCotizar", condition="clickable")
        # await self.selenium.click(cotizar_btn)
        # 
        # # Esperar que se genere la cotización
        # await self.selenium.wait_for(By.ID, "resultado-cotizacion", timeout=30)
        
        pass  # TODO: Implementar formulario real
    
    async def _download_pdf(self):
        """
        Descargar el PDF de la cotización.
        
        Returns:
            Path del archivo descargado, o None si falla
        """
        self.logger.info("Descargando PDF de cotización...")
        
        # TODO: Implementar descarga de PDF
        # Ejemplo:
        #
        # # Click en botón de descarga
        # download_btn = await self.selenium.wait_for(By.ID, "btnDescargarPDF", condition="clickable")
        # await self.selenium.click(download_btn)
        # 
        # # Esperar a que se complete la descarga
        # pdf_path = await self.selenium.wait_for_download(timeout=30, extension=".pdf")
        # 
        # if pdf_path:
        #     self.logger.info(f"PDF descargado: {pdf_path}")
        # 
        # return pdf_path
        
        return None  # TODO: Implementar descarga real

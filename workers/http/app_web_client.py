"""
App Web Client - Cliente HTTP async para comunicación con API BrokerWiz.

Maneja la comunicación con los endpoints de la aplicación web:
- POST /archivos-cotizacion: Subir PDFs resultantes
- POST /api/bot-errors: Reportar errores de bots
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Resultado de subida de archivo."""
    success: bool
    message: str
    data: dict = field(default_factory=dict)
    status_code: int = 0


class AppWebClient:
    """Cliente HTTP async para comunicación con API BrokerWiz."""
    
    # Endpoints
    UPLOAD_ENDPOINT = "/archivos-cotizacion"
    ERRORS_ENDPOINT = "/api/bot-errors"
    
    def __init__(self):
        """Inicializar cliente con configuración de settings."""
        self.base_url = settings.app_web.APP_WEB_BASE_URL
        self.timeout = settings.app_web.APP_WEB_UPLOAD_TIMEOUT
        
        # Configuración de retry
        self.max_retries = 2
        self.initial_wait = 5
        self.backoff_factor = 2
    
    async def upload_pdf(
        self,
        pdf_path: Path,
        solicitud_aseguradora_id: str,
        tipo_subida: str = "bot"
    ) -> UploadResult:
        """
        Subir PDF/imagen al endpoint de archivos.
        
        Endpoint: POST {base_url}/archivos-cotizacion
        Content-Type: multipart/form-data
        
        Args:
            pdf_path: Ruta al archivo PDF/imagen
            solicitud_aseguradora_id: ID de la solicitud (viene en payload del bot)
            tipo_subida: "bot" (default) o "manual"
        
        Returns:
            UploadResult con success, message, data
        """
        if not pdf_path.exists():
            return UploadResult(
                success=False,
                message=f"Archivo no encontrado: {pdf_path}",
                status_code=0
            )
        
        url = f"{self.base_url}{self.UPLOAD_ENDPOINT}"
        
        # Determinar content-type según extensión
        content_type_map = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        content_type = content_type_map.get(pdf_path.suffix.lower(), "application/octet-stream")
        
        logger.info(f"Subiendo archivo: {pdf_path.name} para solicitud {solicitud_aseguradora_id}")
        
        try:
            result = await self._post_multipart_with_retry(
                url=url,
                file_path=pdf_path,
                file_field="archivo",
                content_type=content_type,
                data={
                    "idSolicitudAseguradora": solicitud_aseguradora_id,
                    "tipoSubida": tipo_subida,
                }
            )
            
            if result.get("success"):
                logger.info(f"Archivo subido exitosamente: {result.get('data', {}).get('id')}")
                return UploadResult(
                    success=True,
                    message=result.get("message", "Archivo subido exitosamente"),
                    data=result.get("data", {}),
                    status_code=201
                )
            else:
                logger.error(f"Error en respuesta de upload: {result.get('message')}")
                return UploadResult(
                    success=False,
                    message=result.get("message", "Error desconocido"),
                    data=result.get("data", {}),
                    status_code=result.get("status_code", 400)
                )
                
        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            return UploadResult(
                success=False,
                message=str(e),
                status_code=0
            )
    
    async def report_error(
        self,
        solicitud_aseguradora_id: str,
        aseguradora: str,
        error_code: str,
        message: str,
        severity: str = "ERROR"
    ) -> bool:
        """
        Reportar error al endpoint de errores.
        
        Formato esperado por API:
        {
            "solicitudAseguradoraId": string,
            "aseguradora": string,
            "hasError": boolean,
            "errorCode": string,
            "severity": string,
            "message": string
        }

        Args:
            solicitud_aseguradora_id: ID de la solicitud (mismo que ingresa al bot)
            aseguradora: Nombre del bot en MAYÚSCULAS (ej: "HDI", "SBS", "RUNT")
            error_code: Código de error (ej: "LOGIN_FAILED", "TIMEOUT")
            message: Descripción del error
            severity: "ERROR" o "WARNING"
        
        Returns:
            True si se reportó exitosamente
        """
        url = f"{self.base_url}{self.ERRORS_ENDPOINT}"
        
        # Validar severity - API solo acepta ERROR o WARNING
        if severity not in ("ERROR", "WARNING"):
            logger.warning(f"Severity '{severity}' inválido, usando 'ERROR'")
            severity = "ERROR"
        
        payload = {
            "solicitudAseguradoraId": solicitud_aseguradora_id,
            "aseguradora": aseguradora.upper(),
            "hasError": True,
            "errorCode": error_code,
            "severity": severity,
            "message": message,
        }
        
        logger.info(f"Reportando error [{error_code}] para {aseguradora}: {message[:50]}...")
        
        try:
            result = await self._post_json_with_retry(url, payload)
            
            if result.get("success", True):  # Asumir éxito si no hay campo success
                logger.info(f"Error reportado exitosamente")
                return True
            else:
                logger.warning(f"Respuesta inesperada al reportar error: {result}")
                return False
                
        except Exception as e:
            logger.error(f"No se pudo reportar error: {e}")
            return False
    
    async def _post_json_with_retry(
        self,
        url: str,
        data: dict
    ) -> dict:
        """
        POST JSON con retry y backoff exponencial.
        
        Args:
            url: URL destino
            data: Datos JSON a enviar
        
        Returns:
            Respuesta como dict
        
        Raises:
            Exception si todos los intentos fallan
        """
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        url,
                        json=data,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    # Considerar 2xx como éxito
                    if 200 <= response.status_code < 300:
                        try:
                            return response.json()
                        except Exception:
                            return {"success": True, "status_code": response.status_code}
                    
                    # Error del servidor (5xx) - reintentar
                    if response.status_code >= 500:
                        raise httpx.HTTPStatusError(
                            f"Server error: {response.status_code}",
                            request=response.request,
                            response=response
                        )
                    
                    # Error del cliente (4xx) - no reintentar
                    try:
                        error_data = response.json()
                    except Exception:
                        error_data = {"message": response.text}
                    
                    error_data["status_code"] = response.status_code
                    error_data["success"] = False
                    return error_data
                    
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    wait_time = self.initial_wait * (self.backoff_factor ** attempt)
                    logger.warning(
                        f"Intento {attempt + 1}/{self.max_retries + 1} fallido: {e}. "
                        f"Reintentando en {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Todos los intentos fallidos para POST {url}")
        
        raise last_exception or Exception("Error desconocido en POST JSON")
    
    async def _post_multipart_with_retry(
        self,
        url: str,
        file_path: Path,
        file_field: str,
        content_type: str,
        data: dict
    ) -> dict:
        """
        POST multipart/form-data con retry y backoff exponencial.
        
        Args:
            url: URL destino
            file_path: Ruta al archivo
            file_field: Nombre del campo para el archivo
            content_type: Content-Type del archivo
            data: Campos adicionales del formulario
        
        Returns:
            Respuesta como dict
        
        Raises:
            Exception si todos los intentos fallan
        """
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    # Leer archivo
                    file_content = file_path.read_bytes()
                    
                    # Preparar multipart
                    files = {
                        file_field: (file_path.name, file_content, content_type)
                    }
                    
                    response = await client.post(url, files=files, data=data)
                    
                    # Considerar 2xx como éxito
                    if 200 <= response.status_code < 300:
                        try:
                            return response.json()
                        except Exception:
                            return {"success": True, "status_code": response.status_code}
                    
                    # Error del servidor (5xx) - reintentar
                    if response.status_code >= 500:
                        raise httpx.HTTPStatusError(
                            f"Server error: {response.status_code}",
                            request=response.request,
                            response=response
                        )
                    
                    # Error del cliente (4xx) - no reintentar
                    try:
                        error_data = response.json()
                    except Exception:
                        error_data = {"message": response.text}
                    
                    error_data["status_code"] = response.status_code
                    error_data["success"] = False
                    return error_data
                    
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    wait_time = self.initial_wait * (self.backoff_factor ** attempt)
                    logger.warning(
                        f"Intento {attempt + 1}/{self.max_retries + 1} fallido: {e}. "
                        f"Reintentando en {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Todos los intentos fallidos para upload a {url}")
        
        raise last_exception or Exception("Error desconocido en POST multipart")

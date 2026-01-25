"""
Subpaquete HTTP - Cliente para comunicación con API BrokerWiz.

Proporciona un cliente async para subir PDFs y reportar errores
a los endpoints de la aplicación web.

Uso:
    from workers.http import AppWebClient
    
    client = AppWebClient()
    await client.upload_pdf(pdf_path, solicitud_id)
    await client.report_error(solicitud_id, "HDI", "LOGIN_FAILED", "Credenciales inválidas")
"""

from workers.http.app_web_client import AppWebClient, UploadResult

__all__ = [
    "AppWebClient",
    "UploadResult",
]

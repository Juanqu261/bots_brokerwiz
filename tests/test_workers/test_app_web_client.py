"""
Tests unitarios para AppWebClient.

Valida:
- Inicialización y configuración
- Upload de PDFs
- Reporte de errores
- Manejo de reintentos
- Respuestas de éxito y error

python -m pytest tests/test_workers/test_app_web_client.py
"""

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from tempfile import TemporaryDirectory

import httpx

from workers.http.app_web_client import AppWebClient, UploadResult


class TestAppWebClientInit:
    """Tests de inicialización."""

    def test_init_loads_settings(self):
        """Debe cargar configuración de settings."""
        with patch("workers.http.app_web_client.settings") as mock_settings:
            mock_settings.app_web.APP_WEB_BASE_URL = "https://api.example.com"
            mock_settings.app_web.APP_WEB_UPLOAD_TIMEOUT = 60
            
            client = AppWebClient()
            
            assert client.base_url == "https://api.example.com"
            assert client.timeout == 60

    def test_init_sets_retry_config(self):
        """Debe establecer configuración de reintentos."""
        with patch("workers.http.app_web_client.settings") as mock_settings:
            mock_settings.app_web.APP_WEB_BASE_URL = "https://api.example.com"
            mock_settings.app_web.APP_WEB_UPLOAD_TIMEOUT = 30
            
            client = AppWebClient()
            
            assert client.max_retries >= 0
            assert client.initial_wait > 0
            assert client.backoff_factor > 1


class TestUploadResult:
    """Tests de la dataclass UploadResult."""

    def test_upload_result_success(self):
        """Debe crear resultado exitoso."""
        result = UploadResult(
            success=True,
            message="Archivo subido",
            data={"id": "123"},
            status_code=201
        )
        
        assert result.success is True
        assert result.message == "Archivo subido"
        assert result.data["id"] == "123"
        assert result.status_code == 201

    def test_upload_result_failure(self):
        """Debe crear resultado fallido."""
        result = UploadResult(
            success=False,
            message="Error de red",
            status_code=0
        )
        
        assert result.success is False
        assert result.data == {}


class TestUploadPdf:
    """Tests del método upload_pdf."""

    @pytest.mark.asyncio
    async def test_upload_pdf_file_not_found(self):
        """Debe retornar error si archivo no existe."""
        with patch("workers.http.app_web_client.settings") as mock_settings:
            mock_settings.app_web.APP_WEB_BASE_URL = "https://api.example.com"
            mock_settings.app_web.APP_WEB_UPLOAD_TIMEOUT = 30
            
            client = AppWebClient()
            
            result = await client.upload_pdf(
                pdf_path=Path("/nonexistent/file.pdf"),
                solicitud_aseguradora_id="123"
            )
            
            assert result.success is False
            assert "no encontrado" in result.message.lower()

    @pytest.mark.asyncio
    async def test_upload_pdf_success(self):
        """Debe subir archivo exitosamente."""
        with TemporaryDirectory() as tmpdir:
            # Crear archivo temporal
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"PDF content")
            
            with patch("workers.http.app_web_client.settings") as mock_settings:
                mock_settings.app_web.APP_WEB_BASE_URL = "https://api.example.com"
                mock_settings.app_web.APP_WEB_UPLOAD_TIMEOUT = 30
                
                client = AppWebClient()
                
                # Mock del método interno
                with patch.object(client, "_post_multipart_with_retry", new_callable=AsyncMock) as mock_post:
                    mock_post.return_value = {
                        "success": True,
                        "message": "OK",
                        "data": {"id": "abc123"}
                    }
                    
                    result = await client.upload_pdf(
                        pdf_path=pdf_path,
                        solicitud_aseguradora_id="sol-123",
                        tipo_subida="bot"
                    )
                    
                    assert result.success is True
                    assert result.data["id"] == "abc123"
                    mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_pdf_server_error(self):
        """Debe manejar errores del servidor."""
        with TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"PDF content")
            
            with patch("workers.http.app_web_client.settings") as mock_settings:
                mock_settings.app_web.APP_WEB_BASE_URL = "https://api.example.com"
                mock_settings.app_web.APP_WEB_UPLOAD_TIMEOUT = 30
                
                client = AppWebClient()
                
                with patch.object(client, "_post_multipart_with_retry", new_callable=AsyncMock) as mock_post:
                    mock_post.return_value = {
                        "success": False,
                        "message": "Internal Server Error",
                        "status_code": 500
                    }
                    
                    result = await client.upload_pdf(
                        pdf_path=pdf_path,
                        solicitud_aseguradora_id="sol-123"
                    )
                    
                    assert result.success is False


class TestReportError:
    """Tests del método report_error."""

    @pytest.mark.asyncio
    async def test_report_error_success(self):
        """Debe reportar error exitosamente."""
        with patch("workers.http.app_web_client.settings") as mock_settings:
            mock_settings.app_web.APP_WEB_BASE_URL = "https://api.example.com"
            mock_settings.app_web.APP_WEB_UPLOAD_TIMEOUT = 30
            
            client = AppWebClient()
            
            with patch.object(client, "_post_json_with_retry", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = {"success": True}
                
                result = await client.report_error(
                    solicitud_aseguradora_id="sol-123",
                    aseguradora="hdi",
                    error_code="LOGIN_FAILED",
                    message="Credenciales inválidas",
                    severity="ERROR"
                )
                
                assert result is True
                mock_post.assert_called_once()
                
                # Verificar payload enviado
                call_args = mock_post.call_args
                payload = call_args[0][1]  # Segundo argumento posicional
                assert payload["aseguradora"] == "HDI"
                assert payload["errorCode"] == "LOGIN_FAILED"
                assert payload["hasError"] is True

    @pytest.mark.asyncio
    async def test_report_error_network_failure(self):
        """Debe manejar fallas de red."""
        with patch("workers.http.app_web_client.settings") as mock_settings:
            mock_settings.app_web.APP_WEB_BASE_URL = "https://api.example.com"
            mock_settings.app_web.APP_WEB_UPLOAD_TIMEOUT = 30
            
            client = AppWebClient()
            
            with patch.object(client, "_post_json_with_retry", new_callable=AsyncMock) as mock_post:
                mock_post.side_effect = Exception("Connection refused")
                
                result = await client.report_error(
                    solicitud_aseguradora_id="sol-123",
                    aseguradora="hdi",
                    error_code="TIMEOUT",
                    message="Página no cargó"
                )
                
                assert result is False


class TestContentTypeDetection:
    """Tests de detección de content-type."""

    @pytest.mark.asyncio
    async def test_detects_pdf_content_type(self):
        """Debe detectar content-type para PDF."""
        with TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"PDF content")
            
            with patch("workers.http.app_web_client.settings") as mock_settings:
                mock_settings.app_web.APP_WEB_BASE_URL = "https://api.example.com"
                mock_settings.app_web.APP_WEB_UPLOAD_TIMEOUT = 30
                
                client = AppWebClient()
                
                with patch.object(client, "_post_multipart_with_retry", new_callable=AsyncMock) as mock_post:
                    mock_post.return_value = {"success": True}
                    
                    await client.upload_pdf(pdf_path, "sol-123")
                    
                    call_args = mock_post.call_args
                    # Verificar content_type pasado
                    assert call_args[1]["content_type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_detects_png_content_type(self):
        """Debe detectar content-type para PNG."""
        with TemporaryDirectory() as tmpdir:
            png_path = Path(tmpdir) / "screenshot.png"
            png_path.write_bytes(b"PNG content")
            
            with patch("workers.http.app_web_client.settings") as mock_settings:
                mock_settings.app_web.APP_WEB_BASE_URL = "https://api.example.com"
                mock_settings.app_web.APP_WEB_UPLOAD_TIMEOUT = 30
                
                client = AppWebClient()
                
                with patch.object(client, "_post_multipart_with_retry", new_callable=AsyncMock) as mock_post:
                    mock_post.return_value = {"success": True}
                    
                    await client.upload_pdf(png_path, "sol-123")
                    
                    call_args = mock_post.call_args
                    assert call_args[1]["content_type"] == "image/png"


class TestEndpoints:
    """Tests de endpoints."""

    def test_upload_endpoint_defined(self):
        """Debe tener endpoint de upload definido."""
        assert AppWebClient.UPLOAD_ENDPOINT == "/archivos-cotizacion"

    def test_errors_endpoint_defined(self):
        """Debe tener endpoint de errores definido."""
        assert AppWebClient.ERRORS_ENDPOINT == "/api/bot-errors"

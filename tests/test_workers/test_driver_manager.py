"""
Tests unitarios para SeleniumDriverManager.

Valida:
- Inicialización y configuración
- Creación y cierre del driver
- Context manager
- Métodos de navegación
- Screenshots
- Manejo de cookies

python -m pytest tests/test_workers/test_driver_manager.py
"""

import pytest
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from tempfile import TemporaryDirectory

from workers.selenium.driver_manager import SeleniumDriverManager


class TestDriverManagerInit:
    """Tests de inicialización."""

    def test_init_sets_ids(self):
        """Debe establecer bot_id y job_id."""
        dm = SeleniumDriverManager("hdi", "job-123")
        
        assert dm.bot_id == "hdi"
        assert dm.job_id == "job-123"
        assert dm.driver is None

    def test_init_creates_cookies_manager(self):
        """Debe crear CookiesManager con bot_id correcto."""
        dm = SeleniumDriverManager("sura", "job-456")
        
        assert dm._cookies_manager is not None
        assert dm._cookies_manager.bot_id == "sura"


class TestDriverManagerLifecycle:
    """Tests de ciclo de vida del driver."""

    @pytest.mark.asyncio
    async def test_create_driver_success(self):
        """create_driver debe crear instancia de Chrome."""
        dm = SeleniumDriverManager("hdi", "job-123")
        
        with patch.object(dm, "_create_driver_sync") as mock_create:
            mock_driver = MagicMock()
            mock_create.return_value = mock_driver
            
            result = await dm.create_driver()
            
            assert result == mock_driver
            assert dm.driver == mock_driver
            assert dm._created_at is not None

    @pytest.mark.asyncio
    async def test_quit_closes_driver(self):
        """quit debe cerrar el driver."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm.driver = MagicMock()
        dm._created_at = time.time()
        
        with patch.object(dm, "_cleanup_old_pdfs", new_callable=AsyncMock):
            await dm.quit()
        
        assert dm.driver is None
        assert dm._created_at is None

    @pytest.mark.asyncio
    async def test_quit_handles_exception(self):
        """quit no debe fallar si driver.quit() lanza excepción."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm.driver = MagicMock()
        dm.driver.quit.side_effect = Exception("Error cerrando")
        
        with patch.object(dm, "_cleanup_old_pdfs", new_callable=AsyncMock):
            # No debe lanzar excepción
            await dm.quit()
        
        assert dm.driver is None


class TestDriverManagerContextManager:
    """Tests del context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_and_quits(self):
        """Context manager debe crear driver al entrar y cerrarlo al salir."""
        dm = SeleniumDriverManager("hdi", "job-123")
        
        with patch.object(dm, "create_driver", new_callable=AsyncMock) as mock_create:
            with patch.object(dm, "quit", new_callable=AsyncMock) as mock_quit:
                mock_driver = MagicMock()
                mock_create.return_value = mock_driver
                
                async with dm as manager:
                    assert manager == dm
                    mock_create.assert_called_once()
                
                mock_quit.assert_called_once()


class TestDriverManagerNavigation:
    """Tests de métodos de navegación."""

    @pytest.mark.asyncio
    async def test_get_navigates_to_url(self):
        """get debe navegar a la URL."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm.driver = MagicMock()
        
        await dm.get("https://example.com")
        
        dm.driver.get.assert_called_with("https://example.com")

    @pytest.mark.asyncio
    async def test_refresh_reloads_page(self):
        """refresh debe recargar la página."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm.driver = MagicMock()
        
        await dm.refresh()
        
        dm.driver.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_back_navigates_back(self):
        """back debe navegar hacia atrás."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm.driver = MagicMock()
        
        await dm.back()
        
        dm.driver.back.assert_called_once()

    def test_current_url_property(self):
        """current_url debe retornar URL actual."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm.driver = MagicMock()
        dm.driver.current_url = "https://example.com/page"
        
        assert dm.current_url == "https://example.com/page"

    def test_current_url_empty_when_no_driver(self):
        """current_url debe retornar vacío si no hay driver."""
        dm = SeleniumDriverManager("hdi", "job-123")
        
        assert dm.current_url == ""


class TestDriverManagerScreenshots:
    """Tests de screenshots."""

    @pytest.mark.asyncio
    async def test_screenshot_creates_file(self):
        """screenshot debe guardar captura con nombre correcto."""
        with TemporaryDirectory() as tmpdir:
            dm = SeleniumDriverManager("hdi", "job-123", screenshots_dir=Path(tmpdir))
            dm.driver = MagicMock()
            
            result = await dm.screenshot("test_capture")
            
            assert result.parent == Path(tmpdir)
            assert "test_capture" in result.name
            assert result.suffix == ".png"
            dm.driver.save_screenshot.assert_called_once()


class TestDriverManagerCookies:
    """Tests de manejo de cookies."""

    @pytest.mark.asyncio
    async def test_save_cookies_delegates_to_manager(self):
        """save_cookies debe delegar a CookiesManager."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm.driver = MagicMock()
        dm._cookies_manager.save = AsyncMock()
        
        await dm.save_cookies()
        
        dm._cookies_manager.save.assert_called_once_with(dm.driver)

    @pytest.mark.asyncio
    async def test_load_cookies_delegates_to_manager(self):
        """load_cookies debe delegar a CookiesManager."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm.driver = MagicMock()
        dm._cookies_manager.load = AsyncMock(return_value=True)
        
        result = await dm.load_cookies("hdi.com.co")
        
        assert result is True
        dm._cookies_manager.load.assert_called_once_with(dm.driver, "hdi.com.co")

    def test_clear_cookies_delegates_to_manager(self):
        """clear_cookies debe delegar a CookiesManager."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm._cookies_manager.clear = MagicMock()
        
        dm.clear_cookies()
        
        dm._cookies_manager.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_all_cookies_clears_browser(self):
        """delete_all_cookies debe limpiar cookies del navegador."""
        dm = SeleniumDriverManager("hdi", "job-123")
        dm.driver = MagicMock()
        
        await dm.delete_all_cookies()
        
        dm.driver.delete_all_cookies.assert_called_once()


class TestDriverManagerConstants:
    """Tests de constantes y configuración."""

    def test_chrome_args_base_does_not_contain_headless(self):
        """CHROME_ARGS_BASE no debe incluir headless (se agrega dinámicamente)."""
        assert not any(
            "headless" in arg for arg in SeleniumDriverManager.CHROME_ARGS_BASE
        )

    def test_chrome_args_base_contains_no_sandbox(self):
        """CHROME_ARGS_BASE debe incluir --no-sandbox."""
        assert any(
            "no-sandbox" in arg for arg in SeleniumDriverManager.CHROME_ARGS_BASE
        )

    def test_has_timeout_constants(self):
        """Debe tener constantes de timeout definidas."""
        assert SeleniumDriverManager.IMPLICIT_TIMEOUT > 0
        assert SeleniumDriverManager.PAGE_LOAD_TIMEOUT > 0
        assert SeleniumDriverManager.SCRIPT_TIMEOUT > 0

    def test_has_directory_constants(self):
        """Debe tener directorios configurados."""
        assert SeleniumDriverManager.TEMP_PDF_DIR is not None
        assert SeleniumDriverManager.DEFAULT_SCREENSHOTS_DIR is not None

    def test_custom_screenshots_dir(self):
        """Debe aceptar directorio de screenshots personalizado."""
        custom_dir = Path("/custom/screenshots")
        dm = SeleniumDriverManager("hdi", "job-123", screenshots_dir=custom_dir)
        assert dm._screenshots_dir == custom_dir

    def test_default_screenshots_dir(self):
        """Debe usar directorio default si no se especifica."""
        dm = SeleniumDriverManager("hdi", "job-123")
        assert dm._screenshots_dir == SeleniumDriverManager.DEFAULT_SCREENSHOTS_DIR

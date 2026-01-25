"""
Tests unitarios para SeleniumHelpers.

Valida:
- Métodos de espera (wait_for, wait_for_all)
- Interacción con elementos (click, type_text, select)
- Getters de información (get_text, get_attribute)
- Esperas especiales (wait_for_download, wait_for_url)

python -m pytest tests/test_workers/test_selenium_helpers.py
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

from workers.selenium.helpers import SeleniumHelpers


class MockSeleniumHelpers(SeleniumHelpers):
    """Implementación concreta para testing."""
    
    def __init__(self):
        self.driver = MagicMock()
        self.TEMP_PDF_DIR = Path("temp/pdfs")


class TestWaitFor:
    """Tests de métodos wait_for."""

    @pytest.mark.asyncio
    async def test_wait_for_presence(self):
        """wait_for debe esperar elemento con condición presence."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        
        with patch("workers.selenium.helpers.WebDriverWait") as mock_wait_class:
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_element
            mock_wait_class.return_value = mock_wait
            
            result = await helpers.wait_for(By.ID, "test-id", condition="presence")
            
            assert result == mock_element
            mock_wait_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_clickable(self):
        """wait_for debe soportar condición clickable."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        
        with patch("workers.selenium.helpers.WebDriverWait") as mock_wait_class:
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_element
            mock_wait_class.return_value = mock_wait
            
            result = await helpers.wait_for(By.CSS_SELECTOR, ".btn", condition="clickable")
            
            assert result == mock_element

    @pytest.mark.asyncio
    async def test_wait_for_all_returns_list(self):
        """wait_for_all debe retornar lista de elementos."""
        helpers = MockSeleniumHelpers()
        mock_elements = [MagicMock(), MagicMock(), MagicMock()]
        
        with patch("workers.selenium.helpers.WebDriverWait") as mock_wait_class:
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_elements
            mock_wait_class.return_value = mock_wait
            
            result = await helpers.wait_for_all(By.CLASS_NAME, "item")
            
            assert len(result) == 3


class TestClick:
    """Tests del método click."""

    @pytest.mark.asyncio
    async def test_click_normal(self):
        """click debe hacer scroll y click normal."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        
        await helpers.click(mock_element, scroll=True, use_js=False)
        
        # Verificar scroll
        helpers.driver.execute_script.assert_called()
        # Verificar click
        mock_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_js_fallback(self):
        """click debe usar JS si click normal falla."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        mock_element.click.side_effect = ElementClickInterceptedException("intercepted")
        
        await helpers.click(mock_element, scroll=False, use_js=False)
        
        # Debe haber usado JS click como fallback
        assert helpers.driver.execute_script.call_count >= 1

    @pytest.mark.asyncio
    async def test_click_use_js_directly(self):
        """click con use_js=True debe usar JS directamente."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        
        await helpers.click(mock_element, scroll=False, use_js=True)
        
        # No debe haberse llamado click() del elemento
        mock_element.click.assert_not_called()
        # Debe haber usado execute_script
        helpers.driver.execute_script.assert_called()


class TestTypeText:
    """Tests del método type_text."""

    @pytest.mark.asyncio
    async def test_type_text_clears_field(self):
        """type_text debe limpiar campo por defecto."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        
        await helpers.type_text(mock_element, "test text", clear=True)
        
        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_with("test text")

    @pytest.mark.asyncio
    async def test_type_text_no_clear(self):
        """type_text con clear=False no debe limpiar."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        
        await helpers.type_text(mock_element, "append text", clear=False)
        
        mock_element.clear.assert_not_called()
        mock_element.send_keys.assert_called_with("append text")


class TestSelectMethods:
    """Tests de métodos select."""

    @pytest.mark.asyncio
    async def test_select_by_text(self):
        """select_by_text debe seleccionar por texto visible."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        
        with patch("workers.selenium.helpers.Select") as mock_select_class:
            mock_select = MagicMock()
            mock_select_class.return_value = mock_select
            
            await helpers.select_by_text(mock_element, "Option 1")
            
            mock_select.select_by_visible_text.assert_called_with("Option 1")

    @pytest.mark.asyncio
    async def test_select_by_value(self):
        """select_by_value debe seleccionar por valor."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        
        with patch("workers.selenium.helpers.Select") as mock_select_class:
            mock_select = MagicMock()
            mock_select_class.return_value = mock_select
            
            await helpers.select_by_value(mock_element, "opt1")
            
            mock_select.select_by_value.assert_called_with("opt1")


class TestGetters:
    """Tests de getters de información."""

    @pytest.mark.asyncio
    async def test_get_text(self):
        """get_text debe retornar texto del elemento."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        mock_element.text = "Hello World"
        
        result = await helpers.get_text(mock_element)
        
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_get_attribute(self):
        """get_attribute debe retornar atributo del elemento."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "https://example.com"
        
        result = await helpers.get_attribute(mock_element, "href")
        
        assert result == "https://example.com"
        mock_element.get_attribute.assert_called_with("href")

    @pytest.mark.asyncio
    async def test_is_displayed(self):
        """is_displayed debe retornar visibilidad del elemento."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        mock_element.is_displayed.return_value = True
        
        result = await helpers.is_displayed(mock_element)
        
        assert result is True


class TestWaitForUrl:
    """Tests de wait_for_url."""

    @pytest.mark.asyncio
    async def test_wait_for_url_success(self):
        """wait_for_url debe retornar True si URL contiene texto."""
        helpers = MockSeleniumHelpers()
        
        with patch("workers.selenium.helpers.WebDriverWait") as mock_wait_class:
            mock_wait = MagicMock()
            mock_wait.until.return_value = True
            mock_wait_class.return_value = mock_wait
            
            result = await helpers.wait_for_url("dashboard")
            
            assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_url_timeout(self):
        """wait_for_url debe retornar False en timeout."""
        helpers = MockSeleniumHelpers()
        
        with patch("workers.selenium.helpers.WebDriverWait") as mock_wait_class:
            mock_wait = MagicMock()
            mock_wait.until.side_effect = TimeoutException()
            mock_wait_class.return_value = mock_wait
            
            result = await helpers.wait_for_url("nonexistent")
            
            assert result is False


class TestExecuteJs:
    """Tests de execute_js."""

    @pytest.mark.asyncio
    async def test_execute_js(self):
        """execute_js debe ejecutar script y retornar resultado."""
        helpers = MockSeleniumHelpers()
        helpers.driver.execute_script.return_value = "result"
        
        result = await helpers.execute_js("return document.title")
        
        assert result == "result"
        helpers.driver.execute_script.assert_called_with("return document.title")

    @pytest.mark.asyncio
    async def test_execute_js_with_args(self):
        """execute_js debe pasar argumentos al script."""
        helpers = MockSeleniumHelpers()
        mock_element = MagicMock()
        
        await helpers.execute_js("arguments[0].click()", mock_element)
        
        helpers.driver.execute_script.assert_called_with("arguments[0].click()", mock_element)

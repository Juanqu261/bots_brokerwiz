"""
Tests unitarios para CookiesManager.

Valida:
- Inicialización y paths
- Guardar cookies
- Cargar cookies con filtro de dominio
- Operaciones de limpieza

python -m pytest tests/test_workers/test_cookies_manager.py
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory

from workers.selenium.cookies_manager import CookiesManager


class TestCookiesManagerInit:
    """Tests de inicialización."""

    def test_init_sets_bot_id(self):
        """Debe establecer bot_id correctamente."""
        cm = CookiesManager("hdi")
        assert cm.bot_id == "hdi"

    def test_init_creates_correct_path(self):
        """Debe crear path correcto para cookies."""
        cm = CookiesManager("sura")
        expected_path = CookiesManager.PROFILES_DIR / "sura" / "cookies.json"
        assert cm.cookies_file == expected_path


class TestCookiesManagerExists:
    """Tests del método exists."""

    def test_exists_returns_false_when_no_file(self):
        """exists() debe retornar False si no hay archivo."""
        cm = CookiesManager("nonexistent_bot_xyz")
        assert cm.exists() is False

    def test_exists_returns_true_when_file_exists(self):
        """exists() debe retornar True si existe el archivo."""
        with TemporaryDirectory() as tmpdir:
            with patch.object(CookiesManager, "PROFILES_DIR", Path(tmpdir)):
                cm = CookiesManager("test_bot")
                
                # Crear archivo manualmente
                cm.cookies_file.parent.mkdir(parents=True, exist_ok=True)
                cm.cookies_file.write_text("[]")
                
                assert cm.exists() is True


class TestCookiesManagerSave:
    """Tests del método save."""

    @pytest.mark.asyncio
    async def test_save_creates_file(self):
        """save() debe crear archivo JSON con cookies."""
        with TemporaryDirectory() as tmpdir:
            with patch.object(CookiesManager, "PROFILES_DIR", Path(tmpdir)):
                cm = CookiesManager("test_bot")
                
                # Mock del driver
                mock_driver = MagicMock()
                mock_driver.get_cookies.return_value = [
                    {"name": "session", "value": "abc123", "domain": ".example.com"},
                    {"name": "token", "value": "xyz789", "domain": ".example.com"},
                ]
                
                await cm.save(mock_driver)
                
                assert cm.cookies_file.exists()
                saved_data = json.loads(cm.cookies_file.read_text())
                assert len(saved_data) == 2
                assert saved_data[0]["name"] == "session"


class TestCookiesManagerLoad:
    """Tests del método load."""

    @pytest.mark.asyncio
    async def test_load_returns_false_when_no_file(self):
        """load() debe retornar False si no hay archivo."""
        cm = CookiesManager("nonexistent_bot_xyz")
        mock_driver = MagicMock()
        
        result = await cm.load(mock_driver, "example.com")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_load_filters_by_domain(self):
        """load() debe filtrar cookies por dominio."""
        with TemporaryDirectory() as tmpdir:
            with patch.object(CookiesManager, "PROFILES_DIR", Path(tmpdir)):
                cm = CookiesManager("test_bot")
                
                # Crear archivo con cookies de diferentes dominios
                cm.cookies_file.parent.mkdir(parents=True, exist_ok=True)
                cookies = [
                    {"name": "session", "value": "abc", "domain": ".hdi.com.co"},
                    {"name": "other", "value": "xyz", "domain": ".google.com"},
                ]
                cm.cookies_file.write_text(json.dumps(cookies))
                
                # Mock del driver
                mock_driver = MagicMock()
                
                result = await cm.load(mock_driver, "hdi.com.co")
                
                assert result is True
                # Solo debe haberse añadido 1 cookie (la de hdi.com.co)
                assert mock_driver.add_cookie.call_count == 1

    @pytest.mark.asyncio
    async def test_load_handles_invalid_json(self):
        """load() debe manejar JSON inválido."""
        with TemporaryDirectory() as tmpdir:
            with patch.object(CookiesManager, "PROFILES_DIR", Path(tmpdir)):
                cm = CookiesManager("test_bot")
                
                cm.cookies_file.parent.mkdir(parents=True, exist_ok=True)
                cm.cookies_file.write_text("invalid json {")
                
                mock_driver = MagicMock()
                result = await cm.load(mock_driver, "example.com")
                
                assert result is False


class TestCookiesManagerClear:
    """Tests del método clear."""

    def test_clear_removes_file(self):
        """clear() debe eliminar archivo de cookies."""
        with TemporaryDirectory() as tmpdir:
            with patch.object(CookiesManager, "PROFILES_DIR", Path(tmpdir)):
                cm = CookiesManager("test_bot")
                
                # Crear archivo
                cm.cookies_file.parent.mkdir(parents=True, exist_ok=True)
                cm.cookies_file.write_text("[]")
                assert cm.exists() is True
                
                # Limpiar
                cm.clear()
                assert cm.exists() is False

    def test_clear_does_nothing_if_no_file(self):
        """clear() no debe fallar si no hay archivo."""
        cm = CookiesManager("nonexistent_bot_xyz")
        # No debe lanzar excepción
        cm.clear()


class TestCookiesManagerClearAll:
    """Tests del método clear_all."""

    def test_clear_all_removes_all_cookies(self):
        """clear_all() debe eliminar cookies de todos los bots."""
        with TemporaryDirectory() as tmpdir:
            with patch.object(CookiesManager, "PROFILES_DIR", Path(tmpdir)):
                # Crear cookies para varios bots
                for bot_id in ["hdi", "sura", "axa"]:
                    cm = CookiesManager(bot_id)
                    cm.cookies_file.parent.mkdir(parents=True, exist_ok=True)
                    cm.cookies_file.write_text("[]")
                
                count = CookiesManager.clear_all()
                
                assert count == 3
                # Verificar que ya no existen
                for bot_id in ["hdi", "sura", "axa"]:
                    cm = CookiesManager(bot_id)
                    assert cm.exists() is False

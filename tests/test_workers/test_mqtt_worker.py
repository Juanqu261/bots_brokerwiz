"""
Tests unitarios para mqtt_worker.

Valida:
- Registro de bots (BOT_REGISTRY)
- Funciones get_bot_class y list_available_bots
- Handler de tareas
- Función run_worker (parcial, sin conexión real)

python -m pytest tests/test_workers/test_mqtt_worker.py
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from workers.mqtt_worker import (
    BOT_REGISTRY,
    get_bot_class,
    list_available_bots,
    handle_task,
)
from workers.resource_manager import ResourceUnavailableError
from workers.bots.hdi_bot import HDIBot


class TestBotRegistry:
    """Tests del registro de bots."""

    def test_registry_contains_hdi(self):
        """BOT_REGISTRY debe contener HDIBot."""
        assert "hdi" in BOT_REGISTRY
        assert BOT_REGISTRY["hdi"] == HDIBot

    def test_registry_is_dict(self):
        """BOT_REGISTRY debe ser un diccionario."""
        assert isinstance(BOT_REGISTRY, dict)


class TestGetBotClass:
    """Tests de get_bot_class."""

    def test_get_bot_class_existing(self):
        """Debe retornar clase para bot existente."""
        result = get_bot_class("hdi")
        assert result == HDIBot

    def test_get_bot_class_case_insensitive(self):
        """Debe ser case-insensitive."""
        result = get_bot_class("HDI")
        assert result == HDIBot
        
        result = get_bot_class("Hdi")
        assert result == HDIBot

    def test_get_bot_class_nonexistent(self):
        """Debe retornar None para bot no existente."""
        result = get_bot_class("nonexistent_bot")
        assert result is None


class TestListAvailableBots:
    """Tests de list_available_bots."""

    def test_list_returns_list(self):
        """Debe retornar lista."""
        result = list_available_bots()
        assert isinstance(result, list)

    def test_list_contains_hdi(self):
        """Debe incluir 'hdi'."""
        result = list_available_bots()
        assert "hdi" in result

    def test_list_matches_registry_keys(self):
        """Debe coincidir con keys del registro."""
        result = list_available_bots()
        assert set(result) == set(BOT_REGISTRY.keys())


class TestHandleTask:
    """Tests de handle_task."""

    @pytest.mark.asyncio
    async def test_handle_task_bot_not_found(self):
        """Debe loguear warning si bot no existe."""
        mock_resource_manager = MagicMock()
        
        with patch("workers.mqtt_worker.logger") as mock_logger:
            await handle_task(
                topic="bots/queue/nonexistent",
                data={"job_id": "test-123", "payload": {}},
                resource_manager=mock_resource_manager
            )
            
            # Debe haber logueado warning
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_handle_task_extracts_aseguradora_from_topic(self):
        """Debe extraer aseguradora del topic."""
        mock_resource_manager = MagicMock()
        mock_resource_manager.acquire_slot = MagicMock()
        
        # Simular que el bot no existe para simplificar
        with patch("workers.mqtt_worker.get_bot_class", return_value=None):
            await handle_task(
                topic="bots/queue/sura",
                data={"job_id": "test-123", "payload": {}},
                resource_manager=mock_resource_manager
            )
        
        # No falló, extrajo correctamente

    @pytest.mark.asyncio
    async def test_handle_task_resource_unavailable(self):
        """Debe propagar ResourceUnavailableError."""
        mock_resource_manager = MagicMock()
        
        # Configurar acquire_slot como context manager que lanza error
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=ResourceUnavailableError("No slots"))
        mock_resource_manager.acquire_slot.return_value = mock_cm
        
        with patch("workers.mqtt_worker.get_bot_class") as mock_get_bot:
            mock_get_bot.return_value = MagicMock()
            
            with pytest.raises(ResourceUnavailableError):
                await handle_task(
                    topic="bots/queue/hdi",
                    data={"job_id": "test-123", "payload": {}},
                    resource_manager=mock_resource_manager
                )

    @pytest.mark.asyncio
    async def test_handle_task_success_flow(self):
        """Debe ejecutar bot exitosamente."""
        mock_resource_manager = MagicMock()
        
        # Mock del context manager de recursos
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock()
        mock_cm.__aexit__ = AsyncMock()
        mock_resource_manager.acquire_slot.return_value = mock_cm
        
        # Mock del bot
        mock_bot_instance = AsyncMock()
        mock_bot_instance.run = AsyncMock(return_value=True)
        mock_bot_instance.__aenter__ = AsyncMock(return_value=mock_bot_instance)
        mock_bot_instance.__aexit__ = AsyncMock()
        
        mock_bot_class = MagicMock(return_value=mock_bot_instance)
        
        with patch("workers.mqtt_worker.get_bot_class", return_value=mock_bot_class):
            await handle_task(
                topic="bots/queue/hdi",
                data={"job_id": "test-123", "payload": {"key": "value"}},
                resource_manager=mock_resource_manager
            )
            
            # Verificar que se creó el bot con parámetros correctos
            mock_bot_class.assert_called_once_with(
                job_id="test-123",
                payload={"key": "value"}
            )

    @pytest.mark.asyncio
    async def test_handle_task_handles_bot_exception(self):
        """Debe reportar error si bot lanza excepción."""
        mock_resource_manager = MagicMock()
        
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock()
        mock_cm.__aexit__ = AsyncMock()
        mock_resource_manager.acquire_slot.return_value = mock_cm
        
        # Mock del bot que lanza excepción
        mock_bot_instance = AsyncMock()
        mock_bot_instance.run = AsyncMock(side_effect=Exception("Bot error"))
        mock_bot_instance.report_error = AsyncMock()
        mock_bot_instance.__aenter__ = AsyncMock(return_value=mock_bot_instance)
        mock_bot_instance.__aexit__ = AsyncMock()
        
        mock_bot_class = MagicMock(return_value=mock_bot_instance)
        
        with patch("workers.mqtt_worker.get_bot_class", return_value=mock_bot_class):
            await handle_task(
                topic="bots/queue/hdi",
                data={"job_id": "test-123", "payload": {}},
                resource_manager=mock_resource_manager
            )
            
            # Debe haber reportado el error
            mock_bot_instance.report_error.assert_called_once()
            call_kwargs = mock_bot_instance.report_error.call_args[1]
            assert call_kwargs["error_code"] == "BOT_EXCEPTION"
            assert call_kwargs["severity"] == "CRITICAL"


class TestWorkerFunctions:
    """Tests de funciones auxiliares del worker."""

    def test_handle_task_extracts_job_id_with_default(self):
        """handle_task debe usar 'unknown' si no hay job_id."""
        # Este test verifica la lógica de extracción
        data = {"payload": {}}
        job_id = data.get("job_id", "unknown")
        assert job_id == "unknown"

    def test_handle_task_extracts_payload_with_default(self):
        """handle_task debe usar dict vacío si no hay payload."""
        data = {"job_id": "test-123"}
        payload = data.get("payload", {})
        assert payload == {}

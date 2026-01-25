"""
Tests unitarios para ResourceManager.

Valida:
- Inicialización y configuración
- Verificación de recursos (mocking psutil)
- Adquisición y liberación de slots
- Propiedades y estadísticas

python -m pytest tests/test_workers/test_resource_manager.py
"""
import pytest
from unittest.mock import patch, MagicMock

from workers.resource_manager import ResourceManager, ResourceUnavailableError


class TestResourceManagerInit:
    """Tests de inicialización."""

    def test_init_default_values(self):
        """Debe inicializar con valores por defecto de settings."""
        with patch("workers.resource_manager.settings") as mock_settings:
            mock_settings.workers.MAX_CONCURRENT_BOTS = 3
            
            rm = ResourceManager()
            
            assert rm.max_concurrent == 3
            assert rm._max_cpu == ResourceManager.DEFAULT_MAX_CPU
            assert rm._max_memory == ResourceManager.DEFAULT_MAX_MEMORY
            assert rm.active_bots == 0
    
    def test_init_custom_values(self):
        """Debe aceptar valores personalizados."""
        rm = ResourceManager(
            max_concurrent=5,
            max_cpu_percent=70.0,
            max_memory_percent=75.0
        )
        
        assert rm.max_concurrent == 5
        assert rm._max_cpu == 70.0
        assert rm._max_memory == 75.0


class TestResourceManagerProperties:
    """Tests de propiedades."""

    def test_active_bots_starts_at_zero(self):
        """active_bots debe iniciar en 0."""
        rm = ResourceManager(max_concurrent=2)
        assert rm.active_bots == 0
    
    def test_available_slots(self):
        """available_slots debe calcular correctamente."""
        rm = ResourceManager(max_concurrent=3)
        assert rm.available_slots == 3
    
    def test_get_active_jobs_empty(self):
        """get_active_jobs debe retornar dict vacío inicialmente."""
        rm = ResourceManager(max_concurrent=2)
        assert rm.get_active_jobs() == {}


class TestCheckResources:
    """Tests de verificación de recursos."""

    @pytest.mark.asyncio
    async def test_check_resources_available(self):
        """Debe retornar True cuando hay recursos."""
        rm = ResourceManager(max_concurrent=2, max_cpu_percent=90, max_memory_percent=90)
        
        with patch("workers.resource_manager.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 50.0
            mock_psutil.virtual_memory.return_value = MagicMock(percent=60.0)
            
            ok, reason = await rm.check_resources()
            
            assert ok is True
            assert reason == ""

    @pytest.mark.asyncio
    async def test_check_resources_cpu_high(self):
        """Debe retornar False si CPU muy alta."""
        rm = ResourceManager(max_concurrent=2, max_cpu_percent=70)
        
        with patch("workers.resource_manager.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 85.0
            mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0)
            
            ok, reason = await rm.check_resources()
            
            assert ok is False
            assert "CPU" in reason

    @pytest.mark.asyncio
    async def test_check_resources_memory_high(self):
        """Debe retornar False si RAM muy alta."""
        rm = ResourceManager(max_concurrent=2, max_cpu_percent=90, max_memory_percent=70)
        
        with patch("workers.resource_manager.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 50.0
            mock_psutil.virtual_memory.return_value = MagicMock(percent=85.0)
            
            ok, reason = await rm.check_resources()
            
            assert ok is False
            assert "RAM" in reason


class TestAcquireSlot:
    """Tests del context manager acquire_slot."""

    @pytest.mark.asyncio
    async def test_acquire_slot_success(self):
        """Debe incrementar y decrementar contador correctamente."""
        rm = ResourceManager(max_concurrent=2, max_cpu_percent=90, max_memory_percent=90)
        
        with patch("workers.resource_manager.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 30.0
            mock_psutil.virtual_memory.return_value = MagicMock(percent=40.0)
            
            assert rm.active_bots == 0
            
            async with rm.acquire_slot("hdi", "job-123"):
                assert rm.active_bots == 1
                assert "job-123" in rm.get_active_jobs()
            
            # Después del context manager
            assert rm.active_bots == 0
            assert "job-123" not in rm.get_active_jobs()

    @pytest.mark.asyncio
    async def test_acquire_slot_no_resources(self):
        """Debe lanzar ResourceUnavailableError si no hay recursos."""
        rm = ResourceManager(max_concurrent=2, max_cpu_percent=50)
        
        with patch("workers.resource_manager.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 80.0  # CPU muy alta
            mock_psutil.virtual_memory.return_value = MagicMock(percent=40.0)
            
            with pytest.raises(ResourceUnavailableError):
                async with rm.acquire_slot("hdi", "job-123"):
                    pass

    @pytest.mark.asyncio
    async def test_acquire_slot_releases_on_exception(self):
        """Debe liberar slot incluso si hay excepción dentro."""
        rm = ResourceManager(max_concurrent=2, max_cpu_percent=90, max_memory_percent=90)
        
        with patch("workers.resource_manager.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 30.0
            mock_psutil.virtual_memory.return_value = MagicMock(percent=40.0)
            
            with pytest.raises(ValueError):
                async with rm.acquire_slot("hdi", "job-123"):
                    assert rm.active_bots == 1
                    raise ValueError("Error simulado")
            
            # El slot debe haberse liberado
            assert rm.active_bots == 0


class TestGetSystemStats:
    """Tests de estadísticas del sistema."""

    def test_get_system_stats_structure(self):
        """Debe retornar dict con campos esperados."""
        rm = ResourceManager(max_concurrent=3)
        
        with patch("workers.resource_manager.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 45.0
            mock_memory = MagicMock()
            mock_memory.percent = 60.0
            mock_memory.available = 8 * 1024 * 1024 * 1024  # 8GB
            mock_psutil.virtual_memory.return_value = mock_memory
            
            stats = rm.get_system_stats()
            
            assert "cpu_percent" in stats
            assert "memory_percent" in stats
            assert "memory_available_mb" in stats
            assert "active_bots" in stats
            assert "available_slots" in stats
            assert "max_concurrent" in stats
            assert stats["max_concurrent"] == 3

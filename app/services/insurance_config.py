"""
Administracion de aseguradoras activas.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field
from app.models.job import Aseguradora


logger = logging.getLogger(__name__)


class InsuranceConfig(BaseModel):
    """Configuracion general de una aseguradora."""
    enabled: bool = Field(
        default=True,
        description="Definir si la aseguradora esta activa o no."
    )
    description: Optional[str] = Field(
        default=None,
        description="Descripcion o nombre mas detallado."
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "enabled": True,
                "description": "HDI Seguros"
            }
        }
    }


class InsuranceConfigManager:
    """
    Carga las configuraciones desde el json y ofrece metodos para su
    lectura.
    """
    
    def __init__(self, config_path: str = "config/insurance_config.json"):
        """
        Args:
            config_path: Ruta al archivo de configuraciones.
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, InsuranceConfig] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """
        Cargar las configuracione
        
        Si el archivo no existe, todas las aseguradoras se marcan activas.
        """
        if not self.config_path.exists():
            logger.warning(
                f"Archivo de configuracion no encontrado {self.config_path}. "
                "Marcando todas las aseguradoras como activas."
            )
            self._load_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self._config = {}
            for key, value in config_data.items():
                self._config[key.lower()] = InsuranceConfig(**value)
            
            logger.info(f"Configuracion cargas para {len(self._config)} aseguradoras.")
        
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear archivo de configuracion: {e}")
            self._load_default_config()
        
        except Exception as e:
            logger.error(f"Error cargando configuraciones: {e}")
            self._load_default_config()
    
    def _load_default_config(self) -> None:
        """Cargar configuracion por defecto, con todas las aseguradoras activadas."""
        self._config = {
            aseg.value: InsuranceConfig(enabled=True, description=aseg.value.upper())
            for aseg in Aseguradora
        }
        logger.info("Cargada configuracion por defecto (todas las aseguradoras activas).")
    
    def is_enabled(self, aseguradora: Aseguradora) -> bool:
        """
        Chequea si una aseguradora esta activa.
        
        Args:
            aseguradora: Aseguradora enum
            
        Returns:
            True si esta activa, False de otra manera
        """
        config = self._config.get(aseguradora.value)
        if config is None:
            # If not in config, default to enabled
            logger.warning(
                f"Configuracion no encontrada {aseguradora.value}, activa por defecto."
            )
            return True
        return config.enabled
    
    def get_config(self, aseguradora: Aseguradora) -> InsuranceConfig:
        """
        Extraer toda la configuracion de una aseguradora.
        
        Args:
            aseguradora: Aseguradora enum
            
        Returns:
            Insurance configuration
        """
        config = self._config.get(aseguradora.value)
        if config is None:
            # Return default config if not found
            return InsuranceConfig(enabled=True, description=aseguradora.value.upper())
        return config
    
    def reload(self) -> None:
        """
        Recarga archivo de configuracion
        """
        logger.info("Recargando configuraciones de aseguradoras.")
        self.load_config()


# Singleton instance for dependency injection
_config_manager: Optional[InsuranceConfigManager] = None


def get_insurance_config() -> InsuranceConfigManager:
    """
    Devuelve instancia singleton.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = InsuranceConfigManager()
    return _config_manager

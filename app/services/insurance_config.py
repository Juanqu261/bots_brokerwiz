"""
Insurance configuration management.

This module provides centralized configuration for insurance companies,
allowing administrators to enable/disable specific insurances without code changes.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field
from app.models.job import Aseguradora


logger = logging.getLogger(__name__)


class InsuranceConfig(BaseModel):
    """Configuration for a single insurance company."""
    enabled: bool = Field(
        default=True,
        description="Whether this insurance company is currently enabled"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the insurance company"
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
    Manages insurance company configurations.
    
    Loads configuration from a JSON file and provides methods to check
    insurance status and retrieve configuration details.
    """
    
    def __init__(self, config_path: str = "config/insurance_config.json"):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration JSON file
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, InsuranceConfig] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """
        Load configuration from JSON file.
        
        If the file doesn't exist, all insurances default to enabled.
        """
        if not self.config_path.exists():
            logger.warning(
                f"Configuration file not found at {self.config_path}. "
                "Defaulting to all insurances enabled."
            )
            self._load_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self._config = {}
            for key, value in config_data.items():
                self._config[key.lower()] = InsuranceConfig(**value)
            
            logger.info(f"Loaded configuration for {len(self._config)} insurances")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse configuration file: {e}")
            self._load_default_config()
        
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._load_default_config()
    
    def _load_default_config(self) -> None:
        """Load default configuration with all insurances enabled."""
        self._config = {
            aseg.value: InsuranceConfig(enabled=True, description=aseg.value.upper())
            for aseg in Aseguradora
        }
        logger.info("Loaded default configuration (all insurances enabled)")
    
    def is_enabled(self, aseguradora: Aseguradora) -> bool:
        """
        Check if an insurance company is enabled.
        
        Args:
            aseguradora: Insurance company enum
            
        Returns:
            True if enabled, False otherwise
        """
        config = self._config.get(aseguradora.value)
        if config is None:
            # If not in config, default to enabled
            logger.warning(
                f"No configuration found for {aseguradora.value}, defaulting to enabled"
            )
            return True
        return config.enabled
    
    def get_config(self, aseguradora: Aseguradora) -> InsuranceConfig:
        """
        Get configuration for an insurance company.
        
        Args:
            aseguradora: Insurance company enum
            
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
        Reload configuration from file.
        
        This allows updating configuration without restarting the application.
        """
        logger.info("Reloading insurance configuration")
        self.load_config()


# Singleton instance for dependency injection
_config_manager: Optional[InsuranceConfigManager] = None


def get_insurance_config() -> InsuranceConfigManager:
    """
    Dependency injection function for FastAPI.
    
    Returns a singleton instance of InsuranceConfigManager.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = InsuranceConfigManager()
    return _config_manager

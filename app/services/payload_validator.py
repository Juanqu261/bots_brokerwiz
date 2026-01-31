"""
Validar payloads de aseguradoras.
"""

from typing import Any, Dict, Optional, Type
from app.models.job import Aseguradora
from app.models.insurance_schemas import INSURANCE_SCHEMAS, InsurancePayloadBase


class PayloadValidator:
    """
    Validar payloads de aseguradoras usando Pydantic.
    
    Example:
        validator = PayloadValidator()
        validated_payload = validator.validate(
            Aseguradora.HDI,
            {"in_strTipoDoc": "CC", "in_strNumDoc": "123456"}
        )
    """
    
    def __init__(self):
        """
        The schema registry maps Aseguradora enum values to their
        corresponding Pydantic schema classes.
        """
        self.schemas = INSURANCE_SCHEMAS
    
    def get_schema(self, aseguradora: Aseguradora) -> Type[InsurancePayloadBase]:
        """
        Args:
            aseguradora: Aseguradora enum

        Returns:
            Schema de payload correspondiente a la aseguradora
        """
        return self.schemas[aseguradora]
    
    def validate(
        self, 
        aseguradora: Aseguradora, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Args:
            aseguradora: Aseguradora enum
            payload: Diccionario raw de payload a validar
            
        Returns:
            Diccionario validado con todos los campos (incluyendo campos extra)
        """
        schema = self.get_schema(aseguradora)
        validated_model = schema(**payload)
        
        # Convertir modelo validado de vuelta a diccionario
        return validated_model.model_dump()


# Singleton
_payload_validator: Optional[PayloadValidator] = None


def get_payload_validator() -> PayloadValidator:
    global _payload_validator
    if _payload_validator is None:
        _payload_validator = PayloadValidator()
    return _payload_validator

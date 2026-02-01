"""
Modelos Pydantic para Jobs/Tareas de cotización.

Estos modelos representan las tareas que se encolan en MQTT
para ser procesadas por los workers (bots de Selenium).
"""

from enum import Enum
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel, Field, RootModel
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    """Estados posibles de un job."""
    PENDING = "pending"       # Encolado, esperando worker
    PROCESSING = "processing" # Worker lo está procesando
    COMPLETED = "completed"   # Completado exitosamente
    FAILED = "failed"         # Falló después de reintentos
    CANCELLED = "cancelled"   # Cancelado manualmente


class Aseguradora(str, Enum):
    """Aseguradoras soportadas."""
    HDI = "hdi"
    SURA = "sura"
    AXA = "axa"
    ALLIANZ = "allianz"
    BOLIVAR = "bolivar"
    EQUIDAD = "equidad"
    MUNDIAL = "mundial"
    SBS = "sbs"
    SOLIDARIA = "solidaria"
    RUNT = "runt"


class JobCreate(BaseModel):
    """
    Payload para crear un nuevo job de cotización.
    
    Acepta dos formatos:
    1. Plano (recomendado): todos los campos al mismo nivel
       {"in_strIDSolicitudAseguradora": "abc123", "in_strNumDoc": "123", ...}
    
    2. Anidado: con payload separado
       {"in_strIDSolicitudAseguradora": "abc123", "payload": {...}}
    """
    in_strIDSolicitudAseguradora: str = Field(
        ...,
        description="ID único de la solicitud (viene del sistema externo)",
        examples=["abc123xyz"]
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Datos específicos para el bot de la aseguradora"
    )
    
    model_config = {
        "extra": "allow",  # Permite campos adicionales
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "in_strIDSolicitudAseguradora": "abc123xyz",
                "in_strTipoDoc": "CC",
                "in_strNumDoc": "1234567890",
                "in_strPlaca": "ABC123",
                "in_strNombre": "Juan",
                "in_strApellido": "Pérez"
            }
        }
    }
    
    def __init__(self, **data):
        """
        Extrae in_strIDSolicitudAseguradora y agrupa el resto en payload.
        
        Permite enviar JSON plano o anidado:
        - Plano: {"in_strIDSolicitudAseguradora": "id", "in_strNumDoc": "123", ...}
        - Anidado: {"in_strIDSolicitudAseguradora": "id", "payload": {...}}
        """
        # Extraer ID de solicitud
        solicitud_id = data.pop("in_strIDSolicitudAseguradora", None)
        
        # Si ya hay payload, usarlo; si no, crear uno con los campos restantes
        if "payload" in data:
            payload = data.pop("payload", {})
        else:
            # Todos los campos restantes van al payload
            payload = data.copy()
            data.clear()
        
        super().__init__(
            in_strIDSolicitudAseguradora=solicitud_id,
            payload=payload
        )


class Job(BaseModel):
    """Representación completa de un job."""
    job_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="ID único del job generado por el sistema"
    )
    aseguradora: Aseguradora
    in_strIDSolicitudAseguradora: str = Field(
        ...,
        description="ID de la solicitud de aseguradora"
    )
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def to_mqtt_message(self) -> Dict[str, Any]:
        """Serializar para enviar por MQTT."""
        return {
            "job_id": self.job_id,
            "in_strIDSolicitudAseguradora": self.in_strIDSolicitudAseguradora,
            "payload": self.payload,
            "created_at": self.created_at.isoformat()
        }


class JobResponse(BaseModel):
    """Respuesta al crear un job."""
    job_id: str
    aseguradora: str
    status: JobStatus
    message: str
    queued_at: datetime
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "aseguradora": "hdi",
                "status": "pending",
                "message": "Tarea encolada exitosamente",
                "queued_at": "2026-01-23T10:30:00"
            }
        }
    }

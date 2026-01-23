"""
Modelos Pydantic para Jobs/Tareas de cotización.

Estos modelos representan las tareas que se encolan en MQTT
para ser procesadas por los workers (bots de Selenium).
"""

from enum import Enum
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


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
    
    El payload específico depende de la aseguradora y se valida
    en el mapper correspondiente.
    """
    solicitud_aseguradora_id: str = Field(
        ...,
        description="ID único de la solicitud (viene del sistema externo)",
        examples=["abc123xyz"]
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Datos específicos para el bot de la aseguradora"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "solicitud_aseguradora_id": "abc123xyz",
                "payload": {
                    "in_strTipoDoc": "CC",
                    "in_strNumDoc": "1234567890",
                    "in_strPlaca": "ABC123"
                }
            }
        }
    }


class Job(BaseModel):
    """Representación completa de un job."""
    job_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="ID único del job generado por el sistema"
    )
    aseguradora: Aseguradora
    solicitud_aseguradora_id: str
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
            "solicitud_aseguradora_id": self.solicitud_aseguradora_id,
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

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
    
    El JSON de entrada usa los nombres estándar de la API de bots:
    - in_strIDSolicitudAseguradora: ID de la solicitud
    - Resto de campos: datos específicos del bot
    """
    in_strIDSolicitudAseguradora: str = Field(
        ...,
        alias="in_strIDSolicitudAseguradora",
        description="ID único de la solicitud (viene del sistema externo)",
        examples=["abc123xyz"]
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Datos específicos para el bot de la aseguradora"
    )
    
    model_config = {
        "populate_by_name": True,  # Permite usar tanto el alias como el nombre
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
        
        Esto permite enviar un JSON plano como en el documento de integración.
        """
        solicitud_id = data.pop("in_strIDSolicitudAseguradora", None)
        
        # Todo lo que no sea el ID va al payload
        payload = data.pop("payload", {})
        # Agregar campos adicionales al payload
        payload.update({k: v for k, v in data.items()})
        
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

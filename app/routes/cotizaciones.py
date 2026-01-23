"""
Rutas de cotizaciones - Endpoint principal para encolar tareas.

POST /cotizaciones/{aseguradora}
    Encola una tarea de cotización para la aseguradora especificada.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth import verify_token
from app.models.responses import APIResponse, ErrorResponse
from app.models.job import Aseguradora, Job, JobCreate, JobResponse, JobStatus

from mosquitto.mqtt_service import MQTTService, get_mqtt_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cotizaciones",
    tags=["Cotizaciones"],
    responses={
        401: {"model": ErrorResponse, "description": "No autorizado"},
        422: {"model": ErrorResponse, "description": "Error de validación"}
    }
)


@router.post(
    "/{aseguradora}",
    response_model=APIResponse[JobResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Encolar tarea de cotización",
    description="""
    Encola una nueva tarea de cotización para ser procesada por el bot correspondiente.
    
    La tarea se publica en el topic MQTT `bots/queue/{aseguradora}` y será procesada
    por un worker cuando esté disponible.
    
    **Aseguradoras soportadas:** hdi, sura, axa, allianz, bolivar, equidad, mundial, sbs, solidaria, runt
    """
)
async def crear_cotizacion(
    aseguradora: str,
    data: JobCreate,
    token: str = Depends(verify_token),
    mqtt: MQTTService = Depends(get_mqtt_service)
) -> APIResponse[JobResponse]:
    """Encolar nueva tarea de cotización."""
    
    # Validar aseguradora
    aseguradora_lower = aseguradora.lower()
    try:
        aseg_enum = Aseguradora(aseguradora_lower)
    except ValueError:
        aseguradoras_validas = [a.value for a in Aseguradora]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": f"Aseguradora '{aseguradora}' no soportada",
                "aseguradoras_validas": aseguradoras_validas
            }
        )
    
    # Crear job
    job = Job(
        aseguradora=aseg_enum,
        solicitud_aseguradora_id=data.solicitud_aseguradora_id,
        payload=data.payload
    )
    
    # Publicar en MQTT
    try:
        success = await mqtt.publish_task(
            aseguradora=aseguradora_lower,
            task_data=job.to_mqtt_message()
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error al encolar tarea en MQTT"
            )
            
    except Exception as e:
        logger.error(f"Error publicando en MQTT: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error de conexión con el broker MQTT: {str(e)}"
        )
    
    logger.info(
        f"[{aseguradora_lower.upper()}] Job {job.job_id} encolado - "
        f"Solicitud: {data.solicitud_aseguradora_id}"
    )
    
    return APIResponse(
        success=True,
        message=f"Tarea encolada para {aseguradora_lower.upper()}",
        data=JobResponse(
            job_id=job.job_id,
            aseguradora=aseguradora_lower,
            status=JobStatus.PENDING,
            message="Tarea encolada exitosamente. Será procesada por el un worker disponible.",
            queued_at=job.created_at
        )
    )


@router.post(
    "/batch",
    response_model=APIResponse[list[JobResponse]],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Encolar múltiples cotizaciones",
    description="Encola tareas para múltiples aseguradoras en una sola llamada."
)
async def crear_cotizaciones_batch(
    jobs: list[dict],
    token: str = Depends(verify_token),
    mqtt: MQTTService = Depends(get_mqtt_service)
) -> APIResponse[list[JobResponse]]:
    """
    Encolar múltiples tareas de cotización.
    
    Body:
    ```json
    [
        {"aseguradora": "hdi", "solicitud_aseguradora_id": "abc", "payload": {...}},
        {"aseguradora": "sura", "solicitud_aseguradora_id": "abc", "payload": {...}}
    ]
    ```
    """
    results = []
    errors = []
    
    for item in jobs:
        aseguradora = item.get("aseguradora", "").lower()
        
        # Validar aseguradora
        try:
            aseg_enum = Aseguradora(aseguradora)
        except ValueError:
            errors.append(f"Aseguradora '{aseguradora}' no válida")
            continue
        
        # Crear job
        job = Job(
            aseguradora=aseg_enum,
            solicitud_aseguradora_id=item.get("solicitud_aseguradora_id", ""),
            payload=item.get("payload", {})
        )
        
        # Publicar
        try:
            await mqtt.publish_task(aseguradora, task_data=job.to_mqtt_message())
            results.append(JobResponse(
                job_id=job.job_id,
                aseguradora=aseguradora,
                status=JobStatus.PENDING,
                message="Encolado",
                queued_at=job.created_at
            ))
        except Exception as e:
            errors.append(f"{aseguradora}: {str(e)}")
    
    message = f"{len(results)} tareas encoladas"
    if errors:
        message += f", {len(errors)} errores"
    
    return APIResponse(
        success=len(results) > 0,
        message=message,
        data=results
    )

"""
Dead Letter Queue (DLQ) endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException, Path

from app.services.dlq_manager import get_dlq_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["DLQ"], prefix="/api/dlq")


@router.get(
    "",
    summary="Lista todos los mensajes DLQ",
    description="lista todos los mensajes de todas las aseguradoras bajo el topic dlq."
)
async def list_all_dlq_messages():
    """
    Returns:
        Lista con los mensajes DLQ
    """
    try:
        dlq_manager = get_dlq_manager()
        messages = await dlq_manager.list_all()
        return {
            "count": len(messages),
            "messages": messages
        }
    
    except Exception as e:
        logger.error(f"Error extrayendo los mensajes DLQ: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error extrayendo los mensajes DLQ: {str(e)}"
        )


@router.get(
    "/{aseguradora}",
    summary="Lista los mensajes DLQ por aseguradora",
    description="Mensajes DLQ filtrados por aseguradora"
)
async def list_dlq_by_aseguradora(
    aseguradora: str = Path(..., description="Identificador de la aseguradora (e.g., sbs, hdi)")
):
    """
    Args:
        aseguradora: Identificador de la aseguradora
    
    Returns:
        Lista de los mensajes DLQ de la aseguradora
    """
    try:
        dlq_manager = get_dlq_manager()
        messages = await dlq_manager.list_by_aseguradora(aseguradora)
        return {
            "aseguradora": aseguradora,
            "count": len(messages),
            "messages": messages
        }
    
    except Exception as e:
        logger.error(f"Error extrayendo mensajes DLQ para {aseguradora}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listando mensajes DLQ: {str(e)}"
        )


@router.post(
    "/{job_id}/retry",
    summary="Reintenta un mensajes DLQ",
    description="""
    Reintenta un job fallido hallado en el DLQ, republicandolo en la queue original.
    
    El job sera recreado:
    - retry_count: 0
    - error_history cleared
    - Republicado a bots/queue/{aseguradora}
    """
)
async def retry_dlq_message(
    job_id: str = Path(..., description="Job ID a reintentar")
):
    """
    Args:
        job_id: Job id a reintentar
    
    Returns:
        Success status y job_id
    """
    try:
        dlq_manager = get_dlq_manager()
        success = await dlq_manager.retry_message(job_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} no encontrado en DLQ"
            )
        
        return {
            "status": "requeued",
            "job_id": job_id,
            "message": f"Job {job_id} ha sido republicado para reintento"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error republicando job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reintentando job: {str(e)}"
        )

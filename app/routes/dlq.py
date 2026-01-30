"""
Dead Letter Queue (DLQ) management endpoints.

Provides API for listing and retrying failed jobs.
"""

import logging
from fastapi import APIRouter, HTTPException, Path

from app.services.dlq_manager import get_dlq_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["DLQ"], prefix="/api/dlq")


@router.get(
    "",
    summary="List all DLQ messages",
    description="Get all messages in the Dead Letter Queue across all aseguradoras."
)
async def list_all_dlq_messages():
    """
    List all DLQ messages.
    
    Returns:
        List of DLQ messages with full metadata
    """
    try:
        dlq_manager = get_dlq_manager()
        messages = await dlq_manager.list_all()
        return {
            "count": len(messages),
            "messages": messages
        }
    
    except Exception as e:
        logger.error(f"Error listing DLQ messages: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing DLQ messages: {str(e)}"
        )


@router.get(
    "/{aseguradora}",
    summary="List DLQ messages by aseguradora",
    description="Get DLQ messages filtered by insurance company."
)
async def list_dlq_by_aseguradora(
    aseguradora: str = Path(..., description="Insurance company identifier (e.g., sbs, hdi)")
):
    """
    List DLQ messages for specific aseguradora.
    
    Args:
        aseguradora: Insurance company identifier
    
    Returns:
        List of DLQ messages for the aseguradora
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
        logger.error(f"Error listing DLQ messages for {aseguradora}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing DLQ messages: {str(e)}"
        )


@router.post(
    "/{job_id}/retry",
    summary="Retry a DLQ message",
    description="""
    Retry a failed job from the DLQ by republishing it to the original queue.
    
    The message will be reset:
    - retry_count set to 0
    - error_history cleared
    - Republished to bots/queue/{aseguradora}
    """
)
async def retry_dlq_message(
    job_id: str = Path(..., description="Job ID to retry")
):
    """
    Retry a DLQ message.
    
    Args:
        job_id: Job identifier to retry
    
    Returns:
        Success status and job_id
    """
    try:
        dlq_manager = get_dlq_manager()
        success = await dlq_manager.retry_message(job_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found in DLQ"
            )
        
        return {
            "status": "requeued",
            "job_id": job_id,
            "message": f"Job {job_id} has been requeued for retry"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying DLQ message {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrying message: {str(e)}"
        )

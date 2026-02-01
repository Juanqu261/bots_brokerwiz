"""
Dead Letter Queue (DLQ) manager.

Manages DLQ messages: storage, retrieval, and retry functionality.
"""

import logging
import asyncio
from typing import Optional
from collections import defaultdict

import aiomqtt

from config.settings import settings
from workers.models import JobMessage

logger = logging.getLogger(__name__)


class DLQManager:
    """
    Manages Dead Letter Queue messages.
    
    Subscribes to all DLQ topics and stores messages in memory.
    Provides filtering and retry functionality.
    """
    
    def __init__(self):
        """Initialize DLQ manager."""
        self.messages: dict[str, JobMessage] = {}  # job_id -> JobMessage
        self.by_aseguradora: dict[str, list[str]] = defaultdict(list)  # aseguradora -> [job_ids]
        self._lock = asyncio.Lock()
        self._subscriber_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start DLQ subscriber in background."""
        if self._subscriber_task is None or self._subscriber_task.done():
            self._subscriber_task = asyncio.create_task(self._subscribe_to_dlq())
            logger.info("DLQ manager started")
    
    async def stop(self) -> None:
        """Stop DLQ subscriber."""
        if self._subscriber_task and not self._subscriber_task.done():
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
            logger.info("DLQ manager stopped")
    
    async def _subscribe_to_dlq(self) -> None:
        """Subscribe to all DLQ topics and store messages."""
        while True:
            try:
                async with aiomqtt.Client(
                    hostname=settings.mqtt.MQTT_HOST,
                    port=settings.mqtt.MQTT_PORT,
                    identifier="dlq-manager",
                    clean_session=False
                ) as client:
                    # Subscribe to all DLQ topics
                    await client.subscribe("bots/dlq/#")
                    logger.info("Subscribed to DLQ topics: bots/dlq/#")
                    
                    async for message in client.messages:
                        try:
                            topic = str(message.topic)
                            payload = message.payload.decode('utf-8')
                            
                            # Extract aseguradora from topic: bots/dlq/{aseguradora}
                            parts = topic.split('/')
                            if len(parts) >= 3:
                                aseguradora = parts[2]
                                
                                # Parse message
                                job_message = JobMessage.from_json(payload)
                                
                                # Store in memory
                                async with self._lock:
                                    self.messages[job_message.job_id] = job_message
                                    if job_message.job_id not in self.by_aseguradora[aseguradora]:
                                        self.by_aseguradora[aseguradora].append(job_message.job_id)
                                
                                logger.info(
                                    f"DLQ message stored: {job_message.job_id} "
                                    f"(aseguradora={aseguradora})"
                                )
                        
                        except Exception as e:
                            logger.error(f"Error processing DLQ message: {e}")
            
            except Exception as e:
                logger.warning(f"DLQ subscriber disconnected: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
    
    async def list_all(self) -> list[dict]:
        """
        List all DLQ messages.
        
        Returns:
            List of DLQ messages as dictionaries
        """
        async with self._lock:
            return [msg.to_dict() for msg in self.messages.values()]
    
    async def list_by_aseguradora(self, aseguradora: str) -> list[dict]:
        """
        List DLQ messages for specific aseguradora.
        
        Args:
            aseguradora: Insurance company identifier
        
        Returns:
            List of DLQ messages for the aseguradora
        """
        async with self._lock:
            job_ids = self.by_aseguradora.get(aseguradora.lower(), [])
            return [
                self.messages[job_id].to_dict()
                for job_id in job_ids
                if job_id in self.messages
            ]
    
    async def get_message(self, job_id: str) -> Optional[JobMessage]:
        """
        Get specific DLQ message by job_id.
        
        Args:
            job_id: Job identifier
        
        Returns:
            JobMessage if found, None otherwise
        """
        async with self._lock:
            return self.messages.get(job_id)
    
    async def retry_message(self, job_id: str) -> bool:
        """
        Retry a DLQ message by republishing to original topic.
        
        Resets retry_count to 0 and clears error_history.
        
        Args:
            job_id: Job identifier to retry
        
        Returns:
            True if message was found and requeued, False otherwise
        """
        # Get message
        message = await self.get_message(job_id)
        if not message:
            logger.warning(f"DLQ message not found: {job_id}")
            return False
        
        # Find aseguradora
        aseguradora = None
        async with self._lock:
            for aseg, job_ids in self.by_aseguradora.items():
                if job_id in job_ids:
                    aseguradora = aseg
                    break
        
        if not aseguradora:
            logger.error(f"Could not determine aseguradora for job {job_id}")
            return False
        
        # Reset message for retry
        message.reset_for_retry()
        
        # Republish to original topic
        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt.MQTT_HOST,
                port=settings.mqtt.MQTT_PORT,
                identifier="dlq-retry"
            ) as client:
                topic = f"bots/queue/{aseguradora}"
                await client.publish(
                    topic=topic,
                    payload=message.to_json(),
                    qos=1
                )
                
                logger.info(f"DLQ message {job_id} requeued to {topic}")
                
                # Remove from DLQ storage
                async with self._lock:
                    self.messages.pop(job_id, None)
                    if job_id in self.by_aseguradora[aseguradora]:
                        self.by_aseguradora[aseguradora].remove(job_id)
                
                return True
        
        except Exception as e:
            logger.error(f"Error retrying DLQ message {job_id}: {e}")
            return False


# Global DLQ manager instance
_dlq_manager: Optional[DLQManager] = None
_dlq_started = False


def get_dlq_manager() -> DLQManager:
    """Get or create DLQ manager singleton."""
    global _dlq_manager
    if _dlq_manager is None:
        _dlq_manager = DLQManager()
    return _dlq_manager


async def ensure_dlq_started() -> None:
    """Ensure DLQ manager is started only once across all workers."""
    global _dlq_started
    if not _dlq_started:
        dlq = get_dlq_manager()
        await dlq.start()
        _dlq_started = True
        logger.info("DLQ manager started (singleton)")


async def ensure_dlq_stopped() -> None:
    """Stop DLQ manager."""
    global _dlq_started
    if _dlq_started:
        dlq = get_dlq_manager()
        await dlq.stop()
        _dlq_started = False
        logger.info("DLQ manager stopped")

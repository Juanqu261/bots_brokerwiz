"""
Retry manager for multi-tier retry logic.

Handles immediate retry, delayed retry with exponential backoff, and DLQ publishing.
"""

import asyncio
import logging
from enum import Enum
from typing import Optional

from workers.errors import ErrorType
from workers.models import JobMessage, ErrorDetail
from workers.error_classifier import ErrorClassifier

logger = logging.getLogger(__name__)


class RetryAction(Enum):
    """Action to take after a failure."""
    IMMEDIATE_RETRY = "IMMEDIATE_RETRY"  # Retry once immediately
    REQUEUE = "REQUEUE"                  # Requeue with delay
    DLQ = "DLQ"                          # Send to Dead Letter Queue


class RetryManager:
    """
    Manages retry logic for failed bot executions.
    
    Implements 3-tier retry strategy:
    - Tier 1: Immediate retry for transient errors
    - Tier 2: Delayed retry with exponential backoff for retriable errors
    - Tier 3: Dead Letter Queue for permanent errors or max retries exceeded
    """
    
    def __init__(self, mqtt_client, max_retries: int = 3):
        """
        Initialize retry manager.
        
        Args:
            mqtt_client: MQTT client for publishing messages
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.mqtt_client = mqtt_client
        self.max_retries = max_retries
        self.error_classifier = ErrorClassifier()
    
    def handle_failure(
        self,
        message: JobMessage,
        exception: Exception,
        already_retried_immediately: bool = False
    ) -> RetryAction:
        """
        Determine retry action based on error type and retry count.
        
        Args:
            message: The job message that failed
            exception: The exception that occurred
            already_retried_immediately: Whether immediate retry was already attempted
        
        Returns:
            RetryAction enum indicating what to do next
        """
        error_type = self.error_classifier.classify(exception)
        error_code = self.error_classifier.get_error_code(exception)
        
        logger.info(
            f"[{message.job_id}] Failure classified: "
            f"type={error_type.value}, code={error_code}, "
            f"retry_count={message.retry_count}/{message.max_retries}"
        )
        
        # Tier 1: Immediate retry for transient errors (only if not already tried)
        if error_type == ErrorType.TRANSIENT and not already_retried_immediately:
            return RetryAction.IMMEDIATE_RETRY
        
        # Tier 3: Permanent errors go straight to DLQ
        if error_type == ErrorType.PERMANENT:
            logger.warning(
                f"[{message.job_id}] Permanent error {error_code}, sending to DLQ"
            )
            return RetryAction.DLQ
        
        # Tier 3: Max retries exceeded, send to DLQ
        if message.is_max_retries_exceeded():
            logger.warning(
                f"[{message.job_id}] Max retries ({message.max_retries}) exceeded, sending to DLQ"
            )
            return RetryAction.DLQ
        
        # Tier 2: Retriable errors get delayed retry
        if error_type == ErrorType.RETRIABLE or error_type == ErrorType.TRANSIENT:
            return RetryAction.REQUEUE
        
        # Default to DLQ for safety
        return RetryAction.DLQ
    
    async def requeue_with_delay(
        self,
        message: JobMessage,
        aseguradora: str
    ) -> None:
        """
        Requeue message to original topic after exponential backoff delay.
        
        Args:
            message: Job message to requeue
            aseguradora: Insurance company identifier for topic routing
        """
        # Increment retry counter
        message.increment_retry()
        
        # Calculate delay
        delay = self.calculate_delay(message.retry_count)
        
        logger.info(
            f"[{message.job_id}] Requeueing with delay: "
            f"retry {message.retry_count}/{message.max_retries}, delay={delay}s"
        )
        
        # Wait for delay
        await asyncio.sleep(delay)
        
        # Publish back to original topic
        topic = f"bots/queue/{aseguradora}"
        await self.mqtt_client.publish_task(aseguradora, message.to_dict())
        
        logger.info(f"[{message.job_id}] Requeued to {topic}")
    
    async def send_to_dlq(
        self,
        message: JobMessage,
        aseguradora: str
    ) -> None:
        """
        Publish message to Dead Letter Queue topic.
        
        Args:
            message: Job message to send to DLQ
            aseguradora: Insurance company identifier for DLQ topic routing
        """
        dlq_topic = f"bots/dlq/{aseguradora}"
        
        logger.warning(
            f"[{message.job_id}] Sending to DLQ: {dlq_topic} "
            f"(retry_count={message.retry_count}, errors={len(message.error_history)})"
        )
        
        # Publish to DLQ topic with QoS 1 for persistence
        # Use the internal client publish method
        try:
            await self.mqtt_client._client.publish(
                topic=dlq_topic,
                payload=message.to_json(),
                qos=1,
                retain=False
            )
            logger.info(f"[{message.job_id}] Successfully sent to DLQ: {dlq_topic}")
        except Exception as e:
            logger.error(f"[{message.job_id}] Failed to send to DLQ: {dlq_topic} - {e}")
    
    def calculate_delay(self, retry_count: int) -> int:
        """
        Calculate exponential backoff delay.
        
        Formula: 2^retry_count seconds
        
        Args:
            retry_count: Current retry attempt number (1, 2, 3, ...)
        
        Returns:
            Delay in seconds (2, 4, 8, ...)
        """
        return 2 ** retry_count
    
    def create_error_detail(
        self,
        exception: Exception,
        error_type: ErrorType,
        error_code: str,
        include_stack_trace: bool = False
    ) -> ErrorDetail:
        """
        Create ErrorDetail from exception.
        
        Args:
            exception: The exception that occurred
            error_type: Classified error type
            error_code: Error code identifier
            include_stack_trace: Whether to include full stack trace
        
        Returns:
            ErrorDetail instance
        """
        return ErrorDetail.from_exception(
            exception=exception,
            error_type=error_type,
            error_code=error_code,
            include_stack_trace=include_stack_trace
        )

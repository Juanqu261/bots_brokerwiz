"""
Data models for production hardening features.

Defines message format with retry metadata and error tracking.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any
import json

from workers.errors import ErrorType


@dataclass
class ErrorDetail:
    """Details of a single error occurrence."""
    
    timestamp: str
    error_type: str  # TRANSIENT | RETRIABLE | PERMANENT
    error_code: str
    error_message: str
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ErrorDetail":
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        error_type: ErrorType,
        error_code: str,
        include_stack_trace: bool = False
    ) -> "ErrorDetail":
        """
        Create ErrorDetail from an exception.
        
        Args:
            exception: The exception that occurred
            error_type: Classified error type
            error_code: Error code identifier
            include_stack_trace: Whether to include full stack trace
        
        Returns:
            ErrorDetail instance
        """
        import traceback
        
        return cls(
            timestamp=datetime.utcnow().isoformat() + "Z",
            error_type=error_type.value,
            error_code=error_code,
            error_message=str(exception),
            stack_trace=traceback.format_exc() if include_stack_trace else None
        )


@dataclass
class JobMessage:
    """
    Enhanced job message with retry metadata.
    
    Supports backward compatibility with messages lacking retry fields.
    """
    
    job_id: str
    payload: dict
    retry_count: int = 0
    max_retries: int = 3
    first_attempt_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_error: Optional[ErrorDetail] = None
    error_history: list[ErrorDetail] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary for MQTT publishing.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "job_id": self.job_id,
            "payload": self.payload,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "first_attempt_at": self.first_attempt_at,
            "last_error": self.last_error.to_dict() if self.last_error else None,
            "error_history": [e.to_dict() for e in self.error_history]
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: dict) -> "JobMessage":
        """
        Create from dictionary (MQTT message).
        
        Handles backward compatibility by initializing missing retry metadata
        with default values. Also handles legacy message format where extra
        fields are at the root level instead of inside payload.
        
        Args:
            data: Dictionary from MQTT message
        
        Returns:
            JobMessage instance
        """
        # Extract known JobMessage fields
        job_id = data.get("job_id", "unknown")
        payload = data.get("payload", {})
        
        # Backward compatibility: initialize missing retry metadata
        retry_count = data.get("retry_count", 0)
        max_retries = data.get("max_retries", 3)
        first_attempt_at = data.get("first_attempt_at", datetime.utcnow().isoformat() + "Z")
        last_error = data.get("last_error")
        error_history = data.get("error_history", [])
        
        # Handle legacy format: extra fields at root level should go into payload
        # This includes fields like in_strIDSolicitudAseguradora, in_strPlaca, etc.
        known_fields = {
            "job_id", "payload", "retry_count", "max_retries", 
            "first_attempt_at", "last_error", "error_history", "timestamp"
        }
        
        for key, value in data.items():
            if key not in known_fields and key not in payload:
                payload[key] = value
        
        # Convert error dicts to ErrorDetail objects
        if last_error is not None:
            last_error = ErrorDetail.from_dict(last_error)
        
        error_history = [
            ErrorDetail.from_dict(e) if isinstance(e, dict) else e
            for e in error_history
        ]
        
        return cls(
            job_id=job_id,
            payload=payload,
            retry_count=retry_count,
            max_retries=max_retries,
            first_attempt_at=first_attempt_at,
            last_error=last_error,
            error_history=error_history
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "JobMessage":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def add_error(self, error_detail: ErrorDetail) -> None:
        """
        Add error to history and update last_error.
        
        Args:
            error_detail: Error details to add
        """
        self.error_history.append(error_detail)
        self.last_error = error_detail
    
    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1
    
    def reset_for_retry(self) -> None:
        """
        Reset message for manual retry from DLQ.
        
        Clears retry_count and error_history while preserving original payload.
        """
        self.retry_count = 0
        self.error_history = []
        self.last_error = None
    
    def should_retry(self) -> bool:
        """
        Check if message should be retried.
        
        Returns:
            True if retry_count < max_retries
        """
        return self.retry_count < self.max_retries
    
    def is_max_retries_exceeded(self) -> bool:
        """
        Check if maximum retries have been exceeded.
        
        Returns:
            True if retry_count >= max_retries
        """
        return self.retry_count >= self.max_retries


# Type alias for convenience
Message = JobMessage

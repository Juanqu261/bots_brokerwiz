"""
Error handling infrastructure for BrokerWiz bot automation system.

Defines error type hierarchy and classification for multi-tier retry logic.
"""

from enum import Enum
from typing import Optional


class ErrorType(Enum):
    """Error classification for retry logic."""
    TRANSIENT = "TRANSIENT"      # Immediate retry
    RETRIABLE = "RETRIABLE"      # Delayed retry with backoff
    PERMANENT = "PERMANENT"      # Send to DLQ, no retry


class BrokerWizError(Exception):
    """Base exception for all BrokerWiz errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__


class TransientError(BrokerWizError):
    """
    Transient error that may succeed on immediate retry.
    
    Examples:
    - Network timeouts
    - Stale element references
    - Temporary connection issues
    """
    pass


class RetriableError(BrokerWizError):
    """
    Retriable error that needs delay before retry.
    
    Examples:
    - Resource exhaustion
    - Rate limiting
    - Captcha timeout
    """
    pass


class PermanentError(BrokerWizError):
    """
    Permanent error that will not succeed on retry.
    
    Examples:
    - Invalid credentials
    - Bot not implemented
    - Invalid payload
    """
    pass


# Specific error types for common scenarios

class RateLimitError(RetriableError):
    """Rate limit exceeded, needs cooldown period."""
    pass


class ResourceExhaustedError(RetriableError):
    """System resources exhausted (CPU, RAM, slots)."""
    pass


class AuthenticationError(PermanentError):
    """Authentication failed with invalid credentials."""
    pass


class InvalidCredentialsError(PermanentError):
    """Credentials are invalid or expired."""
    pass


class BotNotImplementedError(PermanentError):
    """Bot for requested aseguradora is not implemented."""
    pass


class ValidationError(PermanentError):
    """Payload validation failed."""
    pass

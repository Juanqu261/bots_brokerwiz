"""
Error classifier for determining retry strategy.

Classifies exceptions into TRANSIENT, RETRIABLE, or PERMANENT categories
to determine appropriate retry behavior.
"""

import logging
import re
from typing import Optional

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException
)

from workers.errors import (
    ErrorType,
    BrokerWizError,
    TransientError,
    RetriableError,
    PermanentError,
    RateLimitError,
    ResourceExhaustedError,
    AuthenticationError,
    InvalidCredentialsError,
    BotNotImplementedError,
    ValidationError
)

logger = logging.getLogger(__name__)


class ErrorClassifier:
    """
    Classifies exceptions to determine retry strategy.
    
    Classification Rules:
    - TRANSIENT: Network timeouts, stale elements, temporary connection issues
    - RETRIABLE: Resource exhaustion, rate limiting, captcha timeouts
    - PERMANENT: Invalid credentials, unimplemented bots, validation errors
    - Unknown exceptions default to RETRIABLE (safe default)
    """
    
    # Patterns for detecting stale element in WebDriverException messages
    STALE_ELEMENT_PATTERNS = [
        r"stale element",
        r"element is not attached",
        r"element reference is stale"
    ]
    
    def classify(self, exception: Exception) -> ErrorType:
        """
        Classify exception into error type.
        
        Args:
            exception: The exception to classify
        
        Returns:
            ErrorType enum value (TRANSIENT, RETRIABLE, or PERMANENT)
        """
        # Check if it's already a BrokerWizError with explicit type
        if isinstance(exception, TransientError):
            return ErrorType.TRANSIENT
        elif isinstance(exception, RetriableError):
            return ErrorType.RETRIABLE
        elif isinstance(exception, PermanentError):
            return ErrorType.PERMANENT
        
        # Classify Selenium exceptions
        if isinstance(exception, (TimeoutException, NoSuchElementException)):
            return ErrorType.TRANSIENT
        
        if isinstance(exception, StaleElementReferenceException):
            return ErrorType.TRANSIENT
        
        if isinstance(exception, WebDriverException):
            # Check if message contains stale element indicators
            if self._is_stale_element_error(exception):
                return ErrorType.TRANSIENT
            # Other WebDriver exceptions are retriable
            return ErrorType.RETRIABLE
        
        # Classify by exception type name (for custom errors without inheritance)
        exception_name = exception.__class__.__name__.lower()
        
        if "auth" in exception_name or "credential" in exception_name:
            return ErrorType.PERMANENT
        
        if "notimplemented" in exception_name or "validation" in exception_name:
            return ErrorType.PERMANENT
        
        if "ratelimit" in exception_name or "resource" in exception_name:
            return ErrorType.RETRIABLE
        
        # Default to RETRIABLE for unknown exceptions (safe default)
        logger.debug(f"Unknown exception type {type(exception).__name__}, defaulting to RETRIABLE")
        return ErrorType.RETRIABLE
    
    def get_error_code(self, exception: Exception) -> str:
        """
        Extract or generate error code from exception.
        
        Args:
            exception: The exception to extract code from
        
        Returns:
            Error code string (e.g., "CAPTCHA_001", "AUTH_001")
        """
        # If it's a BrokerWizError, use its error_code attribute
        if isinstance(exception, BrokerWizError) and hasattr(exception, 'error_code'):
            return exception.error_code
        
        # Generate code from exception class name
        exception_name = exception.__class__.__name__
        
        # Convert CamelCase to UPPER_SNAKE_CASE
        error_code = re.sub(r'(?<!^)(?=[A-Z])', '_', exception_name).upper()
        
        # Remove "EXCEPTION" or "ERROR" suffix if present
        error_code = re.sub(r'_(EXCEPTION|ERROR)$', '', error_code)
        
        return error_code
    
    def _is_stale_element_error(self, exception: WebDriverException) -> bool:
        """
        Check if WebDriverException is a stale element error.
        
        Args:
            exception: WebDriverException to check
        
        Returns:
            True if message contains stale element indicators
        """
        message = str(exception).lower()
        return any(re.search(pattern, message, re.IGNORECASE) 
                  for pattern in self.STALE_ELEMENT_PATTERNS)

from fastapi import HTTPException
from typing import Optional, Dict, Any

class ChatDevException(HTTPException):
    """
    Base exception class for ChatDev API errors
    
    This provides a consistent way to handle and report errors in the API.
    """
    def __init__(
        self, 
        status_code: int, 
        detail: str, 
        error_type: str,
        headers: Optional[Dict[str, Any]] = None
    ):
        self.error_type = error_type
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class AuthenticationError(ChatDevException):
    """
    Exception raised for authentication errors
    """
    def __init__(self, detail: str = "Authentication failed", headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=401,
            detail=detail,
            error_type="authentication_error",
            headers=headers
        )

class AuthorizationError(ChatDevException):
    """
    Exception raised for authorization errors
    """
    def __init__(self, detail: str = "Not authorized", headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=403,
            detail=detail,
            error_type="authorization_error",
            headers=headers
        )

class ResourceNotFoundError(ChatDevException):
    """
    Exception raised when a requested resource is not found
    """
    def __init__(self, detail: str = "Resource not found", headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=404,
            detail=detail,
            error_type="not_found_error",
            headers=headers
        )

class ValidationError(ChatDevException):
    """
    Exception raised for validation errors
    """
    def __init__(self, detail: str = "Validation error", headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=422,
            detail=detail,
            error_type="validation_error",
            headers=headers
        )

class RateLimitError(ChatDevException):
    """
    Exception raised when the rate limit is exceeded
    """
    def __init__(self, detail: str = "Rate limit exceeded", headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=429,
            detail=detail,
            error_type="rate_limit_error",
            headers=headers
        )

class InternalServerError(ChatDevException):
    """
    Exception raised for internal server errors
    """
    def __init__(self, detail: str = "Internal server error", headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=500,
            detail=detail,
            error_type="server_error",
            headers=headers
        )

class TaskCancellationError(ChatDevException):
    """
    Exception raised when a task cancellation fails
    """
    def __init__(self, detail: str = "Failed to cancel task", headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=400,
            detail=detail,
            error_type="task_cancellation_error",
            headers=headers
        )
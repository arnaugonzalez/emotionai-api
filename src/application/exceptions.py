"""
Application Layer Exceptions

These exceptions represent business rules violations and application-specific errors.
They are part of the application layer and can be caught and handled appropriately.
"""

from typing import Optional, Dict, Any


class ApplicationException(Exception):
    """Base exception for all application layer exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationException(ApplicationException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(message)
        self.field = field
        self.value = value


class UserNotFoundException(ApplicationException):
    """Raised when a user cannot be found"""
    
    def __init__(self, user_id: str):
        super().__init__(f"User with ID {user_id} not found")
        self.user_id = user_id


class AgentServiceException(ApplicationException):
    """Raised when agent service operations fail"""
    
    def __init__(self, message: str, agent_type: Optional[str] = None):
        super().__init__(message)
        self.agent_type = agent_type


class TaggingServiceException(ApplicationException):
    """Raised when tagging service operations fail"""
    
    def __init__(self, message: str, content_type: Optional[str] = None):
        super().__init__(message)
        self.content_type = content_type


class UserKnowledgeServiceException(ApplicationException):
    """Raised when user knowledge service operations fail"""
    
    def __init__(self, message: str, user_id: Optional[str] = None):
        super().__init__(message)
        self.user_id = user_id


class RepositoryException(ApplicationException):
    """Raised when repository operations fail"""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message)
        self.operation = operation


class ExternalServiceException(ApplicationException):
    """Raised when external service calls fail"""
    
    def __init__(self, message: str, service_name: Optional[str] = None):
        super().__init__(message)
        self.service_name = service_name


class BusinessRuleViolationException(ApplicationException):
    """Raised when business rules are violated"""
    
    def __init__(self, message: str, rule_name: Optional[str] = None):
        super().__init__(message)
        self.rule_name = rule_name


class InsufficientPermissionsException(ApplicationException):
    """Raised when user lacks required permissions"""
    
    def __init__(self, message: str, required_permission: Optional[str] = None):
        super().__init__(message)
        self.required_permission = required_permission


class ResourceLimitExceededException(ApplicationException):
    """Raised when resource limits are exceeded"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, limit: Optional[int] = None):
        super().__init__(message)
        self.resource_type = resource_type
        self.limit = limit 
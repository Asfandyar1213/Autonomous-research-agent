"""
Exceptions Module

This module defines custom exceptions used throughout the application.
"""

class ResearchAgentError(Exception):
    """Base exception for all errors in the Research Agent"""
    pass


class QueryProcessingError(ResearchAgentError):
    """Raised when there is an error processing a research query"""
    pass


class APIError(ResearchAgentError):
    """Raised when there is an error with an external API"""
    def __init__(self, api_name, message, status_code=None, response=None):
        self.api_name = api_name
        self.status_code = status_code
        self.response = response
        super().__init__(f"{api_name} API Error: {message}")


class RateLimitError(APIError):
    """Raised when an API rate limit is exceeded"""
    def __init__(self, api_name, retry_after=None):
        self.retry_after = retry_after
        message = f"Rate limit exceeded for {api_name}"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(api_name, message)


class DocumentProcessingError(ResearchAgentError):
    """Raised when there is an error processing a document"""
    def __init__(self, document_id, message):
        self.document_id = document_id
        super().__init__(f"Error processing document {document_id}: {message}")


class AnalysisError(ResearchAgentError):
    """Raised when there is an error during analysis"""
    pass


class ModelError(ResearchAgentError):
    """Raised when there is an error with a machine learning model"""
    def __init__(self, model_name, message):
        self.model_name = model_name
        super().__init__(f"Error with model {model_name}: {message}")


class ReportGenerationError(ResearchAgentError):
    """Raised when there is an error generating a report"""
    pass


class ConfigurationError(ResearchAgentError):
    """Raised when there is an error in the configuration"""
    pass


class DatabaseError(ResearchAgentError):
    """Raised when there is a database error"""
    pass


class CacheError(ResearchAgentError):
    """Raised when there is a cache error"""
    pass


class ValidationError(ResearchAgentError):
    """Raised when there is a validation error"""
    pass


class AuthenticationError(ResearchAgentError):
    """Raised when there is an authentication error"""
    pass


class ResourceNotFoundError(ResearchAgentError):
    """Raised when a requested resource is not found"""
    def __init__(self, resource_type, resource_id):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} not found: {resource_id}")

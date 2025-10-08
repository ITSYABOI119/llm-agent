"""
Custom Exceptions
Provides specific exception types for better error handling and debugging
"""


class AgentError(Exception):
    """Base exception for all agent errors"""
    pass


class ToolExecutionError(AgentError):
    """Error during tool execution"""
    pass


class ValidationError(AgentError):
    """Input validation failed"""
    pass


class SecurityError(AgentError):
    """Security constraint violated"""
    pass


class ConfigurationError(AgentError):
    """Invalid configuration"""
    pass


class ModelError(AgentError):
    """Error communicating with LLM model"""
    pass


class ParseError(AgentError):
    """Error parsing LLM response"""
    pass


class RateLimitError(AgentError):
    """Rate limit exceeded"""
    pass


class ResourceLimitError(AgentError):
    """Resource quota exceeded"""
    pass


class FileOperationError(ToolExecutionError):
    """Error during file operation"""
    pass


class CommandExecutionError(ToolExecutionError):
    """Error executing shell command"""
    pass


class NetworkError(ToolExecutionError):
    """Error during network operation"""
    pass

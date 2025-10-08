"""
Base Tool Interface
Abstract base class for all tools to ensure consistent interface
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from pathlib import Path


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.

    All tools must implement the methods defined here to ensure
    consistent interface and behavior across the tool system.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize tool with configuration.

        Args:
            config: Agent configuration dictionary
        """
        self.config = config
        self.workspace = Path(config['agent']['workspace'])

    @abstractmethod
    def get_tool_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions of all tools provided by this module.

        Returns:
            Dict mapping tool names to their descriptions
            Format: {"tool_name": "Description of what the tool does"}
        """
        pass

    @abstractmethod
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with given parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool

        Returns:
            Result dictionary with at least:
            {
                "success": bool,
                "error": str (if success=False),
                "message": str (if success=True),
                ... other tool-specific fields
            }
        """
        pass

    def validate_parameters(self, required: list, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that required parameters are present.

        Args:
            required: List of required parameter names
            parameters: Parameter dictionary to validate

        Returns:
            {"success": True} if valid, or {"success": False, "error": msg} if invalid
        """
        missing = [p for p in required if p not in parameters]

        if missing:
            return {
                "success": False,
                "error": f"Missing required parameters: {', '.join(missing)}"
            }

        return {"success": True}


class FileToolMixin:
    """
    Mixin for tools that work with files.

    Provides common file-related utility methods.
    """

    def _get_safe_path(self, relative_path: str) -> Path:
        """
        Convert relative path to absolute and validate it's in workspace.

        Args:
            relative_path: Path relative to workspace

        Returns:
            Absolute Path object

        Raises:
            PermissionError: If path is outside workspace
        """
        from tools.utils import get_safe_path
        return get_safe_path(self.workspace, relative_path)

    def _format_file_result(self, success: bool, path: str,
                           message: str = None, error: str = None,
                           **kwargs) -> Dict[str, Any]:
        """
        Format a standardized file operation result.

        Args:
            success: Whether operation succeeded
            path: File path that was operated on
            message: Success message
            error: Error message
            **kwargs: Additional fields to include

        Returns:
            Formatted result dictionary
        """
        result = {
            "success": success,
            "path": path
        }

        if success and message:
            result["message"] = message
        elif not success and error:
            result["error"] = error

        result.update(kwargs)
        return result


class CommandToolMixin:
    """
    Mixin for tools that execute commands.

    Provides command validation and formatting utilities.
    """

    def _format_command_result(self, success: bool, command: str,
                               stdout: str = None, stderr: str = None,
                               exit_code: int = None, error: str = None,
                               **kwargs) -> Dict[str, Any]:
        """
        Format a standardized command execution result.

        Args:
            success: Whether command succeeded
            command: Command that was executed
            stdout: Standard output
            stderr: Standard error
            exit_code: Command exit code
            error: Error message
            **kwargs: Additional fields

        Returns:
            Formatted result dictionary
        """
        result = {
            "success": success,
            "command": command
        }

        if stdout is not None:
            result["stdout"] = stdout
        if stderr is not None:
            result["stderr"] = stderr
        if exit_code is not None:
            result["exit_code"] = exit_code
        if error is not None:
            result["error"] = error

        result.update(kwargs)
        return result


class SearchToolMixin:
    """
    Mixin for tools that perform search operations.

    Provides search result formatting utilities.
    """

    def _format_search_result(self, success: bool, pattern: str,
                             matches: list = None, count: int = 0,
                             error: str = None, **kwargs) -> Dict[str, Any]:
        """
        Format a standardized search result.

        Args:
            success: Whether search succeeded
            pattern: Search pattern used
            matches: List of matches found
            count: Number of matches
            error: Error message
            **kwargs: Additional fields

        Returns:
            Formatted result dictionary
        """
        result = {
            "success": success,
            "pattern": pattern,
            "count": count
        }

        if matches is not None:
            result["matches"] = matches
        if error is not None:
            result["error"] = error

        result.update(kwargs)
        return result

"""
Shared Utility Functions
Common utilities used across multiple tool modules
"""

from pathlib import Path


def get_safe_path(workspace: Path, relative_path: str) -> Path:
    """
    Convert relative path to absolute path and validate it's within workspace.

    Args:
        workspace: The workspace root directory (Path object)
        relative_path: The relative path to validate

    Returns:
        Resolved absolute Path object

    Raises:
        PermissionError: If the path is outside the workspace
    """
    # Resolve the full path
    full_path = (workspace / relative_path).resolve()

    # Check if path is within workspace
    try:
        full_path.relative_to(workspace)
    except ValueError:
        raise PermissionError(f"Path {relative_path} is outside workspace")

    return full_path


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes to human-readable string.

    Args:
        bytes_value: Number of bytes

    Returns:
        Human-readable string (e.g., "1.5GB")
    """
    value: float = float(bytes_value)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if value < 1024.0:
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{value:.1f}PB"

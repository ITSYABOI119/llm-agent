"""
Basic File System Operations
Handles fundamental file/folder operations: create, read, write, delete, list
Extracted from filesystem.py to reduce file size
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any
from tools.utils import get_safe_path


class BasicFileOperations:
    """Basic file and folder operations with safety checks"""

    def __init__(self, workspace: Path, max_file_size: int):
        """
        Initialize basic file operations.

        Args:
            workspace: Workspace directory path
            max_file_size: Maximum allowed file size in bytes
        """
        self.workspace = workspace
        self.max_file_size = max_file_size

    def _get_safe_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path and validate it's within workspace"""
        return get_safe_path(self.workspace, relative_path)

    def create_folder(self, path: str) -> Dict[str, Any]:
        """
        Create a new folder.

        Args:
            path: Relative path to folder

        Returns:
            Dict with success status and message
        """
        try:
            full_path = self._get_safe_path(path)
            full_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created folder: {full_path}")
            return {
                "success": True,
                "message": f"Folder created: {path}",
                "path": str(full_path)
            }
        except Exception as e:
            logging.error(f"Error creating folder: {e}")
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file.

        Args:
            path: Relative path to file
            content: Content to write

        Returns:
            Dict with success status and message
        """
        try:
            full_path = self._get_safe_path(path)

            # Check file size
            content_size = len(content.encode('utf-8'))
            if content_size > self.max_file_size:
                return {
                    "success": False,
                    "error": f"File size ({content_size} bytes) exceeds maximum ({self.max_file_size} bytes)"
                }

            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            full_path.write_text(content, encoding='utf-8')
            logging.info(f"Wrote file: {full_path} ({content_size} bytes)")

            return {
                "success": True,
                "message": f"File written: {path} ({content_size} bytes)",
                "path": str(full_path),
                "size": content_size
            }
        except Exception as e:
            logging.error(f"Error writing file: {e}")
            return {"success": False, "error": str(e)}

    def read_file(self, path: str) -> Dict[str, Any]:
        """
        Read file contents.

        Args:
            path: Relative path to file

        Returns:
            Dict with success status and file content
        """
        try:
            full_path = self._get_safe_path(path)

            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }

            if not full_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {path}"
                }

            # Check file size before reading
            file_size = full_path.stat().st_size
            if file_size > self.max_file_size:
                return {
                    "success": False,
                    "error": f"File size ({file_size} bytes) exceeds maximum ({self.max_file_size} bytes)"
                }

            content = full_path.read_text(encoding='utf-8')
            logging.info(f"Read file: {full_path} ({file_size} bytes)")

            return {
                "success": True,
                "content": content,
                "path": str(full_path),
                "size": file_size
            }
        except Exception as e:
            logging.error(f"Error reading file: {e}")
            return {"success": False, "error": str(e)}

    def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """
        List contents of a directory.

        Args:
            path: Relative path to directory (default: workspace root)

        Returns:
            Dict with success status and directory contents
        """
        try:
            full_path = self._get_safe_path(path)

            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {path}"
                }

            if not full_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}"
                }

            # List contents
            contents = {"files": [], "folders": []}
            for item in sorted(full_path.iterdir()):
                if item.is_file():
                    contents["files"].append(item.name)
                elif item.is_dir():
                    contents["folders"].append(item.name)

            logging.info(f"Listed directory: {full_path} ({len(contents['files'])} files, {len(contents['folders'])} folders)")

            return {
                "success": True,
                "contents": contents,
                "path": str(full_path),
                "file_count": len(contents["files"]),
                "folder_count": len(contents["folders"])
            }
        except Exception as e:
            logging.error(f"Error listing directory: {e}")
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str) -> Dict[str, Any]:
        """
        Delete a file.

        Args:
            path: Relative path to file

        Returns:
            Dict with success status and message
        """
        try:
            full_path = self._get_safe_path(path)

            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }

            if full_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is a directory, not a file: {path}"
                }

            full_path.unlink()
            logging.info(f"Deleted file: {full_path}")

            return {
                "success": True,
                "message": f"File deleted: {path}",
                "path": str(full_path)
            }
        except Exception as e:
            logging.error(f"Error deleting file: {e}")
            return {"success": False, "error": str(e)}

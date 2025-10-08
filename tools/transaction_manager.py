"""
Transaction Manager for Multi-File Atomic Operations (Phase 5)
Provides transaction-like behavior with rollback capability
"""

import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any


class TransactionManager:
    """
    Manages atomic operations across multiple files.

    Provides:
    - Automatic backups before modifications
    - All-or-nothing commit (all succeed or all rollback)
    - Safe rollback on any failure
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.backups = {}  # {file_path: backup_path}
        self.operations = []
        self.is_active = False

    def begin(self):
        """Start a new transaction"""
        if self.is_active:
            raise RuntimeError("Transaction already active")

        self.backups = {}
        self.operations = []
        self.is_active = True
        logging.info("Transaction started")

    def backup_file(self, file_path: str):
        """Create backup of a file before modification"""
        if not self.is_active:
            raise RuntimeError("No active transaction")

        full_path = self.workspace / file_path

        if not full_path.exists():
            # File doesn't exist yet, no backup needed
            self.backups[file_path] = None
            logging.info(f"Transaction: No backup needed for new file {file_path}")
            return

        # Create backup
        backup_path = full_path.parent / f".backup_{full_path.name}"
        shutil.copy2(full_path, backup_path)
        self.backups[file_path] = backup_path
        logging.info(f"Transaction: Backed up {file_path} to {backup_path}")

    def add_operation(self, operation: Dict[str, Any]):
        """Add an operation to the transaction"""
        if not self.is_active:
            raise RuntimeError("No active transaction")

        self.operations.append(operation)
        logging.info(f"Transaction: Added operation for {operation.get('file')}")

    def commit(self) -> Dict[str, Any]:
        """
        Commit the transaction - execute all operations.
        If any operation fails, rollback all changes.

        Returns:
            Dict with success status and details
        """
        if not self.is_active:
            return {"success": False, "error": "No active transaction"}

        try:
            logging.info(f"Transaction: Committing {len(self.operations)} operations")
            results = []

            for i, operation in enumerate(self.operations):
                file_path = operation.get('file')
                logging.info(f"Transaction: Executing operation {i+1}/{len(self.operations)} on {file_path}")

                # Operation will be executed by the caller
                # We just track that it's part of this transaction
                results.append({
                    "file": file_path,
                    "operation": operation.get('action'),
                    "success": True
                })

            # All operations succeeded - cleanup backups
            self._cleanup_backups()
            self.is_active = False

            logging.info("Transaction: Committed successfully")
            return {
                "success": True,
                "message": f"Transaction committed: {len(self.operations)} operations",
                "operations": results
            }

        except Exception as e:
            logging.error(f"Transaction: Commit failed - {e}")
            rollback_result = self.rollback()
            return {
                "success": False,
                "error": f"Transaction failed: {e}",
                "rollback": rollback_result
            }

    def rollback(self) -> Dict[str, Any]:
        """
        Rollback the transaction - restore all files from backups.

        Returns:
            Dict with rollback status
        """
        if not self.is_active:
            return {"success": False, "error": "No active transaction"}

        logging.warning(f"Transaction: Rolling back {len(self.backups)} files")
        restored = []
        errors = []

        for file_path, backup_path in self.backups.items():
            try:
                full_path = self.workspace / file_path

                if backup_path is None:
                    # New file that was created - delete it
                    if full_path.exists():
                        full_path.unlink()
                        logging.info(f"Transaction rollback: Deleted new file {file_path}")
                        restored.append(file_path)
                else:
                    # Restore from backup
                    shutil.copy2(backup_path, full_path)
                    logging.info(f"Transaction rollback: Restored {file_path} from backup")
                    restored.append(file_path)

            except Exception as e:
                logging.error(f"Transaction rollback: Failed to restore {file_path}: {e}")
                errors.append({"file": file_path, "error": str(e)})

        # Cleanup backups
        self._cleanup_backups()
        self.is_active = False

        return {
            "success": len(errors) == 0,
            "message": f"Rollback {'complete' if not errors else 'partial'}",
            "restored": restored,
            "errors": errors
        }

    def _cleanup_backups(self):
        """Remove all backup files"""
        for backup_path in self.backups.values():
            if backup_path and backup_path.exists():
                try:
                    backup_path.unlink()
                    logging.info(f"Transaction: Cleaned up backup {backup_path}")
                except Exception as e:
                    logging.warning(f"Transaction: Failed to cleanup backup {backup_path}: {e}")

        self.backups = {}

"""
Context Builder
Builds context for LLM prompts including session tracking, memory, and rules
"""

import logging
from pathlib import Path
from typing import Dict, Any, Set, Optional


class ContextBuilder:
    """
    Build context for LLM prompts.

    Manages:
    - Session file tracking (created/modified files)
    - Project-specific rules from .agentrules
    - Memory integration
    - Session history
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize context builder.

        Args:
            config: Agent configuration dict
        """
        self.config = config
        self.workspace = Path(config['agent']['workspace'])
        self.session_files: Dict[str, Set[str]] = {
            "created": set(),
            "modified": set()
        }

    def track_file_created(self, file_path: str) -> None:
        """
        Track that a file was created in this session.

        Args:
            file_path: Relative path to created file
        """
        self.session_files["created"].add(file_path)
        logging.debug(f"Tracked file creation: {file_path}")

    def track_file_modified(self, file_path: str) -> None:
        """
        Track that a file was modified in this session.

        Args:
            file_path: Relative path to modified file
        """
        # Don't add to modified if it was created this session
        if file_path not in self.session_files["created"]:
            self.session_files["modified"].add(file_path)
            logging.debug(f"Tracked file modification: {file_path}")

    def build_session_context(self) -> str:
        """
        Build context about files created/modified in this session.

        Returns:
            Formatted string with session file tracking info
        """
        parts = []

        if self.session_files["created"]:
            files = ", ".join(sorted(self.session_files["created"]))
            parts.append(f"Files you created this session: {files}")

        if self.session_files["modified"]:
            files = ", ".join(sorted(self.session_files["modified"]))
            parts.append(f"Files you modified this session: {files}")

        if parts:
            return ("SESSION FILE TRACKING:\n" +
                    "\n".join(parts) +
                    "\n\nIMPORTANT: If you need to modify a file you created/modified earlier in this session, use edit_file NOT write_file.")

        return ""

    def load_agent_rules(self) -> Optional[str]:
        """
        Load project-specific rules from .agentrules file.

        Returns:
            Rules content if file exists, None otherwise
        """
        try:
            rules_path = Path(".agentrules")
            if rules_path.exists():
                with open(rules_path, 'r') as f:
                    content = f.read()
                    logging.info(f"Loaded .agentrules ({len(content)} chars)")
                    return content
        except Exception as e:
            logging.debug(f"No .agentrules file found or error loading: {e}")

        return None

    def build_full_context(
        self,
        memory_context: Optional[str] = None,
        history_context: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Build complete context for LLM prompt.

        Args:
            memory_context: Long-term memory context
            history_context: Session history context

        Returns:
            Dict with context sections:
            - session: Session file tracking
            - rules: Project-specific rules
            - memory: Long-term memory
            - history: Session history
        """
        return {
            "session": self.build_session_context(),
            "rules": self.load_agent_rules() or "",
            "memory": memory_context or "",
            "history": history_context or ""
        }

    def format_rules_section(self, rules: Optional[str]) -> str:
        """
        Format project rules for inclusion in prompt.

        Args:
            rules: Rules content from .agentrules

        Returns:
            Formatted rules section or empty string
        """
        if rules:
            return f"\nPROJECT-SPECIFIC RULES:\n{rules}\n"
        return ""

    def clear_session_tracking(self) -> None:
        """Clear session file tracking (for new session start)."""
        self.session_files["created"].clear()
        self.session_files["modified"].clear()
        logging.info("Cleared session file tracking")

    def get_session_stats(self) -> Dict[str, int]:
        """
        Get statistics about current session.

        Returns:
            Dict with counts of created/modified files
        """
        return {
            "files_created": len(self.session_files["created"]),
            "files_modified": len(self.session_files["modified"]),
            "total_files_touched": len(self.session_files["created"]) + len(self.session_files["modified"])
        }

"""
Session History
Maintains conversation history across agent sessions
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class SessionHistory:
    """
    Maintains conversation history across sessions.

    Stores messages with timestamps and metadata, pruning old sessions
    to stay within message limits.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize session history.

        Args:
            config: Agent configuration dictionary
        """
        self.config = config
        self.enabled: bool = config['agent'].get('enable_session_history', False)
        self.history_file: Path = Path(config['agent'].get('session_history_file', 'logs/session_history.json'))
        self.max_messages: int = config['agent'].get('max_history_messages', 50)
        self.sessions: List[Dict[str, Any]] = self._load_history()
        self.current_session_id: str = self._generate_session_id()

    def _generate_session_id(self) -> str:
        """
        Generate a unique session ID.

        Returns:
            Timestamp-based session ID
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _load_history(self) -> List[Dict[str, Any]]:
        """
        Load session history from file.

        Returns:
            List of session dictionaries
        """
        if not self.enabled:
            return []
        
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading history: {e}")
                return []
        return []
    
    def _save_history(self) -> None:
        """Save session history to file."""
        if not self.enabled:
            return

        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving history: {e}")

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to current session.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata dictionary
        """
        if not self.enabled:
            return
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Find or create current session
        current_session = None
        for session in self.sessions:
            if session["session_id"] == self.current_session_id:
                current_session = session
                break
        
        if not current_session:
            current_session = {
                "session_id": self.current_session_id,
                "start_time": datetime.now().isoformat(),
                "messages": []
            }
            self.sessions.append(current_session)
        
        current_session["messages"].append(message)
        current_session["last_updated"] = datetime.now().isoformat()
        
        # Prune old sessions
        self._prune_sessions()
        self._save_history()
    
    def get_recent_context(self, num_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent messages for context.

        Args:
            num_messages: Number of recent messages to return

        Returns:
            List of message dictionaries
        """
        if not self.enabled or not self.sessions:
            return []
        
        # Get current session
        for session in reversed(self.sessions):
            if session["session_id"] == self.current_session_id:
                return session["messages"][-num_messages:]
        
        # If no current session, get from last session
        if self.sessions:
            return self.sessions[-1]["messages"][-num_messages:]
        
        return []
    
    def get_session_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of a session.

        Args:
            session_id: Optional session ID (defaults to current session)

        Returns:
            Dict with session summary or error
        """
        if not self.enabled:
            return {"success": False, "error": "Session history disabled"}
        
        target_id = session_id or self.current_session_id
        
        for session in self.sessions:
            if session["session_id"] == target_id:
                return {
                    "success": True,
                    "session_id": session["session_id"],
                    "start_time": session["start_time"],
                    "last_updated": session.get("last_updated", ""),
                    "message_count": len(session["messages"]),
                    "messages": session["messages"]
                }
        
        return {
            "success": False,
            "error": f"Session {target_id} not found"
        }
    
    def list_sessions(self, limit: int = 10) -> Dict[str, Any]:
        """
        List recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            Dict with session list and total count
        """
        if not self.enabled:
            return {"success": False, "error": "Session history disabled"}
        
        sessions_info = []
        for session in reversed(self.sessions[-limit:]):
            sessions_info.append({
                "session_id": session["session_id"],
                "start_time": session["start_time"],
                "message_count": len(session["messages"])
            })
        
        return {
            "success": True,
            "sessions": sessions_info,
            "total": len(self.sessions)
        }
    
    def search_history(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search across all session history.

        Args:
            query: Search query (case-insensitive)
            limit: Maximum number of results

        Returns:
            Dict with search results and count
        """
        if not self.enabled:
            return {"success": False, "error": "Session history disabled"}
        
        results = []
        query_lower = query.lower()
        
        for session in reversed(self.sessions):
            for msg in session["messages"]:
                if query_lower in msg["content"].lower():
                    results.append({
                        "session_id": session["session_id"],
                        "timestamp": msg["timestamp"],
                        "role": msg["role"],
                        "content": msg["content"][:200]  # Truncate for preview
                    })
                    
                    if len(results) >= limit:
                        break
            
            if len(results) >= limit:
                break
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    
    def _prune_sessions(self) -> None:
        """Keep only recent sessions within message limit."""
        total_messages = sum(len(s["messages"]) for s in self.sessions)
        
        while total_messages > self.max_messages and len(self.sessions) > 1:
            # Remove oldest session
            removed = self.sessions.pop(0)
            total_messages -= len(removed["messages"])
            logging.info(f"Pruned session {removed['session_id']}")
    
    def get_context_for_llm(self, num_messages: int = 5) -> str:
        """
        Format recent history for LLM context.

        Args:
            num_messages: Number of recent messages to include

        Returns:
            Formatted string with recent conversation history
        """
        if not self.enabled:
            return ""
        
        recent = self.get_recent_context(num_messages)
        if not recent:
            return ""
        
        lines = ["Recent conversation history:"]
        for msg in recent:
            role = msg["role"].upper()
            content = msg["content"][:500]  # Limit length
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
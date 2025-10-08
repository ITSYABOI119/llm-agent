"""
Session History
Maintains conversation history across agent sessions
"""

import json
import logging
from datetime import datetime
from pathlib import Path


class SessionHistory:
    def __init__(self, config):
        self.config = config
        self.enabled = config['agent'].get('enable_session_history', False)
        self.history_file = Path(config['agent'].get('session_history_file', 'logs/session_history.json'))
        self.max_messages = config['agent'].get('max_history_messages', 50)
        self.sessions = self._load_history()
        self.current_session_id = self._generate_session_id()
    
    def _generate_session_id(self):
        """Generate a unique session ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _load_history(self):
        """Load session history from file"""
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
    
    def _save_history(self):
        """Save session history to file"""
        if not self.enabled:
            return
        
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving history: {e}")
    
    def add_message(self, role, content, metadata=None):
        """Add a message to current session"""
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
    
    def get_recent_context(self, num_messages=10):
        """Get recent messages for context"""
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
    
    def get_session_summary(self, session_id=None):
        """Get summary of a session"""
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
    
    def list_sessions(self, limit=10):
        """List recent sessions"""
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
    
    def search_history(self, query, limit=20):
        """Search across all session history"""
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
    
    def _prune_sessions(self):
        """Keep only recent sessions within message limit"""
        total_messages = sum(len(s["messages"]) for s in self.sessions)
        
        while total_messages > self.max_messages and len(self.sessions) > 1:
            # Remove oldest session
            removed = self.sessions.pop(0)
            total_messages -= len(removed["messages"])
            logging.info(f"Pruned session {removed['session_id']}")
    
    def get_context_for_llm(self, num_messages=5):
        """Format recent history for LLM context"""
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
"""
Memory System
Stores and retrieves important facts and context across sessions
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class MemorySystem:
    """
    Long-term memory system for storing facts across sessions.

    Persists key-value pairs organized by category with access tracking.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize memory system.

        Args:
            config: Agent configuration dictionary
        """
        self.config = config
        self.enabled: bool = config['agent'].get('enable_memory', False)
        self.memory_file: Path = Path(config['agent'].get('memory_file', 'logs/agent_memory.json'))
        self.max_entries: int = config['agent'].get('max_memory_entries', 1000)
        self.memory: Dict[str, Dict[str, Any]] = self._load_memory()

    def _load_memory(self) -> Dict[str, Dict[str, Any]]:
        """
        Load memory from file.

        Returns:
            Dict of categories with key-value pairs
        """
        if not self.enabled:
            return {}
        
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading memory: {e}")
                return {}
        return {}
    
    def _save_memory(self) -> None:
        """Save memory to file."""
        if not self.enabled:
            return

        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving memory: {e}")

    def store(self, key: str, value: Any, category: str = "general") -> Dict[str, Any]:
        """
        Store a fact in memory.

        Args:
            key: Memory key
            value: Value to store
            category: Category to organize memory (default: "general")

        Returns:
            Dict with success status and message
        """
        if not self.enabled:
            return {"success": False, "error": "Memory system disabled"}
        
        if category not in self.memory:
            self.memory[category] = {}
        
        self.memory[category][key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "access_count": 0
        }
        
        # Prune if too many entries
        self._prune_memory()
        self._save_memory()
        
        logging.info(f"Stored memory: {category}/{key}")
        return {
            "success": True,
            "message": f"Stored {key} in {category}"
        }
    
    def retrieve(self, key: str, category: str = "general") -> Dict[str, Any]:
        """
        Retrieve a fact from memory.

        Args:
            key: Memory key to retrieve
            category: Category to search in

        Returns:
            Dict with success status, key, value, and timestamp
        """
        if not self.enabled:
            return {"success": False, "error": "Memory system disabled"}
        
        if category in self.memory and key in self.memory[category]:
            entry = self.memory[category][key]
            entry["access_count"] += 1
            entry["last_accessed"] = datetime.now().isoformat()
            self._save_memory()
            
            logging.info(f"Retrieved memory: {category}/{key}")
            return {
                "success": True,
                "key": key,
                "value": entry["value"],
                "timestamp": entry["timestamp"]
            }
        
        return {
            "success": False,
            "error": f"No memory found for {category}/{key}"
        }
    
    def search(self, query: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Search memory for matching keys or values.

        Args:
            query: Search query (case-insensitive)
            category: Optional category to limit search

        Returns:
            Dict with success status, results list, and count
        """
        if not self.enabled:
            return {"success": False, "error": "Memory system disabled"}
        
        results = []
        query_lower = query.lower()
        
        categories = [category] if category else self.memory.keys()
        
        for cat in categories:
            if cat in self.memory:
                for key, entry in self.memory[cat].items():
                    # Search in both key and value, case-insensitive
                    key_lower = key.lower()
                    value_lower = str(entry["value"]).lower()
                    
                    if query_lower in key_lower or query_lower in value_lower:
                        results.append({
                            "category": cat,
                            "key": key,
                            "value": entry["value"],
                            "timestamp": entry["timestamp"]
                        })
        
        logging.info(f"Memory search for '{query}': {len(results)} results")
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    
    def list_all(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        List all memories, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            Dict with memories, total entries, and categories list
        """
        if not self.enabled:
            return {"success": False, "error": "Memory system disabled"}
        
        if category:
            memories = {category: self.memory.get(category, {})}
        else:
            memories = self.memory
        
        total = sum(len(entries) for entries in memories.values())
        
        return {
            "success": True,
            "memories": memories,
            "total_entries": total,
            "categories": list(memories.keys())
        }
    
    def delete(self, key: str, category: str = "general") -> Dict[str, Any]:
        """
        Delete a memory entry.

        Args:
            key: Memory key to delete
            category: Category containing the key

        Returns:
            Dict with success status and message
        """
        if not self.enabled:
            return {"success": False, "error": "Memory system disabled"}
        
        if category in self.memory and key in self.memory[category]:
            del self.memory[category][key]
            self._save_memory()
            logging.info(f"Deleted memory: {category}/{key}")
            return {
                "success": True,
                "message": f"Deleted {category}/{key}"
            }
        
        return {
            "success": False,
            "error": f"Memory {category}/{key} not found"
        }
    
    def _prune_memory(self) -> None:
        """Prune old or least-accessed memories if limit exceeded."""
        total = sum(len(entries) for entries in self.memory.values())
        
        if total > self.max_entries:
            # Flatten all entries with metadata
            all_entries = []
            for cat, entries in self.memory.items():
                for key, entry in entries.items():
                    all_entries.append({
                        "category": cat,
                        "key": key,
                        "access_count": entry.get("access_count", 0),
                        "timestamp": entry["timestamp"]
                    })
            
            # Sort by access count (ascending) then by timestamp (oldest first)
            all_entries.sort(key=lambda x: (x["access_count"], x["timestamp"]))
            
            # Remove oldest/least accessed entries
            to_remove = total - self.max_entries
            for entry in all_entries[:to_remove]:
                del self.memory[entry["category"]][entry["key"]]
            
            logging.info(f"Pruned {to_remove} memory entries")
    
    def get_context_summary(self) -> str:
        """
        Get a summary of stored memories for LLM context.

        Returns:
            Formatted string summary of memories (up to 10 per category)
        """
        if not self.enabled or not self.memory:
            return ""
        
        summary_lines = ["Stored memories:"]
        for category, entries in self.memory.items():
            if entries:
                summary_lines.append(f"\n{category.upper()}:")
                for key, entry in list(entries.items())[:10]:  # Limit to 10 per category
                    summary_lines.append(f"  - {key}: {entry['value']}")
        
        return "\n".join(summary_lines)
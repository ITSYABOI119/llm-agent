"""
Memory System
Stores and retrieves important facts and context across sessions
"""

import json
import logging
from datetime import datetime
from pathlib import Path


class MemorySystem:
    def __init__(self, config):
        self.config = config
        self.enabled = config['agent'].get('enable_memory', False)
        self.memory_file = Path(config['agent'].get('memory_file', 'logs/agent_memory.json'))
        self.max_entries = config['agent'].get('max_memory_entries', 1000)
        self.memory = self._load_memory()
    
    def _load_memory(self):
        """Load memory from file"""
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
    
    def _save_memory(self):
        """Save memory to file"""
        if not self.enabled:
            return
        
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving memory: {e}")
    
    def store(self, key, value, category="general"):
        """Store a fact in memory"""
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
    
    def retrieve(self, key, category="general"):
        """Retrieve a fact from memory"""
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
    
    def search(self, query, category=None):
        """Search memory for matching keys or values"""
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
    
    def list_all(self, category=None):
        """List all memories, optionally filtered by category"""
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
    
    def delete(self, key, category="general"):
        """Delete a memory entry"""
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
    
    def _prune_memory(self):
        """Prune old or least-accessed memories if limit exceeded"""
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
    
    def get_context_summary(self):
        """Get a summary of stored memories for LLM context"""
        if not self.enabled or not self.memory:
            return ""
        
        summary_lines = ["Stored memories:"]
        for category, entries in self.memory.items():
            if entries:
                summary_lines.append(f"\n{category.upper()}:")
                for key, entry in list(entries.items())[:10]:  # Limit to 10 per category
                    summary_lines.append(f"  - {key}: {entry['value']}")
        
        return "\n".join(summary_lines)
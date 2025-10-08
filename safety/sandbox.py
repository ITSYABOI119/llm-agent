"""
Sandbox
Provides sandboxing and security boundaries for agent operations
"""

import logging
from pathlib import Path


class Sandbox:
    def __init__(self, config):
        self.config = config
        self.workspace = Path(config['agent']['workspace'])
        self.allowed_paths = config['security']['allowed_paths']
    
    def is_path_allowed(self, path):
        """Check if a path is within allowed directories"""
        try:
            # Convert to absolute path
            full_path = (self.workspace / path).resolve()
            
            # Must be within workspace
            full_path.relative_to(self.workspace)
            
            # Check against allowed paths
            for allowed in self.allowed_paths:
                allowed_full = (self.workspace / allowed).resolve()
                try:
                    full_path.relative_to(allowed_full)
                    return True
                except ValueError:
                    continue
            
            return False
        
        except ValueError:
            # Path is outside workspace
            return False
        except Exception as e:
            logging.error(f"Error checking path: {e}")
            return False
    
    def sanitize_path(self, path):
        """Sanitize and validate a path"""
        # Remove dangerous patterns
        dangerous_patterns = ['..', '~', '$']
        for pattern in dangerous_patterns:
            if pattern in str(path):
                raise ValueError(f"Dangerous pattern '{pattern}' in path")
        
        return path
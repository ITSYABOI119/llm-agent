"""
Search Tools
File search and content grep functionality
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List
from tools.utils import get_safe_path
from tools.cache import Cache


class SearchTools:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.workspace: Path = Path(config['agent']['workspace'])
        self.max_results: int = 100
        self.max_file_size: int = config['security']['max_file_size']
        # Cache for file searches (60 second TTL)
        self._search_cache = Cache(ttl=60)

    def _get_safe_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path and validate it's within workspace"""
        return get_safe_path(self.workspace, relative_path)

    def find_files(self, pattern: str = "*", path: str = ".") -> Dict[str, Any]:
        """
        Find files matching a pattern.
        pattern: glob pattern like *.py, test_*, etc.
        path: directory to search in (relative to workspace)
        """
        # Check cache first
        cache_key = f"find_files:{pattern}:{path}"
        cached_result = self._search_cache.get(cache_key)
        if cached_result is not None:
            logging.debug(f"Cache hit for file search: {pattern} in {path}")
            return cached_result

        try:
            search_path = self._get_safe_path(path)
            
            if not search_path.exists():
                return {"success": False, "error": f"Path not found: {path}"}
            
            if not search_path.is_dir():
                return {"success": False, "error": f"Not a directory: {path}"}
            
            matches = []
            for file_path in search_path.rglob(pattern):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.workspace)
                    matches.append({
                        "path": str(rel_path),
                        "name": file_path.name,
                        "size": file_path.stat().st_size
                    })
                    
                    if len(matches) >= self.max_results:
                        break
            
            logging.info(f"Found {len(matches)} files matching '{pattern}' in {path}")

            result = {
                "success": True,
                "pattern": pattern,
                "search_path": str(search_path),
                "matches": matches,
                "count": len(matches),
                "truncated": len(matches) >= self.max_results
            }

            # Cache the result
            self._search_cache.set(cache_key, result)

            return result
        
        except Exception as e:
            logging.error(f"Error searching files: {e}")
            return {"success": False, "error": str(e)}
    
    def grep_content(self, pattern, path=".", file_pattern="*", case_sensitive=False):
        """
        Search for text pattern in files
        pattern: text or regex pattern to search for
        path: directory to search in
        file_pattern: which files to search (e.g., *.py)
        case_sensitive: whether search is case sensitive
        """
        try:
            search_path = self._get_safe_path(path)
            
            if not search_path.exists():
                return {"success": False, "error": f"Path not found: {path}"}
            
            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {"success": False, "error": f"Invalid regex pattern: {e}"}
            
            matches = []
            files_searched = 0
            
            for file_path in search_path.rglob(file_pattern):
                if not file_path.is_file():
                    continue
                
                # Skip large files
                if file_path.stat().st_size > self.max_file_size:
                    continue
                
                try:
                    # Try to read as text
                    content = file_path.read_text()
                    lines = content.split('\n')
                    
                    file_matches = []
                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            file_matches.append({
                                "line": line_num,
                                "content": line.strip()
                            })
                            
                            # Limit matches per file
                            if len(file_matches) >= 50:
                                break
                    
                    if file_matches:
                        rel_path = file_path.relative_to(self.workspace)
                        matches.append({
                            "file": str(rel_path),
                            "matches": file_matches,
                            "match_count": len(file_matches)
                        })
                    
                    files_searched += 1
                    
                except (UnicodeDecodeError, PermissionError):
                    # Skip binary files or files we can't read
                    continue
                
                # Limit total results
                if len(matches) >= self.max_results:
                    break
            
            logging.info(f"Grepped '{pattern}' in {files_searched} files, found {len(matches)} matches")
            
            return {
                "success": True,
                "pattern": pattern,
                "search_path": str(search_path),
                "file_pattern": file_pattern,
                "files_searched": files_searched,
                "files_with_matches": len(matches),
                "matches": matches,
                "truncated": len(matches) >= self.max_results
            }
        
        except Exception as e:
            logging.error(f"Error grepping content: {e}")
            return {"success": False, "error": str(e)}
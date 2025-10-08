"""
Data Processing Tools
Parse and transform JSON, CSV, and other data formats
"""

import json
import csv
import logging
from pathlib import Path
from io import StringIO
from typing import Dict, Any, Optional, List
from tools.utils import get_safe_path


class DataTools:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.workspace: Path = Path(config['agent']['workspace'])

    def _get_safe_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path and validate it's within workspace"""
        return get_safe_path(self.workspace, relative_path)

    def parse_json(self, file_path: Optional[str] = None, json_string: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse JSON from file or string.
        Either file_path or json_string must be provided.
        """
        try:
            if file_path:
                full_path = self._get_safe_path(file_path)
                if not full_path.exists():
                    return {"success": False, "error": f"File not found: {file_path}"}
                
                content = full_path.read_text()
                data = json.loads(content)
                source = f"file: {file_path}"
            
            elif json_string:
                data = json.loads(json_string)
                source = "string"
            
            else:
                return {"success": False, "error": "Either file_path or json_string must be provided"}
            
            logging.info(f"Parsed JSON from {source}")
            
            return {
                "success": True,
                "source": source,
                "data": data,
                "type": type(data).__name__
            }
        
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            logging.error(f"Error parsing JSON: {e}")
            return {"success": False, "error": str(e)}
    
    def write_json(self, file_path, data, pretty=True):
        """Write data as JSON to a file"""
        try:
            full_path = self._get_safe_path(file_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            indent = 2 if pretty else None
            json_content = json.dumps(data, indent=indent)
            
            full_path.write_text(json_content)
            
            logging.info(f"Wrote JSON to {file_path}")
            
            return {
                "success": True,
                "file": file_path,
                "size": len(json_content)
            }
        
        except Exception as e:
            logging.error(f"Error writing JSON: {e}")
            return {"success": False, "error": str(e)}
    
    def parse_csv(self, file_path, delimiter=',', has_header=True):
        """Parse CSV file"""
        try:
            full_path = self._get_safe_path(file_path)
            if not full_path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            content = full_path.read_text()
            
            if has_header:
                reader = csv.DictReader(StringIO(content), delimiter=delimiter)
                rows = list(reader)
                headers = reader.fieldnames
            else:
                reader = csv.reader(StringIO(content), delimiter=delimiter)
                rows = [list(row) for row in reader]
                headers = None
            
            logging.info(f"Parsed CSV from {file_path}: {len(rows)} rows")
            
            return {
                "success": True,
                "file": file_path,
                "row_count": len(rows),
                "headers": headers,
                "data": rows[:100]  # Limit to first 100 rows
            }
        
        except Exception as e:
            logging.error(f"Error parsing CSV: {e}")
            return {"success": False, "error": str(e)}
    
    def write_csv(self, file_path, data, headers=None):
        """
        Write data as CSV to a file
        data: list of dicts or list of lists
        """
        try:
            full_path = self._get_safe_path(file_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            output = StringIO()
            
            if isinstance(data[0], dict):
                # Data is list of dicts
                fieldnames = headers or list(data[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            else:
                # Data is list of lists
                writer = csv.writer(output)
                if headers:
                    writer.writerow(headers)
                writer.writerows(data)
            
            full_path.write_text(output.getvalue())
            
            logging.info(f"Wrote CSV to {file_path}: {len(data)} rows")
            
            return {
                "success": True,
                "file": file_path,
                "row_count": len(data)
            }
        
        except Exception as e:
            logging.error(f"Error writing CSV: {e}")
            return {"success": False, "error": str(e)}
    
    def transform_data(self, data, operation):
        """
        Apply transformations to data
        operations: 'keys', 'values', 'length', 'filter', etc.
        """
        try:
            if operation == "keys" and isinstance(data, dict):
                result = list(data.keys())
            
            elif operation == "values" and isinstance(data, dict):
                result = list(data.values())
            
            elif operation == "length":
                result = len(data)
            
            elif operation == "type":
                result = type(data).__name__
            
            elif operation == "sort" and isinstance(data, list):
                result = sorted(data)
            
            else:
                return {"success": False, "error": f"Unsupported operation: {operation}"}
            
            return {
                "success": True,
                "operation": operation,
                "result": result
            }
        
        except Exception as e:
            logging.error(f"Error transforming data: {e}")
            return {"success": False, "error": str(e)}
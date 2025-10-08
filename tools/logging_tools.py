"""
Logging Tools
Enhanced logging with structured logs, analysis, and metrics
"""

import json
import logging
import csv
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


class LogManager:
    """
    Enhanced log manager with structured logging and metrics
    """
    def __init__(self, config):
        self.config = config
        self.log_file = Path(config['logging']['log_file'])
        self.max_size = config['logging'].get('max_log_size', 10485760)
        self.backup_count = config['logging'].get('backup_count', 5)
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure log file exists
        if not self.log_file.exists():
            self.log_file.touch()
        
        # Metrics storage
        self.tool_metrics = defaultdict(lambda: {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_execution_time': 0.0,
            'last_call': None
        })
    
    def _check_size_and_rotate(self):
        """Check file size and rotate if needed"""
        if not self.log_file.exists():
            return
        
        if self.log_file.stat().st_size > self.max_size:
            self._rotate_numbered_backups()
    
    def _rotate_numbered_backups(self):
        """Rotate log files with numbered backups"""
        # Remove oldest backup if at limit
        oldest = self.log_file.parent / f"{self.log_file.name}.{self.backup_count}"
        if oldest.exists():
            oldest.unlink()
        
        # Rotate existing backups
        for i in range(self.backup_count - 1, 0, -1):
            src = self.log_file.parent / f"{self.log_file.name}.{i}"
            dst = self.log_file.parent / f"{self.log_file.name}.{i + 1}"
            if src.exists():
                src.rename(dst)
        
        # Move current log to .1
        backup = self.log_file.parent / f"{self.log_file.name}.1"
        if self.log_file.exists():
            shutil.copy2(self.log_file, backup)
            self.log_file.write_text('')
    
    def log_info(self, message):
        """Log info message"""
        self._check_size_and_rotate()
        logging.info(message)
    
    def log_warning(self, message):
        """Log warning message"""
        self._check_size_and_rotate()
        logging.warning(message)
    
    def log_error(self, message):
        """Log error message"""
        self._check_size_and_rotate()
        logging.error(message)
    
    def log_debug(self, message):
        """Log debug message"""
        self._check_size_and_rotate()
        logging.debug(message)
    
    def log_structured(self, level, message, context=None, metadata=None):
        """
        Log structured JSON entry
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        
        if context:
            entry['context'] = context
        
        if metadata:
            entry['metadata'] = metadata
        
        # Write to structured log file
        structured_log = self.log_file.parent / f"{self.log_file.stem}_structured.json"
        
        try:
            # Append to JSON lines file
            with open(structured_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logging.error(f"Failed to write structured log: {e}")
    
    def get_structured_logs(self, limit=100):
        """
        Read structured logs
        """
        structured_log = self.log_file.parent / f"{self.log_file.stem}_structured.json"
        
        if not structured_log.exists():
            return []
        
        logs = []
        try:
            with open(structured_log, 'r') as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
                        if len(logs) >= limit:
                            break
        except Exception as e:
            logging.error(f"Error reading structured logs: {e}")
        
        return logs[-limit:]
    
    def log_tool_start(self, tool_name, parameters):
        """Log tool execution start"""
        self.log_structured(
            'INFO',
            f'Tool started: {tool_name}',
            context={
                'tool': tool_name,
                'parameters': parameters,
                'status': 'started'
            }
        )
    
    def log_tool_success(self, tool_name, parameters, execution_time, result):
        """Log successful tool execution"""
        # Update metrics
        metrics = self.tool_metrics[tool_name]
        metrics['total_calls'] += 1
        metrics['successful_calls'] += 1
        metrics['total_execution_time'] += execution_time
        metrics['last_call'] = datetime.now().isoformat()
        
        self.log_structured(
            'INFO',
            f'Tool completed: {tool_name}',
            context={
                'tool': tool_name,
                'parameters': parameters,
                'status': 'success',
                'execution_time': execution_time,
                'result': result
            }
        )
    
    def log_tool_failure(self, tool_name, parameters, execution_time, error):
        """Log failed tool execution"""
        # Update metrics
        metrics = self.tool_metrics[tool_name]
        metrics['total_calls'] += 1
        metrics['failed_calls'] += 1
        metrics['total_execution_time'] += execution_time
        metrics['last_call'] = datetime.now().isoformat()
        
        self.log_structured(
            'ERROR',
            f'Tool failed: {tool_name}',
            context={
                'tool': tool_name,
                'parameters': parameters,
                'status': 'failed',
                'execution_time': execution_time,
                'error': str(error)
            }
        )
    
    def get_tool_metrics(self, tool_name):
        """Get metrics for a specific tool"""
        metrics = self.tool_metrics[tool_name]
        
        result = {
            'tool': tool_name,
            'total_calls': metrics['total_calls'],
            'successful_calls': metrics['successful_calls'],
            'failed_calls': metrics['failed_calls'],
            'success_rate': 0.0,
            'avg_execution_time': 0.0,
            'last_call': metrics['last_call']
        }
        
        if metrics['total_calls'] > 0:
            result['success_rate'] = metrics['successful_calls'] / metrics['total_calls']
            result['avg_execution_time'] = metrics['total_execution_time'] / metrics['total_calls']
        
        return result
    
    def export_logs(self, output_path, format='json', level=None):
        """Export logs to file"""
        try:
            logs = self.get_structured_logs(limit=10000)
            
            # Filter by level if specified
            if level:
                logs = [log for log in logs if log.get('level') == level]
            
            output_path = Path(output_path)
            
            if format == 'json':
                with open(output_path, 'w') as f:
                    json.dump(logs, f, indent=2)
            
            elif format == 'csv':
                if not logs:
                    return {"success": True, "message": "No logs to export"}
                
                # Get all unique keys
                keys = set()
                for log in logs:
                    keys.update(log.keys())
                
                with open(output_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=sorted(keys))
                    writer.writeheader()
                    for log in logs:
                        # Flatten nested dicts
                        flat_log = {}
                        for key, value in log.items():
                            if isinstance(value, dict):
                                flat_log[key] = json.dumps(value)
                            else:
                                flat_log[key] = value
                        writer.writerow(flat_log)
            
            return {
                "success": True,
                "output_path": str(output_path),
                "count": len(logs)
            }
        
        except Exception as e:
            logging.error(f"Error exporting logs: {e}")
            return {"success": False, "error": str(e)}
    
    def rotate_log(self):
        """Manually rotate log files"""
        try:
            if not self.log_file.exists():
                return {"success": True, "message": "No log file to rotate"}
            
            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.log_file.parent / f"{self.log_file.stem}_{timestamp}.log"
            
            shutil.copy2(self.log_file, backup_path)
            
            # Clear current log
            self.log_file.write_text('')
            
            return {
                "success": True,
                "backup_path": str(backup_path)
            }
        
        except Exception as e:
            logging.error(f"Error rotating log: {e}")
            return {"success": False, "error": str(e)}
    
    def get_log_files(self):
        """Get list of all log files"""
        try:
            log_dir = self.log_file.parent
            
            files = []
            # Get main log file
            if self.log_file.exists():
                files.append({
                    'path': str(self.log_file),
                    'size': self.log_file.stat().st_size,
                    'modified': datetime.fromtimestamp(self.log_file.stat().st_mtime).isoformat()
                })
            
            # Get numbered backups (.1, .2, etc.)
            for i in range(1, self.backup_count + 1):
                backup = self.log_file.parent / f"{self.log_file.name}.{i}"
                if backup.exists():
                    files.append({
                        'path': str(backup),
                        'size': backup.stat().st_size,
                        'modified': datetime.fromtimestamp(backup.stat().st_mtime).isoformat()
                    })
            
            # Get timestamped backups
            pattern = f"{self.log_file.stem}_*.log"
            for file_path in log_dir.glob(pattern):
                files.append({
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
            
            return files
        
        except Exception as e:
            logging.error(f"Error listing log files: {e}")
            return []
    
    def clean_old_logs(self, days=7):
        """Delete log files older than specified days"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            log_dir = self.log_file.parent
            pattern = f"{self.log_file.stem}_*.log"
            
            deleted = []
            for file_path in log_dir.glob(pattern):
                modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if modified_time < cutoff:
                    file_path.unlink()
                    deleted.append(str(file_path))
            
            return {
                "success": True,
                "deleted_count": len(deleted),
                "deleted_files": deleted
            }
        
        except Exception as e:
            logging.error(f"Error cleaning old logs: {e}")
            return {"success": False, "error": str(e)}
    
    def log_performance_metrics(self, stats):
        """Log performance metrics"""
        self.log_structured(
            'INFO',
            'Performance metrics',
            context={
                'type': 'performance',
                'stats': stats
            }
        )
    
    def get_performance_summary(self):
        """Get performance summary"""
        total_calls = sum(m['total_calls'] for m in self.tool_metrics.values())
        total_time = sum(m['total_execution_time'] for m in self.tool_metrics.values())
        
        return {
            'total_tool_calls': total_calls,
            'total_execution_time': total_time,
            'avg_execution_time': total_time / total_calls if total_calls > 0 else 0,
            'tools_used': len(self.tool_metrics)
        }
    
    def get_tool_usage_stats(self):
        """Get tool usage statistics"""
        stats = {}
        for tool_name, metrics in self.tool_metrics.items():
            stats[tool_name] = self.get_tool_metrics(tool_name)
        return stats


class LogAnalyzer:
    """
    Analyze and query log files
    """
    def __init__(self, config):
        self.config = config
        self.log_file = Path(config['logging']['log_file'])
    
    def _read_log_lines(self):
        """Read all log lines"""
        if not self.log_file.exists():
            return []
        
        try:
            with open(self.log_file, 'r') as f:
                return f.readlines()
        except Exception as e:
            logging.error(f"Error reading log file: {e}")
            return []
    
    def _parse_log_line(self, line):
        """Parse a log line into components"""
        # Format: 2025-09-30 23:08:11,559 - root - INFO - Message
        try:
            parts = line.split(' - ', 3)
            if len(parts) >= 4:
                return {
                    'timestamp': parts[0].strip(),
                    'logger': parts[1].strip(),
                    'level': parts[2].strip(),
                    'message': parts[3].strip()
                }
        except:
            pass
        return None
    
    def count_by_level(self):
        """Count log entries by level"""
        counts = defaultdict(int)
        lines = self._read_log_lines()
        
        if not lines:
            return {}
        
        for line in lines:
            parsed = self._parse_log_line(line)
            if parsed:
                counts[parsed['level']] += 1
        
        return dict(counts)
    
    def get_errors(self, limit=100):
        """Get error log entries"""
        errors = []
        lines = self._read_log_lines()
        
        for line in lines:
            parsed = self._parse_log_line(line)
            if parsed and parsed['level'] == 'ERROR':
                errors.append(parsed)
                if len(errors) >= limit:
                    break
        
        return errors[-limit:] if errors else []
    
    def get_warnings(self, limit=100):
        """Get warning log entries"""
        warnings = []
        lines = self._read_log_lines()
        
        for line in lines:
            parsed = self._parse_log_line(line)
            if parsed and parsed['level'] == 'WARNING':
                warnings.append(parsed)
                if len(warnings) >= limit:
                    break
        
        return warnings[-limit:] if warnings else []
    
    def get_recent_logs(self, minutes=60):
        """Get logs from last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent = []
        lines = self._read_log_lines()
        
        for line in lines:
            parsed = self._parse_log_line(line)
            if parsed:
                try:
                    # Parse timestamp
                    ts = datetime.strptime(parsed['timestamp'], '%Y-%m-%d %H:%M:%S,%f')
                    if ts >= cutoff:
                        recent.append(parsed)
                except:
                    pass
        
        return recent
    
    def search_logs(self, query):
        """Search logs for a query string"""
        results = []
        query_lower = query.lower()
        lines = self._read_log_lines()
        
        for line in lines:
            if query_lower in line.lower():
                parsed = self._parse_log_line(line)
                if parsed:
                    results.append(parsed)
        
        return results
    
    def get_statistics(self):
        """Get comprehensive log statistics"""
        lines = self._read_log_lines()
        counts = self.count_by_level()
        
        timestamps = []
        for line in lines:
            parsed = self._parse_log_line(line)
            if parsed:
                try:
                    ts = datetime.strptime(parsed['timestamp'], '%Y-%m-%d %H:%M:%S,%f')
                    timestamps.append(ts)
                except:
                    pass
        
        time_range = {}
        if timestamps:
            time_range = {
                'first': min(timestamps).isoformat(),
                'last': max(timestamps).isoformat(),
                'span_hours': (max(timestamps) - min(timestamps)).total_seconds() / 3600
            }
        
        return {
            'total_entries': len(lines),
            'by_level': counts,
            'time_range': time_range
        }


class LogQuery:
    """
    Advanced querying of structured logs
    """
    def __init__(self, config):
        self.config = config
        self.log_file = Path(config['logging']['log_file'])
        self.structured_log = self.log_file.parent / f"{self.log_file.stem}_structured.json"
    
    def _read_structured_logs(self):
        """Read all structured logs"""
        if not self.structured_log.exists():
            return []
        
        logs = []
        try:
            with open(self.structured_log, 'r') as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
        except Exception as e:
            logging.error(f"Error reading structured logs: {e}")
        
        return logs
    
    def query_by_tool(self, tool_name):
        """Query logs for specific tool"""
        results = []
        
        for log in self._read_structured_logs():
            context = log.get('context', {})
            if context.get('tool') == tool_name:
                results.append(log)
        
        return results
    
    def query_by_time_range(self, start, end):
        """Query logs within time range"""
        results = []
        
        for log in self._read_structured_logs():
            try:
                ts = datetime.fromisoformat(log['timestamp'])
                if start <= ts <= end:
                    results.append(log)
            except:
                pass
        
        return results
    
    def query_by_success(self, success=True):
        """Query logs by success status"""
        results = []
        target_status = 'success' if success else 'failed'
        
        for log in self._read_structured_logs():
            context = log.get('context', {})
            if context.get('status') == target_status:
                results.append(log)
        
        return results
    
    def query_slow_operations(self, threshold=1.0):
        """Query operations slower than threshold"""
        results = []
        
        for log in self._read_structured_logs():
            context = log.get('context', {})
            exec_time = context.get('execution_time', 0)
            if exec_time > threshold:
                results.append(log)
        
        return results
    
    def query_failures(self):
        """Query all failures"""
        return self.query_by_success(success=False)
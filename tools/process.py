"""
Process Management Tools
List and manage system processes
"""

import subprocess
import logging
import signal
import psutil
from typing import Dict, Any, List, Optional


class ProcessTools:
    """
    Manage system processes using psutil.

    Provides tools to list, monitor, and query process information.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize process tools.

        Args:
            config: Agent configuration dictionary
        """
        self.config = config

    def list_processes(self, filter_name: Optional[str] = None) -> Dict[str, Any]:
        """
        List running processes.

        Args:
            filter_name: Optional filter by process name (case-insensitive)

        Returns:
            Dict with success status, count, and list of processes
        """
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info
                    
                    # Filter by name if provided
                    if filter_name and filter_name.lower() not in pinfo['name'].lower():
                        continue
                    
                    processes.append({
                        "pid": pinfo['pid'],
                        "name": pinfo['name'],
                        "user": pinfo['username'],
                        "cpu_percent": round(pinfo['cpu_percent'], 2),
                        "memory_percent": round(pinfo['memory_percent'], 2)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            logging.info(f"Listed {len(processes)} processes")
            
            return {
                "success": True,
                "count": len(processes),
                "processes": processes[:50]  # Limit to top 50
            }
        
        except Exception as e:
            logging.error(f"Error listing processes: {e}")
            return {"success": False, "error": str(e)}
    
    def get_process_info(self, pid: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific process.

        Args:
            pid: Process ID to query

        Returns:
            Dict with process information or error
        """
        try:
            pid = int(pid)
            proc = psutil.Process(pid)
            
            info = {
                "success": True,
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "username": proc.username(),
                "create_time": proc.create_time(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_percent": round(proc.memory_percent(), 2),
                "num_threads": proc.num_threads(),
                "cmdline": " ".join(proc.cmdline())
            }
            
            logging.info(f"Retrieved info for process {pid}")
            return info
        
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process {pid} not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": f"Access denied to process {pid}"}
        except Exception as e:
            logging.error(f"Error getting process info: {e}")
            return {"success": False, "error": str(e)}
    
    def check_process_running(self, name: str) -> Dict[str, Any]:
        """
        Check if a process with given name is running.

        Args:
            name: Process name to search for (case-insensitive)

        Returns:
            Dict with running status, count, and list of matching instances
        """
        try:
            running = []
            for proc in psutil.process_iter(['pid', 'name']):
                if name.lower() in proc.info['name'].lower():
                    running.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name']
                    })
            
            return {
                "success": True,
                "process_name": name,
                "running": len(running) > 0,
                "count": len(running),
                "instances": running
            }
        
        except Exception as e:
            logging.error(f"Error checking process: {e}")
            return {"success": False, "error": str(e)}
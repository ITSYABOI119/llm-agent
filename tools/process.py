"""
Process Management Tools
List and manage system processes
"""

import subprocess
import logging
import signal
import psutil


class ProcessTools:
    def __init__(self, config):
        self.config = config
    
    def list_processes(self, filter_name=None):
        """
        List running processes
        filter_name: optional filter by process name
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
    
    def get_process_info(self, pid):
        """Get detailed information about a specific process"""
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
    
    def check_process_running(self, name):
        """Check if a process with given name is running"""
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
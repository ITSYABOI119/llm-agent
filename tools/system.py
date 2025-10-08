"""
System Information Tools
Provides system status and information
"""

import os
import logging
import subprocess
import platform


class SystemTools:
    def __init__(self, config):
        self.config = config
    
    def get_system_info(self):
        """Get comprehensive system information"""
        try:
            info = {
                "success": True,
                "hostname": platform.node(),
                "platform": platform.system(),
                "platform_release": platform.release(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            }
            
            # Get CPU info
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read()
                    # Count processor entries
                    cpu_count = cpuinfo.count('processor')
                    info['cpu_count'] = cpu_count
            except:
                info['cpu_count'] = os.cpu_count()
            
            # Get memory info
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if 'MemTotal' in line:
                            total = int(line.split()[1]) * 1024  # Convert KB to bytes
                            info['memory_total'] = total
                            info['memory_total_mb'] = round(total / (1024**2), 2)
                        elif 'MemAvailable' in line:
                            available = int(line.split()[1]) * 1024
                            info['memory_available'] = available
                            info['memory_available_mb'] = round(available / (1024**2), 2)
            except:
                pass
            
            # Get disk usage
            try:
                result = subprocess.run(
                    ['df', '-h', '/'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        parts = lines[1].split()
                        info['disk_total'] = parts[1]
                        info['disk_used'] = parts[2]
                        info['disk_available'] = parts[3]
                        info['disk_usage_percent'] = parts[4]
            except:
                pass
            
            # Get uptime
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
                    info['uptime_seconds'] = int(uptime_seconds)
                    # Convert to human readable
                    days = int(uptime_seconds // 86400)
                    hours = int((uptime_seconds % 86400) // 3600)
                    minutes = int((uptime_seconds % 3600) // 60)
                    info['uptime'] = f"{days}d {hours}h {minutes}m"
            except:
                pass
            
            # Get load average
            try:
                load1, load5, load15 = os.getloadavg()
                info['load_average'] = {
                    "1min": round(load1, 2),
                    "5min": round(load5, 2),
                    "15min": round(load15, 2)
                }
            except:
                pass
            
            logging.info("Retrieved system information")
            return info
        
        except Exception as e:
            logging.error(f"Error getting system info: {e}")
            return {"success": False, "error": str(e)}
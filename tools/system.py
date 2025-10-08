"""
System Information Tools
Provides system status and information using psutil for cross-platform support
"""

import logging
import platform
import time
from tools.utils import format_bytes

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - system info will be limited")


class SystemTools:
    def __init__(self, config):
        self.config = config

    def get_system_info(self):
        """Get comprehensive system information (cross-platform with psutil)"""
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

            if not PSUTIL_AVAILABLE:
                info['warning'] = "psutil not installed - limited system info"
                return info

            # CPU info (cross-platform)
            info['cpu_count'] = psutil.cpu_count(logical=True)
            info['cpu_count_physical'] = psutil.cpu_count(logical=False)
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                info['cpu_percent'] = round(cpu_percent, 2)
            except Exception:
                pass

            # Memory info (cross-platform)
            try:
                mem = psutil.virtual_memory()
                info['memory_total'] = mem.total
                info['memory_total_mb'] = round(mem.total / (1024**2), 2)
                info['memory_available'] = mem.available
                info['memory_available_mb'] = round(mem.available / (1024**2), 2)
                info['memory_percent'] = round(mem.percent, 2)
                info['memory_used'] = mem.used
                info['memory_used_mb'] = round(mem.used / (1024**2), 2)
            except Exception as e:
                logging.debug(f"Error getting memory info: {e}")

            # Disk usage (cross-platform)
            try:
                # Get root disk usage (/ on Unix, C:\ on Windows)
                if platform.system() == 'Windows':
                    disk_path = 'C:\\'
                else:
                    disk_path = '/'

                disk = psutil.disk_usage(disk_path)
                info['disk_total'] = format_bytes(disk.total)
                info['disk_used'] = format_bytes(disk.used)
                info['disk_available'] = format_bytes(disk.free)
                info['disk_usage_percent'] = f"{disk.percent}%"
                info['disk_total_bytes'] = disk.total
                info['disk_used_bytes'] = disk.used
                info['disk_free_bytes'] = disk.free
            except Exception as e:
                logging.debug(f"Error getting disk info: {e}")

            # Uptime (cross-platform)
            try:
                boot_time = psutil.boot_time()
                uptime_seconds = int(time.time() - boot_time)
                info['uptime_seconds'] = uptime_seconds
                # Convert to human readable
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                info['uptime'] = f"{days}d {hours}h {minutes}m"
            except Exception as e:
                logging.debug(f"Error getting uptime: {e}")

            # Load average (Unix-like systems only)
            try:
                if hasattr(psutil, 'getloadavg'):
                    load1, load5, load15 = psutil.getloadavg()
                    info['load_average'] = {
                        "1min": round(load1, 2),
                        "5min": round(load5, 2),
                        "15min": round(load15, 2)
                    }
            except (OSError, AttributeError) as e:
                logging.debug(f"Load average not available: {e}")

            logging.info("Retrieved system information")
            return info

        except Exception as e:
            logging.error(f"Error getting system info: {e}")
            return {"success": False, "error": str(e)}
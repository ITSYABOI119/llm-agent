"""
Resource Monitor
Monitors and enforces resource usage limits to prevent system abuse
"""

from typing import Dict, Optional
import logging

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - resource monitoring disabled")


class ResourceMonitor:
    """Monitor and enforce resource usage limits"""

    def __init__(self, config: Dict):
        self.config = config
        quotas = config.get('security', {}).get('resource_quotas', {})

        self.max_cpu_percent = quotas.get('max_cpu_percent', 90)
        self.max_memory_mb = quotas.get('max_memory_mb', 2048)
        self.max_disk_mb = quotas.get('max_disk_mb', 10240)  # 10GB
        self.enabled = PSUTIL_AVAILABLE

    def check_resources(self) -> Optional[str]:
        """
        Check if current resource usage is within quotas.

        Returns:
            Error message if quota exceeded, None otherwise
        """
        if not self.enabled:
            return None

        # Check CPU usage
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > self.max_cpu_percent:
                return f"CPU usage too high: {cpu_percent:.1f}% (max {self.max_cpu_percent}%)"
        except Exception as e:
            logging.debug(f"Error checking CPU: {e}")

        # Check memory usage
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            if memory_mb > self.max_memory_mb:
                return f"Memory usage too high: {memory_mb:.1f}MB (max {self.max_memory_mb}MB)"
        except Exception as e:
            logging.debug(f"Error checking memory: {e}")

        # Check available disk space
        try:
            import platform
            if platform.system() == 'Windows':
                disk_path = 'C:\\\\'
            else:
                disk_path = '/'

            disk = psutil.disk_usage(disk_path)
            free_mb = disk.free / (1024 * 1024)
            if free_mb < self.max_disk_mb:
                return f"Low disk space: {free_mb:.1f}MB free (min {self.max_disk_mb}MB required)"
        except Exception as e:
            logging.debug(f"Error checking disk: {e}")

        return None

    def get_stats(self) -> Dict[str, float]:
        """Get current resource usage statistics"""
        if not self.enabled:
            return {"error": "psutil not available"}

        stats = {}

        try:
            stats['cpu_percent'] = psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logging.debug(f"Error getting CPU stats: {e}")

        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            stats['memory_mb'] = round(memory_mb, 2)
        except Exception as e:
            logging.debug(f"Error getting memory stats: {e}")

        try:
            import platform
            if platform.system() == 'Windows':
                disk_path = 'C:\\\\'
            else:
                disk_path = '/'

            disk = psutil.disk_usage(disk_path)
            stats['disk_free_mb'] = round(disk.free / (1024 * 1024), 2)
            stats['disk_percent_used'] = disk.percent
        except Exception as e:
            logging.debug(f"Error getting disk stats: {e}")

        return stats

"""
Network Operations Tools
Network connectivity and request functionality
"""

import subprocess
import logging
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socket
import platform
from typing import Dict, Any, Optional
from tools.exceptions import NetworkError


class NetworkTools:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Get network settings from config (with defaults)
        network_config = config.get('performance', {}).get('network', {})
        self.timeout: int = network_config.get('timeout', 10)
        max_retries: int = network_config.get('max_retries', 3)
        backoff_factor: float = network_config.get('backoff_factor', 0.3)
        pool_connections: int = network_config.get('pool_connections', 10)
        pool_maxsize: int = network_config.get('pool_maxsize', 10)

        # Create session with connection pooling and retry logic
        self._session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # Only retry safe methods
        )

        # Configure connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize
        )

        # Mount adapter for both HTTP and HTTPS
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def ping(self, host: str, count: int = 4) -> Dict[str, Any]:
        """
        Ping a host to check connectivity (cross-platform).

        Args:
            host: Hostname or IP address to ping
            count: Number of ping packets to send

        Returns:
            Dict with success status, output, and reachability
        """
        try:
            # Platform-specific ping flags
            system = platform.system().lower()
            if system == 'windows':
                cmd = ['ping', '-n', str(count), host]
            else:  # Linux, macOS, BSD
                cmd = ['ping', '-c', str(count), host]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=count * 2 + 5  # Dynamic timeout based on count
            )
            
            # Parse output for basic stats
            output = result.stdout
            success = result.returncode == 0
            
            logging.info(f"Pinged {host}: {'success' if success else 'failed'}")
            
            return {
                "success": success,
                "host": host,
                "packets_sent": count,
                "output": output,
                "reachable": success
            }
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Ping timeout"}
        except Exception as e:
            logging.error(f"Error pinging host: {e}")
            return {"success": False, "error": str(e)}
    
    def check_port(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """Check if a port is open on a host"""
        try:
            port = int(port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((host, port))
            sock.close()
            
            is_open = result == 0
            
            logging.info(f"Port check {host}:{port} - {'open' if is_open else 'closed'}")
            
            return {
                "success": True,
                "host": host,
                "port": port,
                "open": is_open,
                "status": "open" if is_open else "closed"
            }
        
        except Exception as e:
            logging.error(f"Error checking port: {e}")
            return {"success": False, "error": str(e)}
    
    def http_request(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, data: Optional[Any] = None) -> Dict[str, Any]:
        """Make an HTTP request"""
        try:
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                return {"success": False, "error": "URL must start with http:// or https://"}
            
            method = method.upper()
            if method not in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD']:
                return {"success": False, "error": f"Unsupported method: {method}"}
            
            logging.info(f"Making {method} request to {url}")

            # Use session for connection pooling
            response = self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                timeout=self.timeout
            )
            
            # Try to parse as JSON, fall back to text
            try:
                content = response.json()
                content_type = "json"
            except (ValueError, json.JSONDecodeError):
                content = response.text[:5000]  # Limit response size
                content_type = "text"
            
            return {
                "success": True,
                "url": url,
                "method": method,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": content_type,
                "content": content
            }
        
        except requests.Timeout:
            return {"success": False, "error": "Request timeout"}
        except requests.ConnectionError:
            return {"success": False, "error": "Connection error"}
        except Exception as e:
            logging.error(f"Error making HTTP request: {e}")
            return {"success": False, "error": str(e)}
    
    def get_ip_info(self) -> Dict[str, Any]:
        """
        Get network interface information (cross-platform).

        Returns:
            Dict with success status and interface information
        """
        try:
            import psutil
        except ImportError:
            return {
                "success": False,
                "error": "psutil not installed - run: pip install psutil"
            }

        try:
            interfaces = {}

            # Get all network interfaces
            for iface_name, iface_addrs in psutil.net_if_addrs().items():
                addresses = []

                for addr in iface_addrs:
                    addr_info = {
                        "family": str(addr.family),
                        "address": addr.address,
                    }

                    if addr.netmask:
                        addr_info["netmask"] = addr.netmask
                    if addr.broadcast:
                        addr_info["broadcast"] = addr.broadcast

                    addresses.append(addr_info)

                # Get interface stats
                stats = psutil.net_if_stats().get(iface_name)
                interfaces[iface_name] = {
                    "addresses": addresses,
                    "is_up": stats.isup if stats else False,
                    "speed": stats.speed if stats else 0,
                    "mtu": stats.mtu if stats else 0
                }

            logging.info(f"Retrieved info for {len(interfaces)} network interfaces")

            return {
                "success": True,
                "interfaces": interfaces,
                "count": len(interfaces)
            }

        except Exception as e:
            logging.error(f"Error getting IP info: {e}")
            return {"success": False, "error": str(e)}

    def close(self) -> None:
        """Close the HTTP session and release connections"""
        if hasattr(self, '_session'):
            self._session.close()
            logging.debug("Closed HTTP session and released connections")
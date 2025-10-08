"""
Network Operations Tools
Network connectivity and request functionality
"""

import subprocess
import logging
import requests
import socket


class NetworkTools:
    def __init__(self, config):
        self.config = config
        self.timeout = 10
    
    def ping(self, host, count=4):
        """Ping a host to check connectivity"""
        try:
            result = subprocess.run(
                ['ping', '-c', str(count), host],
                capture_output=True,
                text=True,
                timeout=self.timeout
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
    
    def check_port(self, host, port, timeout=5):
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
    
    def http_request(self, url, method="GET", headers=None, data=None):
        """Make an HTTP request"""
        try:
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                return {"success": False, "error": "URL must start with http:// or https://"}
            
            method = method.upper()
            if method not in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD']:
                return {"success": False, "error": f"Unsupported method: {method}"}
            
            logging.info(f"Making {method} request to {url}")
            
            response = requests.request(
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
    
    def get_ip_info(self):
        """Get network interface information"""
        try:
            result = subprocess.run(
                ['ip', 'addr'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return {"success": False, "error": "Failed to get IP info"}
            
            # Parse the output
            interfaces = []
            current_interface = None
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and line[0].isdigit():
                    # New interface
                    parts = line.split(':')
                    if len(parts) >= 2:
                        current_interface = {
                            "name": parts[1].strip(),
                            "addresses": []
                        }
                        interfaces.append(current_interface)
                elif 'inet ' in line and current_interface:
                    # IP address
                    parts = line.split()
                    if len(parts) >= 2:
                        current_interface["addresses"].append(parts[1])
            
            return {
                "success": True,
                "interfaces": interfaces
            }
        
        except Exception as e:
            logging.error(f"Error getting IP info: {e}")
            return {"success": False, "error": str(e)}
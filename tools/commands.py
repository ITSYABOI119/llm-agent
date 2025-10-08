"""
Command Execution Tools
Handles shell command execution with security checks
"""

import subprocess
import logging
import shlex
from typing import Dict, Any, Set
from tools.exceptions import CommandExecutionError, SecurityError


class CommandTools:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.allowed_commands: Set[str] = set(config['security']['allowed_commands'])
        self.allow_execution: bool = config['security']['allow_command_execution']

    def _is_command_allowed(self, command: str) -> bool:
        """Check if a command is in the whitelist"""
        # Parse the command to get the base command
        try:
            parts = shlex.split(command)
            if not parts:
                return False
            base_command = parts[0]
            return base_command in self.allowed_commands
        except ValueError:
            return False

    def run_command(self, command: str) -> Dict[str, Any]:
        """Execute a shell command with safety checks"""
        if not self.allow_execution:
            return {
                "success": False,
                "error": "Command execution is disabled in configuration"
            }
        
        if not command or not command.strip():
            return {"success": False, "error": "Empty command"}
        
        command = command.strip()
        
        # Check if command is allowed
        if not self._is_command_allowed(command):
            logging.warning(f"Blocked disallowed command: {command}")
            return {
                "success": False,
                "error": f"Command not in whitelist. Allowed commands: {', '.join(sorted(self.allowed_commands))}"
            }
        
        try:
            logging.info(f"Executing command: {command}")

            # Execute command with timeout (shell=False for security)
            # Split command into list for safe execution
            import shlex
            cmd_parts = shlex.split(command)

            result = subprocess.run(
                cmd_parts,
                shell=False,  # Security: Prevent shell injection
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=self.config['agent']['workspace']
            )
            
            logging.info(f"Command exit code: {result.returncode}")
            
            return {
                "success": result.returncode == 0,
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        
        except subprocess.TimeoutExpired:
            logging.error(f"Command timeout: {command}")
            return {
                "success": False,
                "error": "Command execution timed out (30s limit)"
            }
        except Exception as e:
            logging.error(f"Error executing command: {e}")
            return {"success": False, "error": str(e)}
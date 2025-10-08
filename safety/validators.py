"""
Validators
Input validation and sanitization using custom exceptions
"""

import re
import logging
from typing import Dict, Any
from tools.exceptions import ValidationError, SecurityError


class Validator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def validate_filename(self, filename: str) -> bool:
        """
        Validate a filename for safety.

        Args:
            filename: Filename to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If filename is invalid
            SecurityError: If filename contains dangerous patterns
        """
        # Check for null bytes
        if '\0' in filename:
            raise SecurityError("Null bytes not allowed in filename")

        # Check for dangerous patterns
        dangerous_patterns = ['..', '~', '$', '`', '|', ';', '&']
        for pattern in dangerous_patterns:
            if pattern in filename:
                raise SecurityError(f"Dangerous pattern '{pattern}' in filename")

        # Check length
        if len(filename) > 255:
            raise ValidationError("Filename too long (max 255 characters)")

        return True

    def validate_command(self, command: str) -> bool:
        """
        Validate a command for safety.

        Args:
            command: Shell command to validate

        Returns:
            True if valid

        Raises:
            SecurityError: If command contains dangerous patterns
        """
        # Check for dangerous patterns
        dangerous_patterns = [
            # Linux destructive commands
            'rm -rf /', 'rm -rf ~', 'rm -rf *',
            ':(){ :|:& };:',  # Fork bomb
            'mkfs', 'dd if=', 'dd of=',
            'chmod 777', 'chown', 'killall',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'init 0', 'init 6',
            # Windows destructive commands
            'del /f /s /q', 'format', 'diskpart',
            'rd /s /q', 'rmdir /s /q',
            # Network/download (can fetch malicious scripts)
            'wget', 'curl -o', 'curl -O',
            'invoke-webrequest',
            # Privilege escalation
            'sudo', 'su -', 'runas',
            # System modification
            'crontab', 'systemctl', 'service',
        ]
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                raise SecurityError(f"Dangerous command pattern detected: {pattern}")

        # Check for command chaining that could bypass whitelist
        chain_chars = ['&&', '||', ';', '|']
        for char in chain_chars:
            if char in command:
                raise SecurityError(f"Command chaining not allowed: '{char}'")

        # Check for redirects (can overwrite files)
        redirect_chars = ['>', '<', '>>']
        for char in redirect_chars:
            if char in command:
                raise SecurityError(f"Output redirection not allowed: '{char}'")

        return True
    
    def sanitize_string(self, text, max_length=10000):
        """Sanitize a string input"""
        if not text:
            return ""
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remove null bytes
        text = text.replace('\0', '')
        
        return text
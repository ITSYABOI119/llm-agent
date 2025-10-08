"""
Validators
Input validation and sanitization
"""

import re
import logging


class Validator:
    def __init__(self, config):
        self.config = config
    
    def validate_filename(self, filename):
        """Validate a filename for safety"""
        # Check for null bytes
        if '\0' in filename:
            raise ValueError("Null bytes not allowed in filename")
        
        # Check for dangerous patterns
        dangerous_patterns = ['..', '~', '$', '`', '|', ';', '&']
        for pattern in dangerous_patterns:
            if pattern in filename:
                raise ValueError(f"Dangerous pattern '{pattern}' in filename")
        
        # Check length
        if len(filename) > 255:
            raise ValueError("Filename too long (max 255 characters)")
        
        return True
    
    def validate_command(self, command):
        """Validate a command for safety"""
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
                raise ValueError(f"Dangerous command pattern detected")

        # Check for command chaining that could bypass whitelist
        chain_chars = ['&&', '||', ';', '|']
        for char in chain_chars:
            if char in command:
                raise ValueError(f"Command chaining not allowed: '{char}'")

        # Check for redirects (can overwrite files)
        redirect_chars = ['>', '<', '>>']
        for char in redirect_chars:
            if char in command:
                raise ValueError(f"Output redirection not allowed: '{char}'")

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
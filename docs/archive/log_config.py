"""
Logging Configuration for LLM Agent
Reduces terminal spam, outputs detailed logs to files
"""

import logging
import sys
from pathlib import Path


def setup_logging(
    console_level: str = "WARNING",
    file_level: str = "INFO",
    log_dir: str = "logs",
    log_file: str = "agent.log"
):
    """
    Configure logging with dual output:
    - Console: Only warnings and errors (reduces spam)
    - File: Detailed info logs (for debugging)

    Args:
        console_level: Log level for terminal output (WARNING, ERROR, INFO, DEBUG)
        file_level: Log level for file output (INFO, DEBUG)
        log_dir: Directory for log files
        log_file: Name of log file
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Capture everything

    # Clear existing handlers
    logger.handlers = []

    # Console handler (minimal output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_format = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (detailed output)
    file_handler = logging.FileHandler(
        log_path / log_file,
        mode='a',
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, file_level.upper()))
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger


def setup_test_logging(verbose: bool = False):
    """
    Configure logging for test suites

    Args:
        verbose: If True, show INFO logs in console. If False, only warnings/errors.
    """
    console_level = "INFO" if verbose else "WARNING"
    return setup_logging(
        console_level=console_level,
        file_level="DEBUG",
        log_file="test.log"
    )


# Convenience functions for common log levels
def setup_quiet_logging():
    """Quiet mode: Only errors in console, detailed logs in file"""
    return setup_logging(console_level="ERROR", file_level="INFO")


def setup_verbose_logging():
    """Verbose mode: Everything in console and file"""
    return setup_logging(console_level="INFO", file_level="DEBUG")


def setup_debug_logging():
    """Debug mode: Everything everywhere"""
    return setup_logging(console_level="DEBUG", file_level="DEBUG")

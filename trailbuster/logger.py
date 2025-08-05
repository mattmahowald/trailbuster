"""
Comprehensive logging system for TrailBuster.

This module provides a beautiful, structured logging system with:
- Colored console output with emojis
- Structured JSON logging for file output
- Different log levels for different components
- Progress tracking and statistics
- Performance monitoring
"""

import json
import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import colorama
from colorama import Fore, Back, Style

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for console output."""

    # Color and emoji mappings for different log levels
    LEVEL_COLORS = {
        logging.DEBUG: (Fore.CYAN, "🔍"),
        logging.INFO: (Fore.GREEN, "ℹ️"),
        logging.WARNING: (Fore.YELLOW, "⚠️"),
        logging.ERROR: (Fore.RED, "❌"),
        logging.CRITICAL: (Fore.RED + Back.WHITE + Style.BRIGHT, "💥"),
    }

    # Component-specific colors and emojis
    COMPONENT_STYLES = {
        "AUTH": (Fore.MAGENTA, "🔐"),
        "CRAWLER": (Fore.BLUE, "🕷️"),
        "PARSER": (Fore.CYAN, "📄"),
        "GMAIL": (Fore.GREEN, "📧"),
        "MAIN": (Fore.WHITE, "🚀"),
        "LINK": (Fore.YELLOW, "🔗"),
        "PROGRESS": (Fore.BLUE, "📊"),
        "PERFORMANCE": (Fore.MAGENTA, "⚡"),
    }

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # Get base color and emoji for log level
        level_color, level_emoji = self.LEVEL_COLORS.get(
            record.levelno, (Fore.WHITE, "📝")
        )

        # Get component-specific styling
        component = getattr(record, "component", "GENERAL")
        component_color, component_emoji = self.COMPONENT_STYLES.get(
            component, (Fore.WHITE, "📝")
        )

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]

        # Format the message
        if self.use_colors:
            # Colored output
            formatted = (
                f"{Fore.LIGHTBLACK_EX}{timestamp}{Style.RESET_ALL} "
                f"{level_color}{level_emoji}{Style.RESET_ALL} "
                f"{component_color}{component_emoji} {component}{Style.RESET_ALL} "
                f"{level_color}{record.levelname:8}{Style.RESET_ALL} "
                f"{record.getMessage()}"
            )
        else:
            # Plain text output
            formatted = (
                f"{timestamp} {level_emoji} {component_emoji} {component} "
                f"{record.levelname:8} {record.getMessage()}"
            )

        return formatted


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging to files."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "component": getattr(record, "component", "GENERAL"),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry)


class ProgressTracker:
    """Tracks progress of crawling operations with beautiful progress bars."""

    def __init__(self, total: int, description: str = "Progress"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        self.last_update = time.time()

    def update(self, increment: int = 1, message: str = ""):
        """Update progress and display progress bar."""
        self.current += increment
        current_time = time.time()

        # Only update display every 0.5 seconds to avoid spam
        if current_time - self.last_update > 0.5 or self.current >= self.total:
            self._display_progress(message)
            self.last_update = current_time

    def _display_progress(self, message: str = ""):
        """Display a beautiful progress bar."""
        percentage = (self.current / self.total) * 100
        elapsed_time = time.time() - self.start_time

        # Calculate ETA
        if self.current > 0:
            eta = (elapsed_time / self.current) * (self.total - self.current)
            eta_str = f"ETA: {eta:.1f}s"
        else:
            eta_str = "ETA: --"

        # Create progress bar
        bar_length = 30
        filled_length = int(bar_length * self.current // self.total)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        # Format the output
        progress_line = (
            f"{Fore.BLUE}📊 {self.description}{Style.RESET_ALL} "
            f"[{bar}] {self.current}/{self.total} ({percentage:.1f}%) "
            f"{Fore.LIGHTBLACK_EX}{eta_str}{Style.RESET_ALL}"
        )

        if message:
            progress_line += f" - {message}"

        # Clear line and print progress
        print(f"\r{progress_line}", end="", flush=True)

        if self.current >= self.total:
            print()  # New line when complete


class TrailBusterLogger:
    """Main logger class for TrailBuster application."""

    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        self.log_level = getattr(logging, log_level.upper())
        self.log_file = log_file

        # Create logger
        self.logger = logging.getLogger("trailbuster")
        self.logger.setLevel(self.log_level)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = ColoredFormatter(use_colors=True)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler with JSON output
        if log_file:
            self._setup_file_handler(log_file)

    def _setup_file_handler(self, log_file: str):
        """Setup file handler with JSON formatting and rotation."""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Rotating file handler (10MB max, keep 5 files)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(self.log_level)
        json_formatter = JSONFormatter()
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)

    def get_logger(self, component: str) -> "ComponentLogger":
        """Get a component-specific logger."""
        return ComponentLogger(self.logger, component)


class ComponentLogger:
    """Component-specific logger with structured logging capabilities."""

    def __init__(self, base_logger: logging.Logger, component: str):
        self.base_logger = base_logger
        self.component = component

    def _log(
        self, level: int, message: str, extra_data: Optional[Dict[str, Any]] = None
    ):
        """Internal logging method with component and extra data."""
        extra = {"component": self.component}
        if extra_data:
            extra["extra_data"] = extra_data

        self.base_logger.log(level, message, extra=extra)

    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        self._log(logging.DEBUG, message, extra_data)

    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self._log(logging.INFO, message, extra_data)

    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self._log(logging.WARNING, message, extra_data)

    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log error message."""
        self._log(logging.ERROR, message, extra_data)

    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log critical message."""
        self._log(logging.CRITICAL, message, extra_data)

    def start_operation(self, operation: str, **kwargs):
        """Log the start of an operation with context."""
        context = {"operation": operation, "start_time": time.time()}
        context.update(kwargs)
        self.info(f"Starting {operation}", context)

    def end_operation(self, operation: str, success: bool = True, **kwargs):
        """Log the end of an operation with results."""
        context = {"operation": operation, "success": success}
        context.update(kwargs)
        status = "completed successfully" if success else "failed"
        self.info(f"{operation} {status}", context)

    def performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics."""
        context = {"operation": operation, "duration": duration}
        context.update(kwargs)
        self.info(f"Performance: {operation} took {duration:.3f}s", context)

    def link_extraction(self, url: str, links_found: int, links_extracted: int):
        """Specialized logging for link extraction."""
        extra_data = {
            "url": url,
            "links_found": links_found,
            "links_extracted": links_extracted,
            "extraction_rate": (
                (links_extracted / links_found * 100) if links_found > 0 else 0
            ),
        }
        self.info(
            f"Link extraction: {links_extracted}/{links_found} links extracted from {url}",
            extra_data,
        )


# Global logger instance
_logger_instance: Optional[TrailBusterLogger] = None


def setup_logging(
    log_level: str = "INFO", log_file: Optional[str] = None, output_dir: str = "logs"
) -> TrailBusterLogger:
    """Setup global logging configuration."""
    global _logger_instance

    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(output_dir, f"trailbuster_{timestamp}.log")

    _logger_instance = TrailBusterLogger(log_level, log_file)
    return _logger_instance


def get_logger(component: str) -> ComponentLogger:
    """Get a component-specific logger."""
    global _logger_instance

    if _logger_instance is None:
        # Setup default logging if not already configured
        setup_logging()

    return _logger_instance.get_logger(component)


# Convenience functions for quick logging
def log_auth(message: str, **kwargs):
    """Log authentication-related messages."""
    get_logger("AUTH").info(message, kwargs if kwargs else None)


def log_crawler(message: str, **kwargs):
    """Log crawler-related messages."""
    get_logger("CRAWLER").info(message, kwargs if kwargs else None)


def log_parser(message: str, **kwargs):
    """Log parser-related messages."""
    get_logger("PARSER").info(message, kwargs if kwargs else None)


def log_gmail(message: str, **kwargs):
    """Log Gmail-related messages."""
    get_logger("GMAIL").info(message, kwargs if kwargs else None)


def log_main(message: str, **kwargs):
    """Log main application messages."""
    get_logger("MAIN").info(message, kwargs if kwargs else None)


def log_link_extraction(url: str, links_found: int, links_extracted: int):
    """Log link extraction results."""
    get_logger("LINK").link_extraction(url, links_found, links_extracted)


def log_performance(operation: str, duration: float, **kwargs):
    """Log performance metrics."""
    get_logger("PERFORMANCE").performance(operation, duration, **kwargs)

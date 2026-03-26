"""Logging configuration for LangGraph framework.

This module provides centralized logging configuration for LangGraph-related loggers,
enabling independent file output with rotation for better log management.
"""

import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Literal, Optional


def setup_langgraph_logging(
    log_file: str = "/work/logs/ReportCenterService/langgraph.log",
    level: int = logging.INFO,
    rotation_type: Literal["size", "time"] = "size",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 10,
    console_output: bool = True,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
    """Configure logging for LangGraph-related loggers with file output.

    Args:
        log_file: Path to the log file. Parent directories will be created if needed.
        level: Logging level (default: logging.INFO).
        rotation_type: Type of rotation - "size" (RotatingFileHandler) or
            "time" (TimedRotatingFileHandler).
        max_bytes: Max size per file for size-based rotation (default: 10 MB).
        backup_count: Number of backup files to keep (default: 5).
        console_output: Whether to also output to console (default: True).
        log_format: Format string for log messages.

    Note:
        Sets `propagate=False` on all configured loggers to prevent duplicate logs
        in the root logger.
    """
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Create appropriate handler based on rotation type
    if rotation_type == "size":
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:  # time-based rotation
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            backupCount=backup_count,
            encoding="utf-8",
        )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Optionally add console handler
    console_handler = None
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

    # LangGraph-related logger names to configure
    logger_names = [
        "langgraph",
        "langgraph_api",
        "langgraph_runtime",
        "langchain",
        "langchain_core",
        "langchain_community",
        "httpx",  # HTTP client used internally by LangGraph
    ]

    # Configure each logger
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

        # Remove any existing handlers to avoid duplicates
        logger.handlers.clear()

        # Add file handler
        logger.addHandler(file_handler)

        # Add console handler if enabled
        if console_handler:
            logger.addHandler(console_handler)

        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False


def setup_deerflow_logging(
    log_file: str = "/work/logs/ReportCenterService/deerflow.log",
    level: int = logging.INFO,
    rotation_type: Literal["size", "time"] = "size",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 10,
    console_output: bool = True,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
    """Configure logging for DeerFlow-related loggers with file output.

    Args:
        log_file: Path to the log file. Parent directories will be created if needed.
        level: Logging level (default: logging.INFO).
        rotation_type: Type of rotation - "size" (RotatingFileHandler) or
            "time" (TimedRotatingFileHandler).
        max_bytes: Max size per file for size-based rotation (default: 10 MB).
        backup_count: Number of backup files to keep (default: 10).
        console_output: Whether to also output to console (default: True).
        log_format: Format string for log messages.

    Note:
        Sets `propagate=False` on all configured loggers to prevent duplicate logs
        in the root logger.
    """
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Create appropriate handler based on rotation type
    if rotation_type == "size":
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:  # time-based rotation
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            backupCount=backup_count,
            encoding="utf-8",
        )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Optionally add console handler
    console_handler = None
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

    # DeerFlow-related logger names to configure
    # Using "deerflow" will capture all deerflow.* submodules
    logger_names = [
        "deerflow",
    ]

    # Configure each logger
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

        # Remove any existing handlers to avoid duplicates
        logger.handlers.clear()

        # Add file handler
        logger.addHandler(file_handler)

        # Add console handler if enabled
        if console_handler:
            logger.addHandler(console_handler)

        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False


def setup_gateway_logging(
    log_file: str = "/work/logs/ReportCenterService/gateway.log",
    level: int = logging.INFO,
    rotation_type: Literal["size", "time"] = "size",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 10,
    console_output: bool = True,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
    """Configure logging for Gateway-related loggers with file output.

    Args:
        log_file: Path to the log file. Parent directories will be created if needed.
        level: Logging level (default: logging.INFO).
        rotation_type: Type of rotation - "size" (RotatingFileHandler) or
            "time" (TimedRotatingFileHandler).
        max_bytes: Max size per file for size-based rotation (default: 10 MB).
        backup_count: Number of backup files to keep (default: 10).
        console_output: Whether to also output to console (default: True).
        log_format: Format string for log messages.

    Note:
        Sets `propagate=False` on all configured loggers to prevent duplicate logs
        in the root logger.
    """
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Create appropriate handler based on rotation type
    if rotation_type == "size":
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:  # time-based rotation
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            backupCount=backup_count,
            encoding="utf-8",
        )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Optionally add console handler
    console_handler = None
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

    # Gateway-related logger names to configure
    # Using "app.gateway" will capture all app.gateway.* submodules
    logger_names = [
        "app.gateway",
    ]

    # Configure each logger
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

        # Remove any existing handlers to avoid duplicates
        logger.handlers.clear()

        # Add file handler
        logger.addHandler(file_handler)

        # Add console handler if enabled
        if console_handler:
            logger.addHandler(console_handler)

        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False


def configure_all_logging(
    root_level: int = logging.INFO,
    langgraph_level: int = logging.INFO,
    deerflow_level: int = logging.INFO,
    gateway_level: int = logging.INFO,
    log_dir: str = "/work/logs/ReportCenterService",
    langgraph_file_output: bool = True,
    deerflow_file_output: bool = True,
    gateway_file_output: bool = True,
    rotation_type: Literal["size", "time"] = "size",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 10,
    console_output: bool = True,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
    """Unified logging configuration for the application.

    This function provides a single entry point for configuring root logger
    and module-specific loggers (LangGraph, DeerFlow, Gateway). Call this at
    application startup BEFORE importing any LangGraph modules.

    Args:
        root_level: Logging level for the root logger (default: INFO).
        langgraph_level: Logging level for LangGraph loggers (default: INFO).
        deerflow_level: Logging level for DeerFlow loggers (default: INFO).
        gateway_level: Logging level for Gateway loggers (default: INFO).
        log_dir: Directory for log files.
        langgraph_file_output: Whether to enable file output for LangGraph logs.
        deerflow_file_output: Whether to enable file output for DeerFlow logs.
        gateway_file_output: Whether to enable file output for Gateway logs.
        rotation_type: Type of rotation - "size" or "time".
        max_bytes: Max size per file for size-based rotation.
        backup_count: Number of backup files to keep.
        console_output: Whether to output logs to console.
        log_format: Format string for log messages.

    Example:
        >>> import logging
        >>> from deerflow.config.logging_config import configure_all_logging
        >>>
        >>> # Configure logging BEFORE importing langgraph modules
        >>> configure_all_logging(
        ...     root_level=logging.INFO,
        ...     langgraph_level=logging.INFO,
        ...     deerflow_level=logging.INFO,
        ...     gateway_level=logging.INFO,
        ...     log_dir="/work/logs/ReportCenterService",
        ...     langgraph_file_output=True,
        ...     deerflow_file_output=True,
        ...     gateway_file_output=True,
        ...     rotation_type="size",
        ...     max_bytes=10 * 1024 * 1024,
        ...     backup_count=10,
        ...     console_output=True,
        ... )
        >>>
        >>> # Now safe to import LangGraph modules
        >>> from langgraph_api.server import app
    """
    # Configure root logger for basic console output
    logging.basicConfig(
        level=root_level,
        format=log_format,
    )

    # Configure LangGraph-specific logging if enabled
    if langgraph_file_output:
        langgraph_log_file = os.path.join(log_dir, "langgraph.log")
        setup_langgraph_logging(
            log_file=langgraph_log_file,
            level=langgraph_level,
            rotation_type=rotation_type,
            max_bytes=max_bytes,
            backup_count=backup_count,
            console_output=console_output,
            log_format=log_format,
        )

    # Configure DeerFlow-specific logging if enabled
    if deerflow_file_output:
        deerflow_log_file = os.path.join(log_dir, "deerflow.log")
        setup_deerflow_logging(
            log_file=deerflow_log_file,
            level=deerflow_level,
            rotation_type=rotation_type,
            max_bytes=max_bytes,
            backup_count=backup_count,
            console_output=console_output,
            log_format=log_format,
        )

    # Configure Gateway-specific logging if enabled
    if gateway_file_output:
        gateway_log_file = os.path.join(log_dir, "gateway.log")
        setup_gateway_logging(
            log_file=gateway_log_file,
            level=gateway_level,
            rotation_type=rotation_type,
            max_bytes=max_bytes,
            backup_count=backup_count,
            console_output=console_output,
            log_format=log_format,
        )

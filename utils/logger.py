"""
utils/logger.py
================
Centralized logging setup for the whole application.

Provides:
    * A rotating file handler (logs/app.log) so log files don't grow
      unbounded on a long-running production server.
    * A colorized console handler for pleasant local development output.
    * ``get_logger(name)`` helper used throughout controllers/services so
      every module logs under its own namespace (e.g. "services.face_service").
"""

import logging
import os
from logging.handlers import RotatingFileHandler

import colorlog


def configure_logging(logs_folder: str, debug: bool = False) -> None:
    """
    Configure the root logger once, at application startup.

    Args:
        logs_folder: Directory where app.log should be written.
        debug: When True, sets console/file level to DEBUG instead of INFO.
    """
    os.makedirs(logs_folder, exist_ok=True)
    log_level = logging.DEBUG if debug else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if configure_logging() is called more than once
    # (e.g. once by the Flask reloader's parent process, once by the child).
    if root_logger.handlers:
        return

    # ---- Rotating file handler (5 MB per file, keep 5 backups) ----
    file_handler = RotatingFileHandler(
        os.path.join(logs_folder, "app.log"), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)

    # ---- Colorized console handler ----
    console_handler = colorlog.StreamHandler()
    console_formatter = colorlog.ColoredFormatter(
        fmt="%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger. Use ``get_logger(__name__)`` in every module."""
    return logging.getLogger(name)

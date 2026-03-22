"""
GhostBox - Logging System
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .config import config


def setup_logger(name: str = "ghostbox") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.log_level))

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler with rotation
    fh = RotatingFileHandler(config.log_file, maxBytes=5_000_000, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


log = setup_logger()

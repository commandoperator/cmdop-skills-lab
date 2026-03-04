"""Logging utility for llm-email."""

import logging
import os

from llm_email.config import LOG_DIR, LOG_FILE


def get_logger(name: str = "llm-email") -> logging.Logger:
    """Get a configured logger that writes to both file and stderr."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — ensure log dir exists
    os.makedirs(LOG_DIR, exist_ok=True)
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Stderr handler — only warnings+
    sh = logging.StreamHandler()
    sh.setLevel(logging.WARNING)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger


log = get_logger()

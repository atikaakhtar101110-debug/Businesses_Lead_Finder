"""
Shared logger factory so every agent/tool logs consistently.
"""
import logging
import sys
from utils.config import config

_CONFIGURED = False


def _configure_root():
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%H:%M:%S")
    )
    root = logging.getLogger("lead_finder")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"lead_finder.{name}")

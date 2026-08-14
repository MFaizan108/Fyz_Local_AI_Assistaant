"""Minimal internal logging so failures (Ollama timeouts, tool errors) are
recorded somewhere real instead of either vanishing or being dumped
straight into a user-facing reply/GUI chat log as a raw traceback."""

import logging
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def get_logger(name: str = "fyz") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        _LOG_DIR.mkdir(exist_ok=True)
        handler = logging.FileHandler(_LOG_DIR / "fyz.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger

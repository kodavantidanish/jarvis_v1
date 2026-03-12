# utils/logger.py

import os
import logging
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'logs')


def get_logger(name="jarvis"):
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log")

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already set up

    logger.setLevel(logging.DEBUG)

    # File handler — logs everything
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # Console handler — only warnings and above
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
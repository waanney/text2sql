import os
import sys
import logging
import json
from datetime import datetime
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """
    Format logs as JSON objects for downstream analysis/parsing.
    """
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add extra attributes passed to the logger
        if hasattr(record, "extra_data") and record.extra_data:
            log_data["extra"] = record.extra_data
        
        # Add exception details if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(name="pamo_sql", log_level=None, log_format=None, log_dir=None):
    """
    Set up a logger with console and file handlers, supporting standard or JSON logs.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured

    # Read config from env or arguments
    level_str = log_level or os.environ.get("LOG_LEVEL", "INFO").upper()
    fmt_str = log_format or os.environ.get("LOG_FORMAT", "text").lower()
    dir_str = log_dir or os.environ.get("LOG_DIR", "artifacts/logs")

    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    # Console Handler
    c_handler = logging.StreamHandler(sys.stdout)
    c_handler.setLevel(level)

    # File Handler
    Path(dir_str).mkdir(parents=True, exist_ok=True)
    log_file = Path(dir_str) / f"{name}.log"
    f_handler = logging.FileHandler(log_file, encoding="utf-8")
    f_handler.setLevel(level)

    # Formatter Choice
    if fmt_str == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] (%(filename)s:%(lineno)d) - %(message)s"
        )

    c_handler.setFormatter(formatter)
    f_handler.setFormatter(formatter)

    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger


# Global default logger
logger = setup_logger()


def log_event(level, message, extra=None):
    """
    Log an event with optional extra structured metadata.
    """
    extra_dict = {"extra_data": extra} if extra else {}
    if level.upper() == "DEBUG":
        logger.debug(message, extra=extra_dict)
    elif level.upper() == "INFO":
        logger.info(message, extra=extra_dict)
    elif level.upper() == "WARNING":
        logger.warning(message, extra=extra_dict)
    elif level.upper() == "ERROR":
        logger.error(message, extra=extra_dict, exc_info=True)
    else:
        logger.info(message, extra=extra_dict)

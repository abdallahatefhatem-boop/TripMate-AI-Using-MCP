import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Define project root and logs directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Standard continuous application log file (always the main active log)
LOG_FILE_PATH = LOGS_DIR / "app.log"

# Log formatting string
LOG_FORMAT = "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d] %(name)s - %(message)s"

# File handler with rotation (max 10MB per file, keeping 5 backup files)
file_handler = RotatingFileHandler(
    LOG_FILE_PATH,
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Console stream handler
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Configure root logger with force=True
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[file_handler, stream_handler],
    force=True,
)

# Export standard logger instance
logger = logging.getLogger("my_project")
logger.setLevel(logging.INFO)

# Attach file handler to uvicorn loggers so HTTP requests are also saved in app.log
for uvi_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    uvi_log = logging.getLogger(uvi_logger_name)
    uvi_log.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in uvi_log.handlers):
        uvi_log.addHandler(file_handler)


def get_logger(name: str = "my_project") -> logging.Logger:
    """
    Returns a configured logger instance with the given name.
    """
    return logging.getLogger(name)


__all__ = ["logging", "logger", "get_logger", "LOG_FILE_PATH", "file_handler"]

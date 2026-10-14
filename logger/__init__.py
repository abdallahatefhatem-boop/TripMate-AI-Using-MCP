import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Define project root and logs directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Generate timestamped log file name
LOG_FILE_NAME = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
LOG_FILE_PATH = LOGS_DIR / LOG_FILE_NAME

# Log formatting string
LOG_FORMAT = "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d] %(name)s - %(message)s"

# Configure root logger
logging.basicConfig(
    format=LOG_FORMAT,
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)

# Export standard logger instance
logger = logging.getLogger("my_project")


def get_logger(name: str = "my_project") -> logging.Logger:
    """
    Returns a configured logger instance with the given name.
    """
    return logging.getLogger(name)


__all__ = ["logging", "logger", "get_logger", "LOG_FILE_PATH"]

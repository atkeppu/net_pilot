import logging
import os
from logging.handlers import RotatingFileHandler
import locale
import sys

LOG_FILE_NAME = "debug.log"

def get_application_path() -> str:
    """Gets the path of the executable or script."""
    if getattr(sys, 'frozen', False):
        # Running as a bundled exe (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Running as a .py script
        return os.path.dirname(os.path.abspath(__file__))

LOG_DIR = get_application_path()

def get_log_file_path() -> str:
    """Returns the full path to the log file."""
    return os.path.join(LOG_DIR, LOG_FILE_NAME)

def setup_logging():
    """Configures logging to a rotating file in the application's directory."""
    log_file = get_log_file_path()

    # Use a rotating file handler to prevent the log file from growing indefinitely
    # 1MB per file, keeping the last 5 files.
    # Use UTF-8 for log file encoding for universal compatibility.
    handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
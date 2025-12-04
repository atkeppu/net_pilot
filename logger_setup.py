import logging
import os
from logging.handlers import RotatingFileHandler
import sys

LOG_FILE_NAME = "debug.log"

def get_application_path() -> str:
    """Gets the path of the executable or script."""
    # Check if the application is running as a frozen executable (e.g., PyInstaller)
    if getattr(sys, 'frozen', False):
        # If so, the path is the directory of the executable
        return os.path.dirname(sys.executable)
    else:
        # Otherwise, it's running as a script, so use the script's directory
        return os.path.dirname(os.path.abspath(__file__))

# The log directory will now always be the project's root directory.
LOG_DIR = get_application_path()

def get_log_file_path() -> str:
    """Returns the full path to the log file."""
    return os.path.join(LOG_DIR, LOG_FILE_NAME)

def setup_logging():
    """Configures logging to a rotating file in the application's directory."""
    log_file = get_log_file_path()
    
    # Determine log level from environment variable, defaulting to INFO
    log_level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Use a rotating file handler to prevent the log file from growing indefinitely
    # 1MB per file, keeping the last 5 files.
    # Use UTF-8 for log file encoding for universal compatibility.
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)

    # Also log to console if in debug mode for easier development
    if log_level == logging.DEBUG:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        root_logger.info("Debug mode enabled: Logging to both file and console.")
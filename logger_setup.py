import logging
import logging.handlers
import os
import sys
from pathlib import Path

# --- Logging Configuration ---

# Use the user's AppData/Roaming directory for logs. This is the standard for
# Windows applications and avoids permission issues with Program Files.
# Fallback to the script's directory if APPDATA is not set.
LOG_DIR_PARENT = Path(os.getenv('APPDATA', '.'))
APP_NAME = "NetPilot"
LOG_DIR = LOG_DIR_PARENT / APP_NAME / "logs"
LOG_FILE_NAME = "app.log"

# Configuration for the RotatingFileHandler
MAX_LOG_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB
BACKUP_COUNT = 5  # Keep 5 old log files (e.g., app.log.1, app.log.2, ...)


def _get_log_level_from_env() -> int:
    """
    Gets the logging level from the 'LOG_LEVEL' environment variable.
    Defaults to logging.INFO if the variable is not set or invalid.
    """
    # Default to DEBUG when running from source for better development feedback,
    # and INFO when packaged to avoid overly verbose logs for end-users.
    if getattr(sys, 'frozen', False):
        default_level = 'INFO'
    else:
        default_level = 'DEBUG'

    log_level_str = os.getenv('LOG_LEVEL', default_level).upper()
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return log_levels.get(log_level_str, logging.INFO)


def get_log_file_path() -> Path:
    """Returns the full, absolute path to the log file."""
    return LOG_DIR / LOG_FILE_NAME


def get_project_or_exe_root() -> Path:
    """
    Returns the absolute path to the project root when running from source,
    or the directory containing the .exe when running as a packaged app.
    """
    if getattr(sys, 'frozen', False):
        # Running as a bundled exe (e.g., via PyInstaller).
        # The executable is in the root of the distribution.
        return Path(sys.executable).parent
    else:
        # Running as a script
        return Path(sys.argv[0]).resolve().parent

def get_dist_path() -> Path:
    """Returns the absolute path to the 'dist' directory."""
    if getattr(sys, 'frozen', False):
        return get_project_or_exe_root()
    return get_project_or_exe_root() / 'dist'


def setup_logging() -> Path | None:
    """
    Configures logging with a RotatingFileHandler and a console handler.

    - Logs are stored in a version-safe, user-specific directory.
    - Log files rotate to prevent them from growing indefinitely.
    - If file logging fails, it falls back to console-only logging.

    Returns:
        The absolute path to the log file if successful, otherwise None.
    """
    log_file_path: Path = get_log_file_path()
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    root_logger = logging.getLogger()
    # Set level from environment variable, defaulting to INFO.
    # This allows for easy debugging without code changes.
    root_logger.setLevel(_get_log_level_from_env())
    
    # Clear any existing handlers to prevent duplicate logging.
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # --- File Handler (Rotating) ---
    try:
        # Ensure the log directory exists.
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Create a handler that rotates log files when they reach a certain size.
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=MAX_LOG_SIZE_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        # If we can't create the log directory/file, we can't log to a file.
        # Fallback to console-only logging and print an error.
        print(f"CRITICAL: Unable to create log file at {log_file_path}. "
              f"Logging to console only. Error: {e}", file=sys.stderr)        

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # Return the path only if the file handler was successfully added.
    return log_file_path if any(isinstance(h, logging.FileHandler) for h in root_logger.handlers) else None
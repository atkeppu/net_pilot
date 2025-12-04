import ctypes
import subprocess
import logging
import os

from exceptions import NetworkManagerError
from github_integration import check_github_cli_auth, publish_to_github
from gui.constants import GITHUB_REPO, APP_NAME

logger = logging.getLogger(__name__)

def is_admin() -> bool:
    """Check if the script is running with administrative privileges on Windows."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def _run_system_command(command: list[str], error_message_prefix: str, check: bool = True):
    """
    A helper function to run a system command and handle errors consistently.
    Raises NetworkManagerError on failure.
    """
    logger.debug("Executing system command: %s", " ".join(command))
    try:
        # Use text=False to capture raw bytes and decode manually for robustness
        result = subprocess.run(command, shell=False, check=check, capture_output=True)
        if result.returncode != 0 and check:
            # Manually raise for non-zero exit codes when check=True
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        # Safely decode output for error logging
        try:
            stdout = e.stdout.decode('oem', errors='ignore').strip() if e.stdout else "None"
            stderr = e.stderr.decode('oem', errors='ignore').strip() if e.stderr else "None"
        except AttributeError: # In case stdout/stderr are not bytes
            stdout = str(e.stdout).strip()
            stderr = str(e.stderr).strip()

        error_message = (
            f"{error_message_prefix}\n\n"
            f"Command: {' '.join(e.cmd)}\n"
            f"Return Code: {e.returncode}\n"
            f"Error Output: {stderr}\n"
            f"Standard Output: {stdout}"
        )
        logger.error("System command failed: %s", error_message)
        raise NetworkManagerError(error_message) from e
    except FileNotFoundError as e:
        raise NetworkManagerError(f"Command '{command[0]}' not found. Is it in the system's PATH?") from e

def reset_network_stack():
    """
    Resets the Winsock Catalog using 'netsh winsock reset'.
    This action requires a system reboot to complete.
    Raises NetworkManagerError on failure.
    """
    _run_system_command(['netsh', 'winsock', 'reset'], "Failed to reset network stack.")

def flush_dns_cache():
    """
    Flushes the DNS resolver cache using 'ipconfig /flushdns'.
    Raises NetworkManagerError on failure.
    """
    _run_system_command(['ipconfig', '/flushdns'], "Failed to flush DNS cache.")

def release_renew_ip():
    """
    Releases and renews the IP address for all adapters.
    Raises NetworkManagerError on failure.
    """
    # First, try to release the IP. We use check=False because this can fail
    # if no IP is assigned, which is not a critical error. We still log it.
    release_result = _run_system_command(['ipconfig', '/release'], "Failed to release IP address.", check=False)
    if release_result.returncode != 0:
        logger.warning("ipconfig /release finished with a non-zero exit code. This may be normal.")
    # Then, renew the IP. This is the critical step.
    _run_system_command(['ipconfig', '/renew'], "Failed to renew IP address.")

def terminate_process_by_pid(pid: int):
    """
    Terminates a process by its Process ID (PID).
    Raises NetworkManagerError on failure.
    """
    if pid in [0, 4]: # Do not allow terminating System Idle or System processes
        raise NetworkManagerError("Terminating system-critical processes is not allowed.")
    try:
        _run_system_command(['taskkill', '/F', '/T', '/PID', str(pid)], f"Failed to terminate process with PID {pid}.")
    except NetworkManagerError as e:
        # Re-raise to keep the original detailed message from the helper
        raise e

def create_github_release(app_version: str, notes: str) -> str:
    """
    Prepares and executes the creation of a new GitHub release.
    """
    is_ok, message = check_github_cli_auth()
    if not is_ok:
        raise NetworkManagerError(message)

    asset_name = f"{APP_NAME}.exe"
    asset_path = os.path.join("dist", asset_name) # Assuming build script creates NetPilot.exe

    asset_to_upload = asset_path if os.path.exists(asset_path) else None
    return publish_to_github(f"v{app_version}", GITHUB_REPO, f"Version {app_version}", notes, asset_path=asset_to_upload)
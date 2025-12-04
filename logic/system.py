import ctypes
import logging
import os

from exceptions import NetworkManagerError
from github_integration import check_github_cli_auth, publish_to_github
from gui.constants import GITHUB_REPO, APP_NAME
from .command_utils import run_system_command

logger = logging.getLogger(__name__)

def is_admin() -> bool:
    """Check if the script is running with administrative privileges on Windows."""
    try:
        # Returns non-zero if admin, 0 if not.
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False

def reset_network_stack():
    """
    Resets the Winsock Catalog using 'netsh winsock reset'.
    This action requires a system reboot to complete.
    Raises NetworkManagerError on failure.
    """
    run_system_command(['netsh', 'winsock', 'reset'], "Failed to reset network stack.")

def flush_dns_cache():
    """
    Flushes the DNS resolver cache using 'ipconfig /flushdns'.
    Raises NetworkManagerError on failure.
    """
    run_system_command(['ipconfig', '/flushdns'], "Failed to flush DNS cache.")

def release_renew_ip():
    """
    Releases and renews the IP address for all adapters.
    Raises NetworkManagerError on failure.
    """
    try:
        # Step 1: Release the current IP address.
        # We use check=False because this command can fail gracefully if an adapter
        # is disconnected or has no IP, which is not a critical error.
        release_result = run_system_command(['ipconfig', '/release'], "IP address release command finished.", check=False)
        if release_result.returncode != 0:
            # Decode output safely for inspection. The error is often in stderr.
            # The _safe_decode logic is part of run_system_command's error handling,
            # but here we need to decode the raw bytes ourselves.
            error_output = (release_result.stderr or release_result.stdout).decode('oem', errors='ignore').strip().lower()
            
            # These are common, expected "errors" that we can safely ignore.
            non_critical_errors = [
                "no operation can be performed", # Adapter is disconnected
                "media is disconnected",         # Cable is unplugged
                "the system cannot find the file specified" # Can occur in some virtual adapter scenarios
            ]
            if any(e in error_output for e in non_critical_errors):
                logger.info("ipconfig /release failed as expected (no address to release or media disconnected).")
            else:
                # Log any other non-zero exit codes as a warning, but don't stop the process.
                logger.warning("ipconfig /release finished with an unexpected non-zero exit code. Error: %s", error_output.strip())

        # Step 2: Renew the IP address. This is the critical step.
        run_system_command(['ipconfig', '/renew'], "Failed to renew IP address.")

    except NetworkManagerError as e:
        # Step 3: Handle specific, known errors from the 'renew' step to provide better user feedback.
        error_str = str(e).lower()
        if "unable to contact your dhcp server" in error_str:
            raise NetworkManagerError(
                "Could not renew IP address: Unable to contact the DHCP server. "
                "Please check your network connection and router.",
                code='DHCP_SERVER_UNREACHABLE'
            ) from e
        if "no adapter is in the state permissible" in error_str:
            raise NetworkManagerError(
                "Could not renew IP address: One or more network adapters are disabled. Please enable them first.",
                code='ADAPTER_DISABLED'
            ) from e
        raise # Re-raise the original, detailed exception for any other errors

def terminate_process_by_pid(pid: int):
    """
    Terminates a process by its Process ID (PID).
    Raises NetworkManagerError on failure.
    """
    if pid in [0, 4]: # Do not allow terminating System Idle or System processes
        raise NetworkManagerError("Terminating system-critical processes is not allowed.")
    try:
        run_system_command(['taskkill', '/F', '/T', '/PID', str(pid)], f"Failed to terminate process with PID {pid}.")
    except NetworkManagerError:
        # Re-raise to keep the original detailed message from the helper.
        raise

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
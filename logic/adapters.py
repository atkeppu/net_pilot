import json
import logging
import time
import os

from exceptions import NetworkManagerError
from .command_utils import run_external_ps_script, run_ps_command
from .wifi import disconnect_wifi, get_current_wifi_details

logger = logging.getLogger(__name__)

# Constants for the disconnect-and-disable workflow
DISCONNECT_TIMEOUT_SECONDS = 5
POLL_INTERVAL_SECONDS = 1

def get_adapter_details() -> list[dict]:
    """
    Retrieves detailed information for all physical network adapters by running
    an optimized external PowerShell script.
    """
    try:
        result_json = run_external_ps_script('Get-AdapterDetails.ps1')
        # If the script returns nothing, treat it as an empty list of adapters.
        if not result_json:
            return []
        adapters = json.loads(result_json)

        if not isinstance(adapters, list):
            adapters = [adapters]

        for adapter in adapters:
            # The 'Status' from Get-NetAdapter is the most reliable administrative state.
            # It can be 'Up', 'Down', 'Disabled', etc. We simplify this for the UI.
            adapter['admin_state'] = 'Disabled' if adapter.get('Status') == 'Disabled' else 'Enabled'
        return adapters
    except (json.JSONDecodeError, NetworkManagerError) as e:
        raise NetworkManagerError(f"Failed to parse adapter details from PowerShell: {e}") from e

def _handle_adapter_status_error(error: NetworkManagerError, adapter_name: str, action: str):
    """Analyzes a NetworkManagerError and re-raises a more specific one if possible."""
    error_str = str(error).lower()  # noqa: E501

    # Check for the specific "cannot disable" error to provide a helpful hint.
    if action == 'disable' and ("cannot be disabled" in error_str or "ei voi poistaa käytöstä" in error_str):  # noqa: E501
        raise NetworkManagerError(
            f"Cannot disable '{adapter_name}' while it is connected to a Wi-Fi network.",  # noqa: E501
            code='WIFI_CONNECTED_DISABLE_FAILED'
        ) from error

    # Check for "already in state" error.
    # The message is typically "The object is already in the state 'Enabled'."
    if "object is already in the state" in error_str:
        raise NetworkManagerError(
            f"Adapter '{adapter_name}' is already {action}d.") from error

    # For all other errors, re-raise a generic but informative exception.
    raise NetworkManagerError(
        f"Failed to {action} adapter '{adapter_name}':\n{error}") from error

def set_network_adapter_status_windows(adapter_name: str, action: str):
    """
    Enables or disables a network adapter on Windows using PowerShell. This
    version does not proactively check Wi-Fi status, relying on the OS to fail
    if needed.
    """
    if action not in ['enable', 'disable']:
        raise ValueError(
            f"Invalid action '{action}'. Must be 'enable' or 'disable'.")

    # Using PowerShell is more robust than netsh for enabling/disabling.
    ps_command = action.capitalize()  # noqa: E501
    ps_script = f"{ps_command}-NetAdapter -Name '{adapter_name}' -Confirm:$false"

    try:
        run_ps_command(ps_script)
    except NetworkManagerError as e:
        _handle_adapter_status_error(e, adapter_name, action)

def disconnect_wifi_and_disable_adapter(adapter_name: str):
    """A multi-step workflow to first disconnect from Wi-Fi, then disable the
    adapter.

    Yields status messages for the UI to consume.
    """
    yield "Step 1/3: Disconnecting from Wi-Fi..."
    # This function now handles the "already disconnected" case gracefully.
    disconnect_wifi()
    yield "Step 2/3: Confirming disconnection..."
    start_time = time.time()
    while time.time() - start_time < DISCONNECT_TIMEOUT_SECONDS:
        if get_current_wifi_details() is None:
            break  # Disconnection confirmed
        time.sleep(POLL_INTERVAL_SECONDS)
    else:
        # If the loop finishes without breaking, the timeout was reached.
        raise NetworkManagerError(
            f"Failed to confirm Wi-Fi disconnection within {DISCONNECT_TIMEOUT_SECONDS} seconds.")

    yield f"Step 3/3: Disabling adapter '{adapter_name}'..."
    set_network_adapter_status_windows(adapter_name, 'disable')

    yield f"Successfully disabled '{adapter_name}'."

def is_network_available() -> bool:
    """
    Checks if any network adapter is enabled and has a valid IP address.
    Returns True if a network is available, False otherwise.
    """
    try:
        adapters = get_adapter_details()
        for adapter in adapters:
            if adapter.get('admin_state') == 'Enabled' and adapter.get('IPv4Address'):
                # Found an active and enabled adapter.
                return True
        # No active adapters found.
        return False
    except NetworkManagerError:
        # Assume no network if adapter details cannot be retrieved.
        return False
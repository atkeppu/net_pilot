import subprocess
import json
import base64
import logging

from exceptions import NetworkManagerError

logger = logging.getLogger(__name__)

def _run_ps_command(script: str) -> str:
    """
    Runs a PowerShell script safely using -EncodedCommand.
    Returns the decoded stdout string.
    """
    try:
        encoded_script = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        command = ['powershell', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', encoded_script]
        result = subprocess.run(command, shell=False, check=True, capture_output=True)
        return result.stdout.decode('utf-8', errors='ignore')
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise NetworkManagerError(f"PowerShell command failed: {e}") from e

def get_adapter_details() -> list[dict]:
    """
    Retrieves detailed information for all physical network adapters using PowerShell.
    """
    ps_script = (
        "Get-CimInstance -Class Win32_NetworkAdapter | Where-Object { $_.PhysicalAdapter } | ForEach-Object {"
        "    $netAdapter = Get-NetAdapter -InterfaceIndex $_.InterfaceIndex;"
        "    $ip4 = (Get-NetIPAddress -InterfaceIndex $_.InterfaceIndex -AddressFamily IPv4).IPAddress;"
        "    $ip6 = (Get-NetIPAddress -InterfaceIndex $_.InterfaceIndex -AddressFamily IPv6).IPAddress;"
        "    [PSCustomObject]@{ "
        "        Name = $netAdapter.Name;"
        "        InterfaceDescription = $netAdapter.InterfaceDescription;"
        "        MacAddress = $netAdapter.MacAddress;"
        "        LinkSpeed = $netAdapter.LinkSpeed;"
        "        Status = $netAdapter.Status;"
        "        DriverVersion = $netAdapter.DriverVersion;"
        "        DriverDate = $netAdapter.DriverDate;"
        "        ComponentID = $netAdapter.ComponentID;"
        "        IPv4Address = $ip4;"
        "        IPv6Address = $ip6;"
        "        NetConnectionStatus = $_.NetConnectionStatus"
        "    }"
        "} | ConvertTo-Json"
    )
    
    try:
        result_json = _run_ps_command(ps_script)
        adapters = json.loads(result_json)
        
        if not isinstance(adapters, list):
            adapters = [adapters]

        for adapter in adapters:
            # NetConnectionStatus from Win32_NetworkAdapter is the most reliable administrative state.
            # A value of 4 means 'Disabled'. All other values mean it's administratively enabled.
            adapter['admin_state'] = 'Disabled' if adapter.get('NetConnectionStatus') == 4 else 'Enabled'
        return adapters
    except (json.JSONDecodeError, NetworkManagerError) as e:
        raise NetworkManagerError(f"Failed to parse adapter details from PowerShell: {e}") from e

def set_network_adapter_status_windows(adapter_name: str, action: str):
    """
    Enables or disables a network adapter on Windows using PowerShell.
    This version does not proactively check Wi-Fi status, relying on the OS to fail if needed.
    """
    if action not in ['enable', 'disable']:
        raise ValueError("Action must be 'enable' or 'disable'.")

    # Using PowerShell is more robust than netsh for enabling/disabling.
    if action == 'enable':
        ps_script = f"Enable-NetAdapter -Name '{adapter_name}' -Confirm:$false"
    else:
        ps_script = f"Disable-NetAdapter -Name '{adapter_name}' -Confirm:$false"

    try:
        _run_ps_command(ps_script)
    except NetworkManagerError as e:
        # Check for the specific "cannot disable" error to provide a helpful hint.
        error_str = str(e).lower()
        if action == 'disable' and ("cannot be disabled" in error_str or "ei voi poistaa käytöstä" in error_str):
            raise NetworkManagerError(
                f"Cannot disable '{adapter_name}' while it is connected to a Wi-Fi network.",
                code='WIFI_CONNECTED_DISABLE_FAILED'
            ) from e
        
        # Check for "already in state" error
        adapters = get_adapter_details()
        selected_adapter = next((a for a in adapters if a.get('Name') == adapter_name), None)
        if selected_adapter and selected_adapter.get('admin_state', '').lower() == action + 'd':
            raise NetworkManagerError(f"Adapter '{adapter_name}' is already {action}d.") from e

        raise NetworkManagerError(f"Failed to {action} adapter '{adapter_name}':\n{e}") from e
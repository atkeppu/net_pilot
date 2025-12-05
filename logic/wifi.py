import re
import json
import logging

from exceptions import NetworkManagerError
from .command_utils import run_system_command, run_ps_command

logger = logging.getLogger(__name__)

def list_wifi_networks() -> list[dict]:
    """Lists available Wi-Fi networks."""
    try:
        command = ['netsh', 'wlan', 'show', 'networks', 'mode=Bssid']
        netsh_output = run_system_command(command, "Failed to list Wi-Fi networks").stdout.decode('oem', errors='ignore')
        return _parse_netsh_wlan_output(netsh_output)
    except NetworkManagerError as e:
        if "no wireless interface" in str(e).lower():
            logger.warning("No wireless interface found while listing networks.")
            return []
        if "location permission" in str(e).lower():
            raise NetworkManagerError(
                "Location services must be enabled to scan for Wi-Fi networks.",
                code='LOCATION_PERMISSION_DENIED'
            ) from e
        raise

def _parse_netsh_wlan_output(output: str) -> list[dict]:
    """
    Parses the output of 'netsh wlan show networks mode=bssid' command.
    This version uses a single, more efficient regex to parse network blocks.
    """
    networks = []
    seen_ssids = set()

    # This regex captures all relevant details for each SSID block in one go.
    # It looks for SSID, Authentication, Encryption, and the first Signal strength found.
    pattern = re.compile(
        r"SSID \d+ : (.*?)\n"  # Capture SSID (non-greedy, can be empty)
        r".*?Authentication\s+: (.+?)\n"  # Capture Authentication
        r".*?Encryption\s+: (.+?)\n"  # Capture Encryption
        r"(?:.*?Signal\s+: (\d+)%)?",  # Optionally capture Signal
        re.DOTALL
    )

    for match in pattern.finditer(output):
        ssid, auth, enc, signal = (m.strip() if m else None for m in match.groups())

        # If SSID is empty or None, treat it as a hidden network.
        display_ssid = ssid if ssid else "(Hidden Network)"

        if display_ssid in seen_ssids:
            continue  # Skip if SSID is missing or already processed

        seen_ssids.add(display_ssid)
        networks.append({
            'ssid': display_ssid,
            'authentication': auth or "N/A",
            'encryption': enc or "N/A",
            'signal': signal or "N/A"
        })

    return networks

def get_current_wifi_details() -> dict | None:
    """Gets details of the current Wi-Fi connection."""
    logger.info("Entering get_current_wifi_details...")
    # This PowerShell script is more efficient and reliable than parsing netsh and ipconfig output.
    # It gets the active Wi-Fi adapter and its associated IP configuration in one go.
    ps_script = """
        $wifi = Get-NetAdapter -Physical | Where-Object { $_.InterfaceDescription -notlike "*Virtual*" -and $_.MediaType -eq "Native 802.11" -and $_.Status -eq "Up" } | Select-Object -First 1
        if ($null -eq $wifi) { exit }

        $ipConfig = $wifi | Get-NetIPConfiguration -Detailed
        $ssidInfo = netsh.exe wlan show interfaces | Select-String -Pattern "SSID", "Signal"

        $result = @{
            interface_name = $wifi.Name
            ssid = ($ssidInfo | Where-Object { $_.Line -like "*SSID*" } | ForEach-Object { ($_.Line -split ':', 2)[1].Trim() }) -join ""
            signal = ($ssidInfo | Where-Object { $_.Line -like "*Signal*" } | ForEach-Object { ($_.Line -split ':', 2)[1].Trim() }) -join ""
            ipv4 = ($ipConfig.IPv4Address.IPAddress | Select-Object -First 1)
        }
        $result | ConvertTo-Json
    """
    try:
        result_json = run_ps_command(ps_script)
        return json.loads(result_json) if result_json else None
    except (NetworkManagerError, json.JSONDecodeError):
        return None

def disconnect_wifi():
    """Disconnects from the current Wi-Fi network."""
    try:
        run_system_command(['netsh', 'wlan', 'disconnect'], "Failed to disconnect from Wi-Fi.")
    except NetworkManagerError as e:
        # It's not a critical error if the command fails because we're already disconnected.
        # We can log this for debugging but don't need to raise an exception.
        error_str = str(e).lower()
        if "not connected" in error_str or "ei ole yhteydessä" in error_str:
            logger.info("Attempted to disconnect, but no active Wi-Fi connection was found.")
        else:
            raise # Re-raise any other unexpected errors.

def get_saved_wifi_profiles() -> list[dict]:
    """Gets saved Wi-Fi profiles and their passwords."""
    # This PowerShell script is significantly faster than calling 'netsh' for each profile in a loop.
    # It gets all profiles and then extracts the key from each profile's XML content.
    ps_script = r"""
        $profiles = (netsh.exe wlan show profiles) | Select-String "All User Profile" | ForEach-Object { $_.Line.Split(':', 2)[1].Trim() }

        $result = foreach ($p in $profiles) {
            try {
                $profileXml = [xml](netsh.exe wlan show profile name="$p" key=clear)
                $password = $profileXml.WLANProfile.MSM.security.sharedKey.keyMaterial
                [PSCustomObject]@{
                    ssid     = $p
                    password = if ($password) { $password } else { "N/A" }
                }
            } catch {
                # This can happen if we don't have permissions for a profile or it has no key
                [PSCustomObject]@{
                    ssid     = $p
                    password = "(Password not stored or accessible)"
                }
            }
        }
        $result | ConvertTo-Json -Compress
    """
    try:
        result_json = run_ps_command(ps_script)
        return json.loads(result_json) if result_json else []
    except (NetworkManagerError, json.JSONDecodeError) as e:
        logger.error("Failed to get saved Wi-Fi profiles via PowerShell.", exc_info=True)
        raise NetworkManagerError(f"Could not retrieve saved Wi-Fi profiles: {e}") from e
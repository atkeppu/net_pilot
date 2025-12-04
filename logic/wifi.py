import subprocess
import re
import logging
import tempfile
import os

from exceptions import NetworkManagerError

logger = logging.getLogger(__name__)

def _run_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Helper to run a command and capture its output."""
    try:
        return subprocess.run(command, shell=False, check=check, capture_output=True, text=False, creationflags=subprocess.CREATE_NO_WINDOW)
    except FileNotFoundError as e:
        raise NetworkManagerError(f"Command '{command[0]}' not found. Is it in the system's PATH?") from e
    except subprocess.CalledProcessError as e:
        stdout = e.stdout.strip() if e.stdout else "None"
        stderr = e.stderr.strip() if e.stderr else "None"
        error_message = (f"Command failed: {' '.join(e.cmd)}\nReturn Code: {e.returncode}\nError Output: {stderr}\nStandard Output: {stdout}")
        raise NetworkManagerError(error_message) from e

def list_wifi_networks() -> list[dict]:
    """Lists available Wi-Fi networks."""
    try:
        netsh_output = _run_command(['netsh', 'wlan', 'show', 'networks', 'mode=Bssid']).stdout.decode('oem', errors='ignore')
        networks, current_network = [], {}
        ssid_pattern = re.compile(r"^\s*SSID \d+ : (.+)")
        auth_pattern = re.compile(r"^\s*Authentication\s+: (.+)")
        encr_pattern = re.compile(r"^\s*Encryption\s+: (.+)")
        signal_pattern = re.compile(r"^\s*Signal\s+: (\d+)%")

        for line in netsh_output.splitlines():
            ssid_match = ssid_pattern.match(line)
            if ssid_match:
                if current_network and 'ssid' in current_network and not any(n['ssid'] == current_network['ssid'] for n in networks):
                    networks.append(current_network)
                current_network = {'ssid': ssid_match.group(1).strip()}
                continue
            if not current_network: continue
            auth_match = auth_pattern.match(line)
            if auth_match:
                current_network['authentication'] = auth_match.group(1).strip()
                continue
            encr_match = encr_pattern.match(line)
            if encr_match:
                current_network['encryption'] = encr_match.group(1).strip()
                continue
            signal_match = signal_pattern.match(line)
            if signal_match and 'signal' not in current_network:
                current_network['signal'] = signal_match.group(1).strip()

        if current_network and 'ssid' in current_network and not any(n['ssid'] == current_network['ssid'] for n in networks):
            networks.append(current_network)
        return networks
    except NetworkManagerError as e:
        if "no wireless interface" in str(e).lower():
            logger.warning("No wireless interface found while listing networks.")
            return []
        raise

def get_current_wifi_details() -> dict | None:
    """Gets details of the current Wi-Fi connection."""
    try:
        netsh_output = _run_command(['netsh', 'wlan', 'show', 'interfaces']).stdout.decode('oem', errors='ignore')
        if "not connected" in netsh_output.lower(): return None
        details = {}
        
        ssid_match = re.search(r"SSID\s+: (.+)", netsh_output)
        details['ssid'] = ssid_match.group(1).strip() if ssid_match else "N/A"
        
        signal_match = re.search(r"Signal\s+: (\d+)%", netsh_output)
        details['signal'] = f"{signal_match.group(1)}%" if signal_match else "N/A"
        
        name_match = re.search(r"Name\s+: (.+)", netsh_output)
        details['interface_name'] = name_match.group(1).strip() if name_match else "N/A"
        
        ipconfig_output = _run_command(['ipconfig']).stdout.decode('oem', errors='ignore')
        interface_section = re.search(rf"Wireless LAN adapter {re.escape(details['interface_name'])}:(.*?)(?=\n\n|\Z)", ipconfig_output, re.DOTALL)
        if interface_section:
            ipv4_match = re.search(r"IPv4 Address. . . . . . . . . . . : ([\d\.]+)", interface_section.group(1))
            if ipv4_match:
                details['ipv4'] = ipv4_match.group(1)
        return details
    except NetworkManagerError:
        return None

def connect_to_wifi_network(ssid: str, password: str | None = None):
    """Connects to a Wi-Fi network."""
    if password:
        auth, encryption, key_type = "WPA2PSK", "AES", "passPhrase"
        key_material_xml = f"<sharedKey><keyType>{key_type}</keyType><protected>false</protected><keyMaterial>{password}</keyMaterial></sharedKey>"
    else:
        auth, encryption = "open", "none"
        key_material_xml = ""

    profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM><security>
        <authEncryption><authentication>{auth}</authentication><encryption>{encryption}</encryption><useOneX>false</useOneX></authEncryption>
        {key_material_xml}
    </security></MSM>
</WLANProfile>"""

    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.xml', encoding='utf-8') as tmpfile:
            tmpfile.write(profile_xml)
            profile_path = tmpfile.name
        _run_command(['netsh', 'wlan', 'add', 'profile', f'filename="{profile_path}"'])
        connect_with_profile_name(ssid)
    except NetworkManagerError as e:
        raise NetworkManagerError(f"Failed to create profile or connect to '{ssid}':\n{e}") from e
    finally:
        if 'profile_path' in locals() and profile_path and os.path.exists(profile_path):
            os.remove(profile_path)

def disconnect_wifi():
    """Disconnects from the current Wi-Fi network."""
    _run_command(['netsh', 'wlan', 'disconnect'])

def get_saved_wifi_profiles() -> list[dict]:
    """Gets saved Wi-Fi profiles and their passwords."""
    profiles_output = _run_command(['netsh', 'wlan', 'show', 'profiles']).stdout.decode('oem', errors='ignore')
    profile_names = re.findall(r"All User Profile\s+:\s(.+)", profiles_output)
    saved_profiles = []
    for name in profile_names:
        name = name.strip()
        password = "N/A"
        try:
            profile_detail_output = _run_command(['netsh', 'wlan', 'show', 'profile', f'name="{name}"', 'key=clear']).stdout.decode('oem', errors='ignore')
            password_match = re.search(r"Key Content\s+:\s(.+)", profile_detail_output)
            if password_match:
                password = password_match.group(1).strip()
        except NetworkManagerError:
            password = "(Password not stored or accessible)"
        saved_profiles.append({'ssid': name, 'password': password})
    return saved_profiles

def connect_with_profile_name(profile_name: str):
    """Connects to a Wi-Fi network using a saved profile name."""
    _run_command(['netsh', 'wlan', 'connect', f'name="{profile_name}"'])

def delete_wifi_profile(profile_name: str):
    """Deletes a saved Wi-Fi profile."""
    _run_command(['netsh', 'wlan', 'delete', 'profile', f'name="{profile_name}"'])
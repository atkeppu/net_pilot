import tempfile
import os
import logging

from exceptions import NetworkManagerError
from .command_utils import run_system_command

logger = logging.getLogger(__name__)

def _create_wlan_profile_xml(ssid: str, authentication: str, encryption: str, password: str | None) -> str:
    """
    Generates the XML content for a WLAN profile based on security settings.
    """
    # Map netsh output to WLAN profile XML values
    auth_map = {
        "WPA2-Personal": "WPA2PSK",
        "WPA3-Personal": "WPA3SAE",
        "WPA-Personal": "WPAPSK",
        "Open": "open",
        "WEP": "open"  # WEP uses 'open' for auth and key is handled separately
    }
    # Default to AES for modern standards, TKIP for legacy, or none for open
    enc_map = {"CCMP": "AES", "TKIP": "TKIP", "None": "none", "WEP": "WEP"}

    auth_xml = auth_map.get(authentication, "WPA2PSK")  # Default to WPA2PSK if unknown
    enc_xml = enc_map.get(encryption, "AES")

    if password:
        # WEP uses a different key structure
        key_type = "networkKey" if auth_xml == "open" and enc_xml == "WEP" else "passPhrase"
        key_material_xml = f"<sharedKey><keyType>{key_type}</keyType><protected>false</protected><keyMaterial>{password}</keyMaterial></sharedKey>"
    else:
        # Ensure settings are correct for an open network
        auth_xml = "open"
        enc_xml = "none"
        key_material_xml = ""

    return f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM><security>
        <authEncryption><authentication>{auth_xml}</authentication><encryption>{enc_xml}</encryption><useOneX>false</useOneX></authEncryption>
        {key_material_xml}
    </security></MSM>
</WLANProfile>"""

def connect_to_wifi_network(ssid: str, authentication: str, encryption: str, password: str | None = None):
    """
    Connects to a Wi-Fi network by dynamically creating a profile based on security settings.
    """
    profile_xml = _create_wlan_profile_xml(ssid, authentication, encryption, password)

    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.xml', encoding='utf-8') as tmpfile:
            tmpfile.write(profile_xml)
            profile_path = tmpfile.name
        add_command = ['netsh', 'wlan', 'add', 'profile', f'filename="{profile_path}"']
        run_system_command(add_command, f"Failed to add Wi-Fi profile for {ssid}")
        connect_with_profile_name(ssid)
    except NetworkManagerError as e:
        raise NetworkManagerError(f"Failed to create profile or connect to '{ssid}':\n{e}") from e
    finally:
        if 'profile_path' in locals() and profile_path and os.path.exists(profile_path):
            os.remove(profile_path)

def connect_with_profile_name(profile_name: str):
    """Connects to a Wi-Fi network using a saved profile name."""
    try:
        connect_cmd = ['netsh', 'wlan', 'connect', f'name="{profile_name}"']
        run_system_command(connect_cmd, f"Failed to connect using profile {profile_name}")
    except NetworkManagerError as e:
        error_str = str(e).lower()
        if "the network security key is not correct" in error_str:
            raise NetworkManagerError(
                f"Connection to '{profile_name}' failed: The password is incorrect.",
                code='WIFI_INVALID_KEY'
            ) from e
        # Add more specific checks here as they are discovered
        raise e  # Re-raise the original exception if no specific error is matched

def delete_wifi_profile(profile_name: str):
    """Deletes a saved Wi-Fi profile."""
    delete_cmd = ['netsh', 'wlan', 'delete', 'profile', f'name="{profile_name}"']
    run_system_command(delete_cmd, f"Failed to delete profile {profile_name}")
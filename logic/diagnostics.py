import subprocess
import re
import logging
import requests
import json

from exceptions import NetworkManagerError
from .command_utils import run_system_command, run_external_ps_script, run_ps_command

logger = logging.getLogger(__name__)

def get_network_diagnostics(external_target: str = "8.8.8.8") -> dict:
    """Gathers various network diagnostic details using native Python and system
    commands."""
    diagnostics = {
        "Public IP": "Error",
        "Gateway": "N/A",
        "Gateway Latency": "N/A",
        "External Latency": "N/A",
        "DNS Servers": "N/A",
    }

    # 1. Get Public IP using requests library (more reliable than Invoke-RestMethod)
    try:
        response = requests.get('https://api.ipify.org', timeout=2)
        response.raise_for_status()
        diagnostics["Public IP"] = response.text.strip()
    except requests.RequestException as e:
        logger.warning("Could not fetch public IP: %s", e)

    # 2. Get Gateway and DNS from ipconfig
    try:
        ipconfig_output = run_system_command(
            ['ipconfig', '/all'], "Failed to run ipconfig").stdout.decode('oem', errors='ignore')
        gateway_match = re.search(
            r"Default Gateway . . . . . . . . . : (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ipconfig_output)
        if gateway_match:
            diagnostics["Gateway"] = gateway_match.group(1)

        # Make regex bilingual to support both "DNS Servers" and "DNS-palvelimet"
        dns_matches = re.findall(
            r"DNS(?: Servers|-palvelimet) .*: ([\d\.\s]+)", ipconfig_output)
        if dns_matches:
            # Clean up and join all found DNS servers
            all_dns = [ip.strip() for dns_block in dns_matches for ip in dns_block.split(
                '\n') if ip.strip()]
            diagnostics["DNS Servers"] = ", ".join(all_dns)
    except NetworkManagerError as e:
        logger.warning("Could not parse ipconfig output: %s", e)

    # 3. Get Latencies using system ping
    def get_latency(target: str) -> str:
        if not target or target == "0.0.0.0":
            return "N/A"
        try:
            ping_output = run_system_command(
                ['ping', '-n', '1', '-w', '1000', target], "Ping failed").stdout.decode('oem', errors='ignore')
            match = re.search(r"Average = (\d+)ms", ping_output)
            return f"{match.group(1)} ms" if match else "No Response"
        except NetworkManagerError:
            return "No Response"

    diagnostics["Gateway Latency"] = get_latency(diagnostics["Gateway"])
    diagnostics["External Latency"] = get_latency(external_target)

    return diagnostics

def get_raw_network_stats() -> dict:
    """Gets raw network traffic stats (bytes sent/received) for all interfaces."""
    try:
        stats_json = run_external_ps_script('Get-RawNetworkStats.ps1')
        stats_list = json.loads(stats_json)
        if isinstance(stats_list, dict):
            stats_list = [stats_list]
        return {
            stat['Name']: {'received': stat.get('ReceivedBytes') or 0, 'sent': stat.get('SentBytes') or 0}
            for stat in stats_list if isinstance(stat, dict) and 'Name' in stat
        }
    except (NetworkManagerError, json.JSONDecodeError) as e:
        logger.error("Failed to get raw network stats: %s", e)
        return {}

def get_active_connections() -> list[dict]:
    """Gets a list of active network connections using a single, efficient PowerShell command."""
    try:  # noqa: E501
        result_json = run_external_ps_script('Get-ActiveConnections.ps1')
        raw_data = json.loads(result_json)
        return raw_data if isinstance(raw_data, list) else ([
            raw_data] if raw_data else [])
    except (NetworkManagerError, json.JSONDecodeError) as e:
        logger.error("get_active_connections failed", exc_info=True)
        raise NetworkManagerError(
            f"Failed to get active connections via PowerShell: {e}") from e

def run_traceroute(target: str):
    """Runs a traceroute command and yields each line of output."""
    # Basic input validation to prevent command injection vulnerabilities.
    if not re.match(r"^[a-zA-Z0-9\.\-:]+$", target):
        raise NetworkManagerError(
            "Invalid target specified. Only hostnames and IP addresses are allowed.")

    # This PowerShell script streams the output of Test-NetConnection -TraceRoute
    # in a format similar to the classic tracert tool.
    ps_script = f"""
        $ProgressPreference = 'SilentlyContinue'
        Test-NetConnection -ComputerName '{target}' -TraceRoute
    """
    try:
        # We cannot use run_ps_command directly as it doesn't stream.
        # Instead, we use run_system_command's underlying Popen mechanism.
        # This is a special case where we need live output.
        for line in run_ps_command(ps_script, stream_output=True):
            yield line
    except NetworkManagerError as e:
        # Re-raise to propagate the error from the command execution.
        raise
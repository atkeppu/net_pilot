import subprocess
import re
import logging
import json
import base64
from urllib import request, error

from exceptions import NetworkManagerError

logger = logging.getLogger(__name__)

def _run_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Helper to run a command and capture its output."""
    try:
        return subprocess.run(command, shell=False, check=check, capture_output=True, text=False)
    except FileNotFoundError as e:
        raise NetworkManagerError(f"Command '{command[0]}' not found. Is it in the system's PATH?") from e
    except subprocess.CalledProcessError as e:
        stdout = e.stdout.strip() if e.stdout else "None"
        stderr = e.stderr.strip() if e.stderr else "None"
        error_message = (f"Command failed: {' '.join(e.cmd)}\nReturn Code: {e.returncode}\nError Output: {stderr}\nStandard Output: {stdout}")
        raise NetworkManagerError(error_message) from e

def _run_ps_command(script: str) -> str:
    """Runs a PowerShell script safely using -EncodedCommand."""
    try:
        encoded_script = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        command = ['powershell', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', encoded_script]
        result = subprocess.run(command, shell=False, check=True, capture_output=True)
        return result.stdout.decode('utf-8', errors='ignore')
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise NetworkManagerError(f"PowerShell command failed: {e}") from e

def get_network_diagnostics(external_target: str = "8.8.8.8") -> dict:
    """Gathers various network diagnostic details."""
    diagnostics = {"Public IP": "N/A", "Gateway": "N/A", "Gateway Latency": "N/A", "External Latency": "N/A", "DNS Servers": "N/A"}
    try:
        diagnostics["Public IP"] = request.urlopen('https://api.ipify.org', timeout=3).read().decode('utf-8')
    except error.URLError:
        diagnostics["Public IP"] = "Error"

    try:
        ipconfig_output = _run_command(['ipconfig', '/all']).stdout.decode('oem', errors='ignore')
        gateway_match = re.search(r"Default Gateway.*: ([\d\.]+)", ipconfig_output)
        if gateway_match:
            diagnostics["Gateway"] = gateway_match.group(1)
        dns_matches = re.findall(r"DNS Servers.*: ([\d\.\s]+)", ipconfig_output)
        if dns_matches:
            diagnostics["DNS Servers"] = ", ".join(re.findall(r'[\d\.]+', "".join(dns_matches)))
    except NetworkManagerError:
        pass

    if diagnostics["Gateway"] != "N/A":
        try:
            ping_output = _run_command(['ping', '-n', '1', '-w', '1000', diagnostics["Gateway"]]).stdout.decode('oem', errors='ignore')
            latency_match = re.search(r"Average = (\d+)ms", ping_output)
            diagnostics["Gateway Latency"] = f"{latency_match.group(1)} ms" if latency_match else "Timeout"
        except NetworkManagerError:
            diagnostics["Gateway Latency"] = "Error"

    try:
        ping_output = _run_command(['ping', '-n', '1', '-w', '1000', external_target]).stdout.decode('oem', errors='ignore')
        latency_match = re.search(r"Average = (\d+)ms", ping_output)
        diagnostics["External Latency"] = f"{latency_match.group(1)} ms" if latency_match else "Timeout"
    except NetworkManagerError:
        diagnostics["External Latency"] = "Error"

    return diagnostics

def get_raw_network_stats() -> dict:
    """Gets raw network traffic stats (bytes sent/received) for all interfaces."""
    ps_script = (
        "Get-NetAdapter -IncludeHidden | ForEach-Object { "
        "  $stats = Get-NetAdapterStatistics -Name $_.Name; "
        "  [PSCustomObject]@{ "
        "    Name = $_.Name; "
        "    ReceivedBytes = $stats.ReceivedBytes; "
        "    SentBytes = $stats.SentBytes "
        "  } "
        "} | ConvertTo-Json"
    )
    try:
        stats_json = _run_ps_command(ps_script)
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
    try:
        ps_script = (
            "$procs = @{}; Get-CimInstance Win32_Process | ForEach-Object { $procs[$_.ProcessId] = $_.Name };"
            "$procs[0] = 'System Idle'; $procs[4] = 'System';"
            "$tcp = Get-NetTCPConnection | Select-Object @{N='Proto';E={'TCP'}},@{N='Local';E={-join($_.LocalAddress,':',$_.LocalPort)}},@{N='Foreign';E={-join($_.RemoteAddress,':',$_.RemotePort)}},State,@{N='PID';E={$_.OwningProcess}},@{N='ProcessName';E={$procs[$_.OwningProcess]}};"
            "$udp = Get-NetUDPEndpoint | Select-Object @{N='Proto';E={'UDP'}},@{N='Local';E={-join($_.LocalAddress,':',$_.LocalPort)}},@{N='Foreign';E={'*:*'}},@{N='State';E={'N/A'}},@{N='PID';E={$_.OwningProcess}},@{N='ProcessName';E={$procs[$_.OwningProcess]}};"
            "($tcp + $udp) | Where-Object { $_.PID -ne $null } | ConvertTo-Json -Compress"
        )
        result_json = _run_ps_command(ps_script)
        raw_data = json.loads(result_json)
        return raw_data if isinstance(raw_data, list) else [raw_data]
    except (NetworkManagerError, json.JSONDecodeError) as e:
        logger.error("get_active_connections failed", exc_info=True)
        raise NetworkManagerError(f"Failed to get active connections via PowerShell: {e}") from e

def run_traceroute(target: str):
    """Runs a traceroute command and yields each line of output."""
    command = ['tracert', '-d', target]
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='oem', shell=False)
        for line in iter(process.stdout.readline, ''):
            yield line.strip()
        process.stdout.close()
        return_code = process.wait()
        if return_code != 0:
            yield f"\nTraceroute finished with error code: {return_code}"
    except FileNotFoundError as e:
        raise NetworkManagerError(f"Command '{command[0]}' not found.") from e
param(
    [string]$ExternalTarget = "8.8.8.8"
)

# Get public IP
$publicIp = try { (Invoke-RestMethod -Uri 'https://api.ipify.org' -TimeoutSec 3) } catch { "Error" }

# Get network configuration details for the primary adapter
$netConfig = Get-NetIPConfiguration | Select-Object -First 1
$gateway = $netConfig.IPv4DefaultGateway
$dnsServers = $netConfig.DNSServer

# Ping gateway and external target
$gatewayLatency = "N/A"
if ($gateway) {
    $pingResult = Test-NetConnection -ComputerName $gateway -Count 1 -ErrorAction SilentlyContinue
    if ($pingResult.PingSucceeded) { $gatewayLatency = "$($pingResult.PingReplyDetails.RoundtripTime) ms" } else { $gatewayLatency = "Timeout" }
}

$externalLatency = "N/A"
if ($ExternalTarget) {
    $pingResult = Test-NetConnection -ComputerName $ExternalTarget -Count 1 -ErrorAction SilentlyContinue
    if ($pingResult.PingSucceeded) { $externalLatency = "$($pingResult.PingReplyDetails.RoundtripTime) ms" } else { $externalLatency = "Timeout" }
}

# Construct the result object
[PSCustomObject]@{
    "Public IP" = $publicIp
    "Gateway" = $gateway
    "Gateway Latency" = $gatewayLatency
    "External Latency" = $externalLatency
    "DNS Servers" = ($dnsServers | Out-String).Trim() # Convert array to string
} | ConvertTo-Json -Compress
# Get public IP
$publicIp = try { (Invoke-RestMethod -Uri 'https://api.ipify.org' -TimeoutSec 1) } catch { "Error" }

# Get network configuration details for the primary adapter
$netConfig = Get-NetIPConfiguration | Select-Object -First 1
# Extract the actual IP address string from the gateway object
$gatewayIp = $netConfig.IPv4DefaultGateway.NextHop
# Extract the IP addresses from the DNS server objects and join them into a single string
$dnsServerIps = ($netConfig.DNSServer.ServerAddresses | Where-Object {$_}) -join ', '

# Ping gateway and external target
$gatewayLatency = "N/A"
if ($gatewayIp) {
    # Force an ICMP ping test for accurate latency measurement.
    $pingTest = Test-NetConnection -ComputerName $gatewayIp -ConstrainInterface $netConfig.InterfaceIndex -ErrorAction SilentlyContinue
    if ($pingTest.PingSucceeded) {
        $gatewayLatency = "$($pingTest.PingReplyDetails.RoundtripTime) ms"
    } else {
        $gatewayLatency = "No Response"
    }
}

$externalLatency = "N/A"
if ($external_target) {
    # First, try a standard ICMP ping to get accurate latency.
    $pingTest = Test-NetConnection -ComputerName $external_target -ConstrainInterface $netConfig.InterfaceIndex -ErrorAction SilentlyContinue
    if ($pingTest.PingSucceeded) {
        $externalLatency = "$($pingTest.PingReplyDetails.RoundtripTime) ms"
    } else {
        $externalLatency = "No Response"
    }
}

# Construct the result object
[PSCustomObject]@{
    "Public IP"        = $publicIp
    "Gateway"          = $gatewayIp
    "Gateway Latency"  = $gatewayLatency
    "External Latency" = $externalLatency
    "DNS Servers"      = $dnsServerIps
} | ConvertTo-Json -Compress
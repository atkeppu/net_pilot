# Get process names for PID lookup
$procs = @{}
Get-CimInstance Win32_Process | ForEach-Object { $procs[$_.ProcessId] = $_.Name }
$procs[0] = 'System Idle'
$procs[4] = 'System'

# Get TCP connections
$tcp = Get-NetTCPConnection | Select-Object @{N='Proto';E={'TCP'}},
                               @{N='Local';E={-join($_.LocalAddress,':',$_.LocalPort)}},
                               @{N='Foreign';E={-join($_.RemoteAddress,':',$_.RemotePort)}},
                               State,
                               @{N='PID';E={$_.OwningProcess}},
                               @{N='ProcessName';E={$procs[$_.OwningProcess]}}

# Get UDP endpoints
$udp = Get-NetUDPEndpoint | Select-Object @{N='Proto';E={'UDP'}},
                               @{N='Local';E={-join($_.LocalAddress,':',$_.LocalPort)}},
                               @{N='Foreign';E={'*:*'}},
                               @{N='State';E={'N/A'}},
                               @{N='PID';E={$_.OwningProcess}},
                               @{N='ProcessName';E={$procs[$_.OwningProcess]}}

# Combine and filter out connections without a PID (e.g., system-level)
($tcp + $udp) | Where-Object { $_.PID -ne $null } | ConvertTo-Json -Compress
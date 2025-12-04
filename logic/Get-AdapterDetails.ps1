# Using Get-CimInstance is often more reliable for finding all physical adapters.
$adapters = Get-CimInstance -Class Win32_NetworkAdapter -Filter "PhysicalAdapter = TRUE"
 
 $results = foreach ($adapter in $adapters) {
     # Find the corresponding NetAdapter. If not found, skip to the next one.
     $netAdapter = Get-NetAdapter -InterfaceDescription $adapter.Description
 
     if ($netAdapter) {
         $ipConfig = $netAdapter | Get-NetIPConfiguration -All -ErrorAction SilentlyContinue
         $driver = $netAdapter | Get-NetAdapterHardwareInfo -ErrorAction SilentlyContinue
 
         [PSCustomObject]@{
             Name                 = $netAdapter.Name
             InterfaceDescription = $adapter.Description
             MacAddress           = $adapter.MACAddress
             LinkSpeed            = $netAdapter.LinkSpeed
             NetConnectionStatus  = $adapter.NetConnectionStatus
             IPv4Address          = ($ipConfig.IPv4Address.IPAddress | Select-Object -First 1)
             IPv6Address          = ($ipConfig.IPv6Address.IPAddress | Select-Object -First 1)
             DriverVersion        = ($driver.DriverVersion | Select-Object -First 1)
             DriverDate           = ($driver.DriverDate | Select-Object -First 1)
         }
     }
 }
 $results | ConvertTo-Json -Compress
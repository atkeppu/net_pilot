<#
.SYNOPSIS
    Retrieves detailed information about all physical network adapters.

.DESCRIPTION
    This script queries the system for all physical network adapters using WMI/CIM.
    For each adapter, it gathers additional details like IP configuration and driver information.
    The final output is a JSON array of objects, each representing an adapter.

.OUTPUTS
    System.String
    A JSON formatted string containing the details of all physical network adapters.
    Returns an empty JSON array '[]' if no adapters are found.
#>

# Helper function to safely extract the first item from a property collection.
# This avoids errors if the property is null or empty, and reduces code repetition (DRY principle).
function Get-SafeProperty {
    param(
        [Parameter(Mandatory=$true, ValueFromPipeline=$true)]
        $InputObject
    )
    # Select the first object from the pipeline, returning $null if the pipeline is empty.
    $InputObject | Select-Object -First 1
}

try {
    # Get-CimInstance is a modern and efficient way to query WMI.
    # We filter for physical adapters to exclude virtual ones.
    $physicalAdapters = Get-CimInstance -Class Win32_NetworkAdapter -Filter "PhysicalAdapter = TRUE" -ErrorAction Stop

    $adapterDetails = foreach ($adapter in $physicalAdapters) {
        try {
            # Find the corresponding NetAdapter to get more details.
            # If not found, an exception is thrown and caught, and we move to the next adapter.
            $netAdapter = Get-NetAdapter -InterfaceDescription $adapter.Description -ErrorAction Stop

            # Retrieve IP configuration and hardware info.
            # Using variables makes the code cleaner and easier to debug.
            # SilentlyContinue is used because a failure here should not stop processing the adapter.
            $ipConfig = $netAdapter | Get-NetIPConfiguration -All -ErrorAction SilentlyContinue
            if (-not $ipConfig) {
                Write-Warning "Could not retrieve IP configuration for adapter '$($netAdapter.Name)'."
            }

            $driverInfo = $netAdapter | Get-NetAdapterHardwareInfo -ErrorAction SilentlyContinue
            if (-not $driverInfo) {
                Write-Warning "Could not retrieve driver information for adapter '$($netAdapter.Name)'."
            }

            # Construct a custom object with the collected details.
            # Provide default null values for properties that might not exist to ensure consistent object structure.
            [PSCustomObject]@{
                Name                 = $netAdapter.Name
                InterfaceDescription = $adapter.Description
                MacAddress           = $adapter.MACAddress
                LinkSpeed            = $netAdapter.LinkSpeed
                NetConnectionStatus  = $adapter.NetConnectionStatus
                IPv4Address          = $ipConfig.IPv4Address.IPAddress | Get-SafeProperty
                IPv6Address          = $ipConfig.IPv6Address.IPAddress | Get-SafeProperty
                DriverVersion        = $driverInfo.DriverVersion | Get-SafeProperty
                DriverDate           = $driverInfo.DriverDate | Get-SafeProperty
            }
        }
        catch {
            # Log or handle the error if a specific adapter's details can't be retrieved.
            # For now, we just continue to the next adapter silently.
            Write-Warning "Could not retrieve full details for adapter with description: $($adapter.Description). Error: $($_.Exception.Message)"
        }
    }

    # Convert the final array of objects to a compressed JSON string.
    # The -Depth parameter ensures that nested objects are fully serialized.
    $adapterDetails | ConvertTo-Json -Compress -Depth 3
}
catch {
    # If the initial query for adapters fails, output an empty JSON array.
    Write-Error "Failed to retrieve network adapters. Error: $($_.Exception.Message)"
    "[]" | ConvertTo-Json
}
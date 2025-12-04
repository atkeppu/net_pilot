Get-NetAdapter -IncludeHidden | ForEach-Object {
  $stats = Get-NetAdapterStatistics -Name $_.Name -ErrorAction SilentlyContinue;
  [PSCustomObject]@{
    Name = $_.Name;
    ReceivedBytes = $stats.ReceivedBytes;
    SentBytes = $stats.SentBytes
  }
} | ConvertTo-Json -Compress
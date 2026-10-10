param([Parameter(Mandatory = $true)][string]$Address)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$apiDir = Join-Path $repo 'backend/SolarTrading.Api'
$privateDir = Join-Path $repo '.tools'
$dotnet = Join-Path $privateDir 'dotnet/dotnet.exe'
$dll = Join-Path $apiDir 'bin/Release/net10.0/SolarTrading.Api.dll'
if (!(Test-Path $dll)) { throw 'Build the Release API first using scripts/start-local.ps1.' }
$adapter = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $Address -ErrorAction Stop |
    Where-Object { $_.IPAddress -ne '127.0.0.1' } | Select-Object -First 1
if (!$adapter) { throw 'Choose an IPv4 address assigned to this laptop.' }
$listeners = @(Get-NetTCPConnection -State Listen -LocalPort 5080 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique)
$processes = @()
foreach ($processId in $listeners) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
    if (!$process.CommandLine -or $process.CommandLine.IndexOf($apiDir, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw 'Port 5080 belongs to another application; no process was stopped.'
    }
    $processes += $process
}

# Permit only the local subnet, on this interface and address, for this API executable/port.
# Administrator rights are required to add the Windows firewall rule.
$ruleName = 'Solara-SharedDemo-5080'
$rule = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if ($rule -and $rule.Description -ne 'Managed by Solara start-shared-backend.ps1') {
    throw 'An unrelated firewall rule has the same name; it was left unchanged.'
}
if ($rule) { Remove-NetFirewallRule -Name $ruleName }
New-NetFirewallRule -Name $ruleName -DisplayName 'Solara API for phones on the local Wi-Fi' `
    -Description 'Managed by Solara start-shared-backend.ps1' -Direction Inbound -Action Allow `
    -Protocol TCP -LocalPort 5080 -LocalAddress $Address -RemoteAddress LocalSubnet `
    -InterfaceAlias $adapter.InterfaceAlias -Profile Any -Program $dotnet | Out-Null

foreach ($process in $processes) {
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($process.ParentProcessId)" -ErrorAction SilentlyContinue
    if ($parent.CommandLine -and $parent.CommandLine.IndexOf($apiDir, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
        Stop-Process -Id $parent.ProcessId -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
}
$env:DOTNET_CLI_HOME = Join-Path $privateDir 'cli'
$env:ASPNETCORE_ENVIRONMENT = 'Development'
$urls = 'http://127.0.0.1:5080;http://' + $Address + ':5080'
$api = Start-Process -FilePath $dotnet -ArgumentList @(('"' + $dll + '"'), '--urls', ('"' + $urls + '"')) `
    -WorkingDirectory $apiDir -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $privateDir 'api-output.log') `
    -RedirectStandardError (Join-Path $privateDir 'api-error.log')
[IO.File]::WriteAllText((Join-Path $privateDir 'api.pid'), $api.Id.ToString())
$deadline = [DateTime]::UtcNow.AddSeconds(30)
do {
    try {
        $health = Invoke-RestMethod ('http://' + $Address + ':5080/api/health') -TimeoutSec 2
        if ($health.status -eq 'healthy' -and $health.database -eq 'connected') {
            Write-Output ('Shared API ready: http://' + $Address + ':5080/api')
            Write-Output 'Set both phones to this server. USB may continue using http://127.0.0.1:5080/api.'
            exit 0
        }
    } catch { Start-Sleep -Milliseconds 500 }
} while (!$api.HasExited -and [DateTime]::UtcNow -lt $deadline)
throw 'Shared API did not become healthy. Inspect .tools/api-output.log and .tools/api-error.log.'

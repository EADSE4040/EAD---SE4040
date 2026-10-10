$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$resultPath = Join-Path $repo '.tools/iis-config-sync-result.json'
$manager = $null
$committed = $false
$previous = @{}
try {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this script from administrator Windows PowerShell.'
    }
    $base = Get-Content (Join-Path $repo 'backend/SolarTrading.Api/appsettings.json') -Raw | ConvertFrom-Json
    $local = Get-Content (Join-Path $repo 'backend/SolarTrading.Api/appsettings.Local.json') -Raw | ConvertFrom-Json
    if (!$local.Mongo.ConnectionString -or !$local.Jwt.Key -or !$local.Qr.Key) { throw 'Source API configuration is incomplete.' }
    $database = if ($local.Mongo.Database) { $local.Mongo.Database } else { $base.Mongo.Database }
    $settings = @{
        'Mongo__ConnectionString' = $local.Mongo.ConnectionString
        'Mongo__Database' = $database
        'Jwt__Key' = $local.Jwt.Key
        'Qr__Key' = $local.Qr.Key
        'Jwt__Issuer' = $(if ($local.Jwt.Issuer) { $local.Jwt.Issuer } else { $base.Jwt.Issuer })
        'Jwt__Audience' = $(if ($local.Jwt.Audience) { $local.Jwt.Audience } else { $base.Jwt.Audience })
    }
    Add-Type -Path "$env:windir/System32/inetsrv/Microsoft.Web.Administration.dll"
    $manager = New-Object Microsoft.Web.Administration.ServerManager
    $pool = $manager.ApplicationPools | Where-Object Name -eq 'SolaraApi' | Select-Object -First 1
    if (!$pool) { throw 'Existing SolaraApi IIS application pool was not found.' }
    $variables = $pool.GetCollection('environmentVariables')
    # Keep an ignored private rollback record; never print secrets or connection strings.
    foreach ($name in $settings.Keys) {
        $entry = $variables | Where-Object { $_.GetAttributeValue('name') -eq $name } | Select-Object -First 1
        $previous[$name] = @{ Exists = ($null -ne $entry); Value = $(if ($entry) { $entry.GetAttributeValue('value') } else { $null }) }
        if (!$entry) {
            $entry = $variables.CreateElement('add')
            $entry['name'] = $name
            $entry['value'] = [string]$settings[$name]
            $variables.Add($entry)
        } else { $entry['value'] = [string]$settings[$name] }
    }
    $backupPath = Join-Path $repo ('.tools/iis-config-backup-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss') + '.json')
    $previous | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $backupPath
    $manager.CommitChanges()
    $committed = $true
    $pool.Recycle() | Out-Null
    $manager.Dispose(); $manager = $null
    $healthy = $false
    for ($attempt = 0; $attempt -lt 12; $attempt++) {
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:8080/api/health' -TimeoutSec 10
            if ($health.status -eq 'healthy' -and $health.database -eq 'connected') { $healthy = $true; break }
        } catch { }
        Start-Sleep -Seconds 2
    }
    if (!$healthy) { throw 'IIS API did not become healthy after configuration sync.' }
    @{ success = $true; completedUtc = [DateTime]::UtcNow.ToString('o'); databaseHost = ([uri]$local.Mongo.ConnectionString).Host; database = $database; rollbackBackup = $backupPath } |
        ConvertTo-Json | Set-Content -LiteralPath $resultPath
    Write-Output 'IIS API now uses the source API database and signing configuration. Health check passed.'
} catch {
    $failure = $_.Exception.Message
    if ($manager) { $manager.Dispose(); $manager = $null }
    if ($committed) {
        try {
            $manager = New-Object Microsoft.Web.Administration.ServerManager
            $pool = $manager.ApplicationPools | Where-Object Name -eq 'SolaraApi' | Select-Object -First 1
            $variables = $pool.GetCollection('environmentVariables')
            foreach ($name in $previous.Keys) {
                $entry = $variables | Where-Object { $_.GetAttributeValue('name') -eq $name } | Select-Object -First 1
                if ($previous[$name].Exists) { $entry['value'] = [string]$previous[$name].Value }
                elseif ($entry) { $variables.Remove($entry) }
            }
            $manager.CommitChanges(); $pool.Recycle() | Out-Null
            $failure += ' Previous configuration restored.'
        } catch { $failure += ' Automatic rollback failed; use the private backup.' }
    }
    @{ success = $false; error = $failure; completedUtc = [DateTime]::UtcNow.ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath $resultPath
    Write-Error $failure -ErrorAction Continue
    exit 1
} finally { if ($manager) { $manager.Dispose() } }

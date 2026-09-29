# Run the reviewed IIS installer with an audit log; launched through Windows UAC.
$repo=Split-Path $PSScriptRoot -Parent
$log=Join-Path $repo '.tools/iis-setup.log'
$result=Join-Path $repo '.tools/iis-setup-result.json'
$ErrorActionPreference='Stop'
Start-Transcript -Path $log -Force | Out-Null
try {
    & (Join-Path $PSScriptRoot 'setup-iis.ps1')
    @{success=$true;completedUtc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $result
} catch {
    @{success=$false;message=$_.Exception.Message;completedUtc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $result
    Write-Error $_ -ErrorAction Continue
    exit 1
} finally { Stop-Transcript | Out-Null }

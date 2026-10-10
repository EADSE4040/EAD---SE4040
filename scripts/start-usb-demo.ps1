param([string]$Serial, [switch]$Stop)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$privateDir = Join-Path $repo '.tools'
New-Item -ItemType Directory -Path $privateDir -Force | Out-Null
$stateFile = Join-Path $privateDir 'usb-demo-watcher.json'
$watcher = $null
if (Test-Path -LiteralPath $stateFile) {
    $saved = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    $candidate = Get-Process -Id $saved.ProcessId -ErrorAction SilentlyContinue
    if ($candidate -and $candidate.ProcessName -eq 'powershell' -and
        $candidate.StartTime.ToUniversalTime().Ticks.ToString() -eq $saved.StartTicks) {
        $watcher = $candidate
    }
}
if ($Stop) {
    if ($watcher) { Stop-Process -Id $watcher.Id; Write-Output 'USB reconnect watcher stopped.' }
    else { Write-Output 'USB reconnect watcher is not running.' }
    exit
}
if ($watcher) { Write-Output 'USB reconnect watcher is already running.'; exit }
$helper = Join-Path $PSScriptRoot 'connect-android-usb.ps1'
$arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $helper + '"'), '-Watch')
if ($Serial) {
    if ($Serial -notmatch '^[a-zA-Z0-9._:-]+$') { throw 'Invalid ADB serial.' }
    $arguments += @('-Serial', $Serial)
}
$process = Start-Process -FilePath "$env:windir/System32/WindowsPowerShell/v1.0/powershell.exe" `
    -ArgumentList $arguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $privateDir 'usb-demo-watcher.log') `
    -RedirectStandardError (Join-Path $privateDir 'usb-demo-watcher-error.log')
@{ ProcessId = $process.Id; StartTicks = $process.StartTime.ToUniversalTime().Ticks.ToString() } |
    ConvertTo-Json | Set-Content -LiteralPath $stateFile
Write-Output 'USB reconnect watcher started. Keep IIS/MongoDB running and the phone authorized for USB debugging.'

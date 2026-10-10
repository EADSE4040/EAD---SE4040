param([switch]$Disable)
$ErrorActionPreference = 'Stop'
# Register this user's watcher at Windows sign-in; no administrator or system-wide changes.
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$name = 'SolaraUsbDemo'
if ($Disable) {
    Remove-ItemProperty -LiteralPath $runKey -Name $name -ErrorAction SilentlyContinue
    & (Join-Path $PSScriptRoot 'start-usb-demo.ps1') -Stop
    Write-Output 'Solara USB demo autostart disabled.'
    exit
}
$launcher = Join-Path $PSScriptRoot 'start-usb-demo.ps1'
$powershell = "$env:windir/System32/WindowsPowerShell/v1.0/powershell.exe"
$command = '"' + $powershell + '" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $launcher + '"'
New-Item -Path $runKey -Force | Out-Null
New-ItemProperty -LiteralPath $runKey -Name $name -PropertyType String -Value $command -Force | Out-Null
& $launcher
Write-Output 'Solara USB reconnect watcher will start automatically at Windows sign-in.'

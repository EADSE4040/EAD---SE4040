param([string]$Serial, [switch]$Watch)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $repo '.tools/android-sdk/platform-tools/adb.exe'
if (!(Test-Path -LiteralPath $adb)) {
    $adb = (Get-Command adb -ErrorAction Stop).Source
}

# Restore only the demo port after a cable reconnect or ADB restart.
if ($Watch) {
    $lastState = ''
    while ($true) {
        $rows = @(& $adb devices 2>$null)
        $phones = @($rows | Where-Object { $_ -match '^\S+\s+device\s*$' -and $_ -notmatch '^emulator-' } | ForEach-Object { ($_ -split '\s+')[0] })
        if ($Serial) { $phones = @($phones | Where-Object { $_ -eq $Serial }) }
        $state = 'Waiting for an authorized USB phone.'
        if ($phones.Count -gt 1) {
            $state = 'Several phones are attached. Restart the helper with -Serial to choose one.'
        } elseif ($phones.Count -eq 1) {
            $phone = $phones[0]
            $rules = @(& $adb -s $phone reverse --list 2>$null)
            if (!($rules -match '\s+tcp:8080\s+tcp:8080\s*$')) {
                & $adb -s $phone reverse tcp:8080 tcp:8080 2>$null | Out-Null
                if ($LASTEXITCODE -ne 0) { $state = 'USB forwarding failed; waiting to retry.' }
                else { $state = "USB forwarding restored for $phone." }
            } else { $state = "USB forwarding ready for $phone." }
        }
        if ($state -ne $lastState) {
            Write-Output ("{0:u} {1}" -f (Get-Date), $state)
            $lastState = $state
        }
        Start-Sleep -Seconds 3
    }
}

# Select an authorized physical device; require an explicit choice if several are attached.
$devices = @(& $adb devices)
if ($LASTEXITCODE -ne 0) { throw 'ADB could not list devices.' }
$connected = @($devices | Where-Object { $_ -match '^\S+\s+device\s*$' -and $_ -notmatch '^emulator-' } | ForEach-Object { ($_ -split '\s+')[0] })
if (!$Serial) {
    if ($connected.Count -ne 1) { throw 'Connect and authorize one physical phone, or specify -Serial.' }
    $Serial = $connected[0]
}
if ($Serial -notin $connected) { throw 'The selected phone is not connected and authorized for USB debugging.' }

# Check the assessed IIS service before forwarding the phone's localhost over USB.
$health = Invoke-RestMethod 'http://127.0.0.1:8080/api/health' -TimeoutSec 15
if ($health.status -ne 'healthy' -or $health.database -ne 'connected') { throw 'IIS API or MongoDB is unhealthy.' }
& $adb -s $Serial reverse tcp:8080 tcp:8080
if ($LASTEXITCODE -ne 0) { throw 'USB port forwarding failed.' }
& $adb -s $Serial shell am start -S -n 'com.solara.microgrid/.MainActivity' --es solara_usb_api 'http://127.0.0.1:8080/api'
if ($LASTEXITCODE -ne 0) { throw 'Install the Solara debug APK on this phone first.' }
Write-Output 'USB IIS connection ready. The current debug app saves http://127.0.0.1:8080/api automatically.'
Write-Output 'Run scripts/start-usb-demo.ps1 to keep forwarding restored automatically after reconnects.'
Write-Output 'This local HTTP setup requires the debug APK; release builds require HTTPS.'

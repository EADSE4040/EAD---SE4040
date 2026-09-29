param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'

$repo = Split-Path $PSScriptRoot -Parent
$jdk = Get-ChildItem (Join-Path $repo '.tools/jdk') -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName 'bin/java.exe') } |
    Select-Object -First 1
if (!$jdk) { throw 'Java 17 is missing from .tools/jdk. Run the environment setup first.' }

$env:JAVA_HOME = $jdk.FullName
$env:Path = (Join-Path $env:JAVA_HOME 'bin') + [IO.Path]::PathSeparator + $env:Path
$env:ANDROID_HOME = Join-Path $repo '.tools/android-sdk'
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:ANDROID_AVD_HOME = Join-Path $repo '.tools/android-avd'
$env:GRADLE_USER_HOME = Join-Path $repo '.tools/gradle-cache'

$adb = Join-Path $env:ANDROID_HOME 'platform-tools/adb.exe'
if (!(Test-Path -LiteralPath $adb)) { throw 'Android SDK platform-tools are missing.' }
$gradle = Join-Path $repo '.tools/gradle/gradle-8.13/bin/gradle.bat'
if (!(Test-Path -LiteralPath $gradle)) { throw 'Workspace Gradle 8.13 is missing.' }

& (Join-Path $PSScriptRoot 'start-android-emulator.ps1') -ShowWindow

Write-Output 'Waiting for the Android emulator to finish booting...'
$deadline = (Get-Date).AddMinutes(3)
do {
    Start-Sleep -Seconds 2
    $booted = (& $adb shell getprop sys.boot_completed 2>$null).Trim()
} until ($booted -eq '1' -or (Get-Date) -ge $deadline)
if ($booted -ne '1') { throw 'The emulator did not finish booting within three minutes.' }

if (!$SkipBuild) {
    Push-Location (Join-Path $repo 'frontend/android')
    try {
        & $gradle --no-daemon installDebug
        if ($LASTEXITCODE -ne 0) { throw 'Android build or installation failed.' }
    }
    finally { Pop-Location }
}

& $adb shell am start -n 'com.solara.microgrid/.MainActivity' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Solara could not be opened in the emulator.' }
Write-Output 'Solara is running. Emulator API URL: http://10.0.2.2:8080/api'

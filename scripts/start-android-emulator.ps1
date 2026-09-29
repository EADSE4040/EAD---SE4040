param([switch]$ShowWindow, [string]$CameraImage)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$env:ANDROID_HOME=Join-Path $repo '.tools/android-sdk'
$env:ANDROID_SDK_ROOT=$env:ANDROID_HOME
$env:ANDROID_AVD_HOME=Join-Path $repo '.tools/android-avd'
$emulator=Join-Path $env:ANDROID_HOME 'emulator/emulator.exe'
$config=Join-Path $env:ANDROID_AVD_HOME 'Solara_API35.avd/config.ini'
if (!(Test-Path -LiteralPath $config)) { throw 'Create the Solara_API35 Google APIs virtual device first.' }
$adb=Join-Path $env:ANDROID_HOME 'platform-tools/adb.exe'
if ((& $adb devices) -match 'emulator-5554\s+device') { Write-Output 'The test emulator is already running.'; return }
$camera='virtualscene'
if($CameraImage) {
    $image=(Resolve-Path -LiteralPath $CameraImage).Path
    $camera='"imagefile:'+$image+'"'
}
$arguments=@('-avd','Solara_API35','-no-snapshot','-no-audio','-gpu','swiftshader','-memory','1536','-cores','2','-camera-back',$camera)
if (!$ShowWindow) { $arguments+='-no-window' }
$windowStyle=if($ShowWindow){'Normal'}else{'Hidden'}
$process=Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle $windowStyle -RedirectStandardOutput (Join-Path $repo '.tools/emulator.log') -RedirectStandardError (Join-Path $repo '.tools/emulator-error.log') -PassThru
Write-Output "Emulator requested (PID $($process.Id)). Wait for adb shell getprop sys.boot_completed to return 1 before installing."
Write-Output 'IIS API address inside the emulator: http://10.0.2.2:8080/api'

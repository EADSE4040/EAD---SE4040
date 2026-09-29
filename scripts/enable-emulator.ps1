# Install Google's signed emulator acceleration driver on this Intel Windows PC.
# A Windows Hypervisor Platform installation is also supported by the emulator.
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run this script in administrator Windows PowerShell.' }
if (Get-Service aehd -ErrorAction SilentlyContinue) { Start-Service aehd; return }
if (Get-Service gvm -ErrorAction SilentlyContinue) { throw 'An older Google hypervisor driver already exists. Review it before installing another version.' }
$driver=Join-Path $repo '.tools/android-sdk/extras/google/Android_Emulator_Hypervisor_Driver'
$signature=Get-AuthenticodeSignature -LiteralPath (Join-Path $driver 'aehd.cat')
if ($signature.Status -ne 'Valid') { throw 'The driver catalog signature is not valid.' }
Push-Location $driver
try {
    & ./silent_install_safe.bat
    if ($LASTEXITCODE -ne 0) { throw 'Google emulator driver installation failed.' }
    if ((Get-Service aehd -ErrorAction Stop).Status -ne 'Running') { throw 'Google emulator driver is not running; inspect Windows virtualization settings.' }
} finally { Pop-Location }

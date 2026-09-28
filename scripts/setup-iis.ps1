# Administrator-only setup of dedicated loopback IIS sites on this Windows PC.
# Run prepare-iis.ps1 first. Existing sites/pools are preserved; name collisions stop setup.
$ErrorActionPreference='Stop'
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Open Windows PowerShell as Administrator and run this script again.' }
$repo=Split-Path $PSScriptRoot -Parent
$root=Join-Path $repo 'artifacts/iis-local'
$installer=Join-Path $repo '.tools/dotnet-hosting-10.0.12-win.exe'
$configPath=Join-Path $repo 'backend/SolarTrading.Api/appsettings.Local.json'
foreach ($file in @($installer,$configPath,(Join-Path $root 'api/web.config'),(Join-Path $root 'web/index.html'))) {
    if (!(Test-Path -LiteralPath $file)) { throw "Missing $file. Run prepare-iis.ps1 and configure-local.ps1 first." }
}
$signature=Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') { throw 'Installer Microsoft signature verification failed.' }
$config=Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
if (!$config.Mongo.ConnectionString -or !$config.Jwt.Key -or !$config.Qr.Key) { throw 'Local configuration is incomplete.' }
foreach ($port in @(8080,8081)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { throw "Port $port is already occupied; existing services will not be replaced." }
}
# DISM is available in administrator Windows PowerShell even when optional-feature cmdlets are absent.
& dism.exe /Online /Enable-Feature /FeatureName:IIS-WebServerRole /FeatureName:IIS-WebServer /FeatureName:IIS-CommonHttpFeatures /FeatureName:IIS-StaticContent /FeatureName:IIS-DefaultDocument /FeatureName:IIS-HttpErrors /FeatureName:IIS-ManagementConsole /All /NoRestart
if ($LASTEXITCODE -eq 3010) { throw 'Windows requires a restart. Restart this PC, then rerun setup-iis.ps1.' }
if ($LASTEXITCODE -ne 0) { throw 'Windows could not enable IIS. Review the DISM output before continuing.' }
$process=Start-Process -FilePath $installer -ArgumentList '/install','/quiet','/norestart' -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -eq 3010) { throw 'The Hosting Bundle requires a restart. Restart this PC, then rerun setup-iis.ps1.' }
if ($process.ExitCode -ne 0) { throw "Hosting Bundle installer failed: $($process.ExitCode)." }
Add-Type -Path (Join-Path $env:windir 'System32/inetsrv/Microsoft.Web.Administration.dll')
$manager=New-Object Microsoft.Web.Administration.ServerManager
try {
    foreach ($name in @('SolaraApi','SolaraWeb')) {
        if ($manager.Sites[$name] -or $manager.ApplicationPools[$name]) { throw "$name already exists. Inspect it in IIS Manager; this script will not overwrite it." }
    }
    $apiPool=$manager.ApplicationPools.Add('SolaraApi')
    $apiPool.ManagedRuntimeVersion=''
    $apiPool.Enable32BitAppOnWin64=$false
    $webPool=$manager.ApplicationPools.Add('SolaraWeb')
    $webPool.ManagedRuntimeVersion=''
    $variables=$apiPool.GetCollection('environmentVariables')
    $settings=@{ 'ASPNETCORE_ENVIRONMENT'='Production'; 'Mongo__ConnectionString'=$config.Mongo.ConnectionString; 'Jwt__Key'=$config.Jwt.Key; 'Qr__Key'=$config.Qr.Key; 'Cors__Origins__0'='http://127.0.0.1:8081' }
    # The local database already has its administrator; no bootstrap password is persisted to IIS.
    foreach ($entry in $settings.GetEnumerator()) {
        $element=$variables.CreateElement('add'); $element['name']=$entry.Key; $element['value']=$entry.Value; $variables.Add($element)
    }
    $api=$manager.Sites.Add('SolaraApi','http','127.0.0.1:8080:',(Join-Path $root 'api'))
    $api.Applications['/'].ApplicationPoolName='SolaraApi'
    $api.ServerAutoStart=$false
    $web=$manager.Sites.Add('SolaraWeb','http','127.0.0.1:8081:',(Join-Path $root 'web'))
    $web.Applications['/'].ApplicationPoolName='SolaraWeb'
    $web.ServerAutoStart=$false
    $manager.CommitChanges()
    # Read/execute access only; application identities cannot modify their published files.
    foreach ($pair in @(@('SolaraApi','api'),@('SolaraWeb','web'))) {
        & icacls.exe (Join-Path $root $pair[1]) /grant "IIS AppPool\$($pair[0]):(OI)(CI)(RX)" /T /Q
        if ($LASTEXITCODE -ne 0) { throw 'Could not assign application-pool read permissions.' }
    }
} finally { $manager.Dispose() }
Start-Service W3SVC
$manager=New-Object Microsoft.Web.Administration.ServerManager
try {
    $manager.Sites['SolaraApi'].ServerAutoStart=$true
    $manager.Sites['SolaraWeb'].ServerAutoStart=$true
    $manager.CommitChanges()
    $manager.Sites['SolaraApi'].Start() | Out-Null
    $manager.Sites['SolaraWeb'].Start() | Out-Null
} finally { $manager.Dispose() }
$healthy=$false
for ($attempt=0; $attempt -lt 20; $attempt++) {
    try { $health=Invoke-RestMethod 'http://127.0.0.1:8080/api/health'; if ($health.status -eq 'healthy') { $healthy=$true; break } } catch { Start-Sleep -Seconds 1 }
}
if (!$healthy) { throw 'Sites were installed but API health did not pass. Keep MongoDB running and inspect IIS/Event Viewer logs.' }
Invoke-WebRequest 'http://127.0.0.1:8081' -UseBasicParsing | Out-Null
Write-Output 'IIS API healthy: http://127.0.0.1:8080/api/health'
Write-Output 'IIS web portal: http://127.0.0.1:8081'
Write-Output 'Android emulator debug API: http://10.0.2.2:8080/api. HTTPS is required for release/device network hosting.'

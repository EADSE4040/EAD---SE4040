# Administrator setup for this workspace's loopback-only MongoDB replica set.
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Administrator Windows PowerShell is required.' }
$privateDir=Join-Path $repo '.tools'
$data=Join-Path $privateDir 'mongo-data'
$logs=Join-Path $privateDir 'mongo-service-log'
$mongoExe=Get-ChildItem -LiteralPath (Join-Path $privateDir 'mongodb') -Filter mongod.exe -Recurse | Select-Object -First 1 -ExpandProperty FullName
if (!$mongoExe -or !(Test-Path -LiteralPath $data)) { throw 'The existing local MongoDB installation/data were not found.' }
$existing=Get-CimInstance Win32_Service -Filter "Name='SolaraMongo'"
if ($existing -and $existing.PathName -notlike ('*'+$data+'*')) { throw 'SolaraMongo already belongs to a different data directory.' }
if (!$existing) {
    $listener=Get-NetTCPConnection -LocalPort 27018 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        $process=Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
        if ($process.Name -ne 'mongod.exe' -or !$process.CommandLine.Contains($data)) { throw 'Port 27018 belongs to another process; refusing to stop it.' }
        # MongoDB journals recover safely if a development process is terminated.
        Stop-Process -Id $process.ProcessId -Force
    }
    New-Item -ItemType Directory -Path $logs -Force | Out-Null
    & $mongoExe --install --serviceName SolaraMongo --serviceDisplayName 'Solara MongoDB replica set' --dbpath $data --logpath (Join-Path $logs 'mongod.log') --logappend --bind_ip 127.0.0.1 --port 27018 --replSet rs0
    if ($LASTEXITCODE -ne 0) { throw 'MongoDB service installation failed.' }
    & sc.exe config SolaraMongo obj= 'NT AUTHORITY\LocalService' start= auto
    if ($LASTEXITCODE -ne 0) { throw 'Could not configure the MongoDB service identity.' }
    & icacls.exe (Split-Path $mongoExe -Parent) /grant '*S-1-5-19:(OI)(CI)(RX)' /T /Q
    if ($LASTEXITCODE -ne 0) { throw 'Could not grant MongoDB binary read access.' }
    foreach ($folder in @($data,$logs)) {
        & icacls.exe $folder /grant '*S-1-5-19:(OI)(CI)(M)' /T /Q
        if ($LASTEXITCODE -ne 0) { throw 'Could not grant MongoDB data/log write access.' }
    }
}
Start-Service SolaraMongo
$ready=$false
for($i=0;$i -lt 30;$i++) {
    $socket=New-Object Net.Sockets.TcpClient
    try { $socket.Connect('127.0.0.1',27018); $ready=$true; break } catch { Start-Sleep -Seconds 1 } finally { $socket.Dispose() }
}
if(!$ready) { throw 'MongoDB did not start; inspect .tools/mongo-service-log/mongod.log.' }
Add-Type -Path (Join-Path $env:windir 'System32/inetsrv/Microsoft.Web.Administration.dll')
$manager=New-Object Microsoft.Web.Administration.ServerManager
try {
    $pool=$manager.ApplicationPools['SolaraApi']
    if($pool) { if($pool.State -eq 'Started'){$pool.Recycle()|Out-Null}else{$pool.Start()|Out-Null} }
    $sites=foreach($name in @('SolaraApi','SolaraWeb')) {
        $site=$manager.Sites[$name]
        if($site) { @{name=$name;state=$site.State.ToString();pool=$site.Applications['/'].ApplicationPoolName;bindings=@($site.Bindings | ForEach-Object { $_.Protocol+' '+$_.BindingInformation });physicalPath=$site.Applications['/'].VirtualDirectories['/'].PhysicalPath} }
    }
    @{capturedUtc=[DateTime]::UtcNow.ToString('o');mongoService=(Get-Service SolaraMongo).Status.ToString();sites=@($sites)} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $repo 'docs/evidence/iis-configuration.json')
} finally { $manager.Dispose() }
Write-Output 'SolaraMongo service is running with automatic startup; the Solara API pool was restarted.'

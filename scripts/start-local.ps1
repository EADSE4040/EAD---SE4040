$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$privateDir=Join-Path $repo '.tools'
New-Item -ItemType Directory -Path $privateDir -Force | Out-Null
function Port-IsOpen([int]$port) {
    $client=New-Object Net.Sockets.TcpClient
    try { $client.Connect('127.0.0.1',$port); return $true } catch { return $false } finally { $client.Dispose() }
}
$dotnet=Join-Path $privateDir 'dotnet/dotnet.exe'
if (!(Test-Path -LiteralPath $dotnet)) { $dotnet=(Get-Command dotnet -ErrorAction Stop).Source }
$env:DOTNET_CLI_HOME=Join-Path $privateDir 'cli'
if (!(Port-IsOpen 27018)) {
    $mongoExe=Get-ChildItem -LiteralPath (Join-Path $privateDir 'mongodb') -Filter 'mongod.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    if (!$mongoExe) { $mongoExe=(Get-Command mongod -ErrorAction Stop).Source }
    $data=Join-Path $privateDir 'mongo-data'; New-Item -ItemType Directory -Path $data -Force | Out-Null
    $mongo=Start-Process -FilePath $mongoExe -ArgumentList @('--dbpath',('"'+$data+'"'),'--bind_ip','127.0.0.1','--port','27018','--replSet','rs0','--logpath',('"'+(Join-Path $privateDir 'mongodb.log')+'"')) -WindowStyle Hidden -PassThru
    [IO.File]::WriteAllText((Join-Path $privateDir 'mongodb.pid'),$mongo.Id.ToString())
    $deadline=[DateTime]::UtcNow.AddSeconds(20)
    while (!(Port-IsOpen 27018)) { if ($mongo.HasExited -or [DateTime]::UtcNow -gt $deadline) { throw 'MongoDB failed to start. Inspect .tools/mongodb.log.' }; Start-Sleep -Milliseconds 200 }
    & $dotnet run --project (Join-Path $repo 'backend/SolarTrading.Tests') -c Release -- --init
    if ($LASTEXITCODE -ne 0) { throw 'Could not initialize the local MongoDB replica set.' }
}
if (!(Test-Path -LiteralPath (Join-Path $repo 'backend/SolarTrading.Api/appsettings.Local.json'))) { & (Join-Path $PSScriptRoot 'configure-local.ps1') }
if (!(Port-IsOpen 5080)) {
    $api=Start-Process -FilePath $dotnet -ArgumentList @('run','--project',('"'+(Join-Path $repo 'backend/SolarTrading.Api')+'"'),'-c','Release') -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput (Join-Path $privateDir 'api-output.log') -RedirectStandardError (Join-Path $privateDir 'api-error.log') -PassThru
    [IO.File]::WriteAllText((Join-Path $privateDir 'api.pid'),$api.Id.ToString())
}
if (!(Port-IsOpen 5173)) {
    $node=(Get-Command node -ErrorAction Stop).Source
    $webDir=Join-Path $repo 'frontend/web'
    if (!(Test-Path -LiteralPath (Join-Path $webDir 'node_modules/vite/bin/vite.js'))) { throw 'Run npm ci in frontend/web first.' }
    $web=Start-Process -FilePath $node -ArgumentList @(('"'+(Join-Path $webDir 'node_modules/vite/bin/vite.js')+'"'),'--host','127.0.0.1','--strictPort') -WorkingDirectory $webDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $privateDir 'web-output.log') -RedirectStandardError (Join-Path $privateDir 'web-error.log') -PassThru
    [IO.File]::WriteAllText((Join-Path $privateDir 'web.pid'),$web.Id.ToString())
}
Write-Output 'Local services requested. Portal: http://127.0.0.1:5173. Check .tools logs if a service is not ready.'

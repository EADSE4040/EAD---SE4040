param([switch]$Android)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$dotnet=Join-Path $repo '.tools/dotnet/dotnet.exe'
if (!(Test-Path -LiteralPath $dotnet)) { $dotnet='dotnet' }
$env:DOTNET_CLI_HOME=Join-Path $repo '.tools/cli'
& $dotnet build (Join-Path $repo 'backend/SolarTrading.Tests/SolarTrading.Tests.csproj') -c Release
if ($LASTEXITCODE -ne 0) { throw 'Backend build failed.' }
Push-Location (Join-Path $repo 'frontend/web')
try { & npm.cmd ci --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }; & npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' } } finally { Pop-Location }
if ($Android) {
    Push-Location (Join-Path $repo 'frontend/android')
    try { & ./gradlew.bat assembleDebug lintDebug; if ($LASTEXITCODE -ne 0) { throw 'Android checks failed.' } } finally { Pop-Location }
}

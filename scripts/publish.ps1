param([string]$ApiUrl)
$ErrorActionPreference='Stop'
if (!$ApiUrl -or $ApiUrl -notmatch '^https://.+/api$') { throw 'Provide the IIS HTTPS API URL ending in /api.' }
$repo=Split-Path $PSScriptRoot -Parent
$dotnet=Join-Path $repo '.tools/dotnet/dotnet.exe'
if (!(Test-Path -LiteralPath $dotnet)) { $dotnet='dotnet' }
$output=Join-Path $repo 'artifacts/publish'
& $dotnet publish (Join-Path $repo 'backend/SolarTrading.Api/SolarTrading.Api.csproj') -c Release -o (Join-Path $output 'api')
if ($LASTEXITCODE -ne 0) { throw 'API publish failed.' }
Push-Location (Join-Path $repo 'frontend/web')
try { $env:VITE_API_URL=$ApiUrl; & npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'Web publish failed.' }; New-Item -ItemType Directory -Path (Join-Path $output 'web') -Force | Out-Null; Copy-Item -Path './dist/*' -Destination (Join-Path $output 'web') -Recurse -Force; Copy-Item -LiteralPath './web.config' -Destination (Join-Path $output 'web/web.config') -Force } finally { Remove-Item Env:VITE_API_URL -ErrorAction SilentlyContinue; Pop-Location }
Write-Output 'IIS publish artifacts generated. Configure secrets, HTTPS bindings and CORS before starting the IIS site.'
